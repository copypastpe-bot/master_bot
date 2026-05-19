import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src import database as db


class _FakeBot:
    """Captures aiogram send_* calls without hitting Telegram."""

    def __init__(self):
        self.calls = []
        self.fail_on_tg_ids: set[int] = set()
        self.blocked_tg_ids: set[int] = set()

    def _maybe_raise(self, tg_id):
        from aiogram.exceptions import TelegramForbiddenError
        if tg_id in self.blocked_tg_ids:
            raise TelegramForbiddenError(method=None, message="blocked")
        if tg_id in self.fail_on_tg_ids:
            raise RuntimeError("network glitch")

    async def send_message(self, chat_id, text):
        self._maybe_raise(chat_id)
        self.calls.append(("text", chat_id, text))

    async def send_photo(self, chat_id, photo, caption):
        self._maybe_raise(chat_id)
        self.calls.append(("photo", chat_id, caption))

    async def send_video(self, chat_id, video, caption):
        self._maybe_raise(chat_id)
        self.calls.append(("video", chat_id, caption))


def _fake_app(bot=None):
    return SimpleNamespace(state=SimpleNamespace(client_bot=bot or _FakeBot()))


async def _seed_master_with_clients(master_id=1, n=3):
    """Insert one master + N clients linked with notify_marketing=1."""
    conn = await db.get_connection()
    try:
        await conn.execute(
            "INSERT INTO masters (id, tg_id, name, invite_token) VALUES (?, ?, 'M', ?)",
            (master_id, 1000 + master_id, f"invite_{master_id}"),
        )
        for i in range(1, n + 1):
            await conn.execute(
                "INSERT INTO clients (id, tg_id, name) VALUES (?, ?, ?)",
                (i, 2000 + i, f"Client{i}"),
            )
            await conn.execute(
                "INSERT INTO master_clients (master_id, client_id, notify_marketing) VALUES (?, ?, 1)",
                (master_id, i),
            )
        await conn.commit()
    finally:
        await conn.close()


class BroadcastSchemaTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        await db.init_db()

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    async def test_campaigns_has_progress_columns(self):
        conn = await db.get_connection()
        try:
            cur = await conn.execute("PRAGMA table_info(campaigns)")
            cols = {row["name"] for row in await cur.fetchall()}
        finally:
            await conn.close()
        for col in ("status", "total_recipients", "failed_count",
                    "last_progress_at", "media_path", "media_type"):
            self.assertIn(col, cols, f"campaigns.{col} missing")

    async def test_broadcast_recipients_table_exists(self):
        conn = await db.get_connection()
        try:
            cur = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='broadcast_recipients'"
            )
            self.assertIsNotNone(await cur.fetchone())
            cur = await conn.execute("PRAGMA table_info(broadcast_recipients)")
            cols = {row["name"] for row in await cur.fetchall()}
        finally:
            await conn.close()
        self.assertEqual(
            cols,
            {"id", "campaign_id", "client_id", "tg_id", "status", "sent_at", "error"},
        )


class BroadcastQueueTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        await db.init_db()
        await _seed_master_with_clients()

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    async def test_create_seeds_pending_queue(self):
        cid = await db.create_broadcast_campaign(
            master_id=1, text="hi {name}", segment="all",
            recipients=[
                {"client_id": 1, "tg_id": 2001},
                {"client_id": 2, "tg_id": 2002},
                {"client_id": 3, "tg_id": 2003},
            ],
            media_path=None, media_type=None,
        )
        self.assertIsInstance(cid, int)

        status = await db.get_broadcast_status(cid)
        self.assertEqual(status["status"], "pending")
        self.assertEqual(status["total_recipients"], 3)
        self.assertEqual(status["sent_count"], 0)
        self.assertEqual(status["failed_count"], 0)

        pending = await db.get_pending_broadcast_recipients(cid, limit=10)
        self.assertEqual({r["tg_id"] for r in pending}, {2001, 2002, 2003})

    async def test_mark_sent_increments_counter_and_drains_queue(self):
        cid = await db.create_broadcast_campaign(
            master_id=1, text="x", segment="all",
            recipients=[{"client_id": 1, "tg_id": 2001}],
            media_path=None, media_type=None,
        )
        await db.mark_broadcast_recipient_sent(cid, client_id=1)
        status = await db.get_broadcast_status(cid)
        self.assertEqual(status["sent_count"], 1)
        self.assertEqual(await db.get_pending_broadcast_recipients(cid, limit=10), [])

    async def test_mark_failed_records_error_and_increments_failed(self):
        cid = await db.create_broadcast_campaign(
            master_id=1, text="x", segment="all",
            recipients=[{"client_id": 1, "tg_id": 2001}],
            media_path=None, media_type=None,
        )
        await db.mark_broadcast_recipient_failed(
            cid, client_id=1, error="TelegramForbiddenError", blocked=True,
        )
        status = await db.get_broadcast_status(cid)
        self.assertEqual(status["failed_count"], 1)

    async def test_finalize_sets_done(self):
        cid = await db.create_broadcast_campaign(
            master_id=1, text="x", segment="all",
            recipients=[{"client_id": 1, "tg_id": 2001}],
            media_path=None, media_type=None,
        )
        await db.mark_broadcast_recipient_sent(cid, client_id=1)
        await db.finalize_broadcast(cid)
        self.assertEqual((await db.get_broadcast_status(cid))["status"], "done")

    async def test_find_resumable_returns_pending_and_running(self):
        cid = await db.create_broadcast_campaign(
            master_id=1, text="x", segment="all",
            recipients=[{"client_id": 1, "tg_id": 2001}],
            media_path=None, media_type=None,
        )
        await db.set_broadcast_status(cid, "running")
        ids = await db.find_resumable_broadcasts()
        self.assertIn(cid, ids)
        await db.finalize_broadcast(cid)
        ids_after = await db.find_resumable_broadcasts()
        self.assertNotIn(cid, ids_after)


class BroadcastWorkerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        await db.init_db()
        await _seed_master_with_clients()
        self.bot = _FakeBot()
        self.app = _fake_app(self.bot)

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    async def test_worker_sends_to_all_and_finalizes(self):
        from src.api.routers.master.broadcast import _run_broadcast
        cid = await db.create_broadcast_campaign(
            master_id=1, text="hi {name}", segment="all",
            recipients=[
                {"client_id": 1, "tg_id": 2001},
                {"client_id": 2, "tg_id": 2002},
            ],
            media_path=None, media_type=None,
        )
        await _run_broadcast(cid, self.app, sleep_seconds=0)

        status = await db.get_broadcast_status(cid)
        self.assertEqual(status["status"], "done")
        self.assertEqual(status["sent_count"], 2)
        self.assertEqual(status["failed_count"], 0)
        # Both messages prefixed with "M:\n\n" and personalized
        texts = [c[2] for c in self.bot.calls]
        self.assertTrue(all(t.startswith("M:\n\n") for t in texts))
        self.assertIn("hi Client1", texts[0])

    async def test_worker_marks_blocked_clients_failed_but_continues(self):
        from src.api.routers.master.broadcast import _run_broadcast
        self.bot.blocked_tg_ids = {2002}
        cid = await db.create_broadcast_campaign(
            master_id=1, text="x", segment="all",
            recipients=[
                {"client_id": 1, "tg_id": 2001},
                {"client_id": 2, "tg_id": 2002},
                {"client_id": 3, "tg_id": 2003},
            ],
            media_path=None, media_type=None,
        )
        await _run_broadcast(cid, self.app, sleep_seconds=0)

        status = await db.get_broadcast_status(cid)
        self.assertEqual(status["status"], "done")
        self.assertEqual(status["sent_count"], 2)
        self.assertEqual(status["failed_count"], 1)

    async def test_worker_resumes_only_pending_rows(self):
        """A 'crashed' campaign with half its queue already sent should
        only re-send to remaining pending recipients on the next run."""
        from src.api.routers.master.broadcast import _run_broadcast
        cid = await db.create_broadcast_campaign(
            master_id=1, text="x", segment="all",
            recipients=[
                {"client_id": 1, "tg_id": 2001},
                {"client_id": 2, "tg_id": 2002},
            ],
            media_path=None, media_type=None,
        )
        # Simulate that client 1 was already sent before the crash.
        await db.mark_broadcast_recipient_sent(cid, client_id=1)
        await db.set_broadcast_status(cid, "running")

        await _run_broadcast(cid, self.app, sleep_seconds=0)

        self.assertEqual(len(self.bot.calls), 1)  # only client 2 was re-sent
        self.assertEqual(self.bot.calls[0][1], 2002)
        status = await db.get_broadcast_status(cid)
        self.assertEqual(status["sent_count"], 2)
        self.assertEqual(status["status"], "done")

    async def test_worker_reads_media_from_disk(self):
        from src.api.routers.master.broadcast import _run_broadcast
        media = Path(self.tmp.name) / "photo.jpg"
        media.write_bytes(b"\xff\xd8\xff\xe0fake")
        cid = await db.create_broadcast_campaign(
            master_id=1, text="x", segment="all",
            recipients=[{"client_id": 1, "tg_id": 2001}],
            media_path=str(media), media_type="photo",
        )
        await _run_broadcast(cid, self.app, sleep_seconds=0)
        self.assertEqual(self.bot.calls[0][0], "photo")
