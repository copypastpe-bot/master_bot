# Broadcast Background Tasks Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert `POST /api/master/broadcast/send` from a blocking sync loop (10–60s for big segments → nginx/Cloudflare 504) into a fire-and-forget endpoint that returns 202 with a `campaign_id` in <100ms, runs the send loop as an `asyncio.create_task()` in the background, persists progress per recipient, and resumes orphaned campaigns after container restart.

**Architecture:**
- Persist progress in two places: `campaigns` gets new status columns; new table `broadcast_recipients(campaign_id, client_id, status, ...)` is seeded up-front so resume is trivial — "send the rows that are still `pending`."
- Media bytes are written to disk under `BROADCAST_MEDIA_DIR` so a mid-flight crash can re-read them on resume. The campaign row stores `media_path` + `media_type`.
- A FastAPI `startup` hook scans `campaigns WHERE status IN ('pending','running')` and re-launches their workers.

**Tech Stack:** FastAPI, aiosqlite, aiogram, asyncio. No new external libs (apscheduler already in tree but used only for cron-like scheduler; for one-shot background work `asyncio.create_task` is enough).

**Non-goals (out of scope):**
- Per-recipient retries with exponential backoff.
- Mini App polling UI (separate ticket; backend exposes `GET /campaigns/{id}` and that's it).
- Multi-worker horizontal scaling (current deploy is single uvicorn worker).

---

## Task 1: Migration 025 — broadcast progress columns and per-recipient table

**Files:**
- Create: `migrations/025_broadcast_progress.sql`
- Test: `tests/test_broadcast_background.py`

**Step 1: Write the failing test**

```python
# tests/test_broadcast_background.py
import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("BONUS_MEDIA_DIR", "/tmp/mb_test/bm")
os.environ.setdefault("AVATARS_DIR", "/tmp/mb_test/av")
os.environ.setdefault("PORTFOLIO_DIR", "/tmp/mb_test/pf")
os.environ.setdefault("PROMO_MEDIA_DIR", "/tmp/mb_test/pm")
os.environ.setdefault("BROADCAST_MEDIA_DIR", "/tmp/mb_test/br")


class BroadcastSchemaTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        with patch.dict(os.environ, {"DB_PATH": self._tmp.name}):
            import importlib
            from src import database
            importlib.reload(database)
            self.db = database
            await self.db.init_db()

    async def asyncTearDown(self):
        os.unlink(self._tmp.name)

    async def test_campaigns_has_new_progress_columns(self):
        conn = await self.db.get_connection()
        try:
            cur = await conn.execute("PRAGMA table_info(campaigns)")
            cols = {row["name"] for row in await cur.fetchall()}
            self.assertIn("status", cols)
            self.assertIn("total_recipients", cols)
            self.assertIn("failed_count", cols)
            self.assertIn("last_progress_at", cols)
            self.assertIn("media_path", cols)
            self.assertIn("media_type", cols)
        finally:
            await conn.close()

    async def test_broadcast_recipients_table_exists(self):
        conn = await self.db.get_connection()
        try:
            cur = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='broadcast_recipients'"
            )
            row = await cur.fetchone()
            self.assertIsNotNone(row)
            cur = await conn.execute("PRAGMA table_info(broadcast_recipients)")
            cols = {row["name"] for row in await cur.fetchall()}
            self.assertEqual(
                cols,
                {"id", "campaign_id", "client_id", "tg_id", "status", "sent_at", "error"},
            )
        finally:
            await conn.close()
```

**Step 2: Run test to verify it fails**

```bash
BONUS_MEDIA_DIR=/tmp/mb_test/bm AVATARS_DIR=/tmp/mb_test/av \
PORTFOLIO_DIR=/tmp/mb_test/pf PROMO_MEDIA_DIR=/tmp/mb_test/pm \
BROADCAST_MEDIA_DIR=/tmp/mb_test/br APP_ENV=test \
python3.11 -m unittest tests.test_broadcast_background -v
```
Expected: FAIL — `AssertionError: 'status' not found` and `broadcast_recipients` table missing.

**Step 3: Write minimal migration**

```sql
-- migrations/025_broadcast_progress.sql

-- Progress columns on existing campaigns table.
-- status: pending | running | done | failed
ALTER TABLE campaigns ADD COLUMN status TEXT NOT NULL DEFAULT 'done';
ALTER TABLE campaigns ADD COLUMN total_recipients INTEGER NOT NULL DEFAULT 0;
ALTER TABLE campaigns ADD COLUMN failed_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE campaigns ADD COLUMN last_progress_at TIMESTAMP;
ALTER TABLE campaigns ADD COLUMN media_path TEXT;
ALTER TABLE campaigns ADD COLUMN media_type TEXT;

-- Per-recipient queue. Seeded at campaign creation; status flips
-- as the background worker walks the list. Restart-safe: resume by
-- selecting WHERE status = 'pending'.
CREATE TABLE IF NOT EXISTS broadcast_recipients (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id  INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    client_id    INTEGER NOT NULL REFERENCES clients(id),
    tg_id        INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',  -- pending | sent | failed | blocked
    sent_at      TIMESTAMP,
    error        TEXT
);

CREATE INDEX IF NOT EXISTS idx_broadcast_recipients_campaign_status
    ON broadcast_recipients(campaign_id, status);
```

**Note on `status DEFAULT 'done'`:** existing rows in `campaigns` were finished synchronously, so backfilling them as `done` is correct. New code will use `pending`/`running`/`done`/`failed`.

**Step 4: Run test to verify it passes**

```bash
BONUS_MEDIA_DIR=/tmp/mb_test/bm AVATARS_DIR=/tmp/mb_test/av \
PORTFOLIO_DIR=/tmp/mb_test/pf PROMO_MEDIA_DIR=/tmp/mb_test/pm \
BROADCAST_MEDIA_DIR=/tmp/mb_test/br APP_ENV=test \
python3.11 -m unittest tests.test_broadcast_background -v
```
Expected: PASS — both tests green.

**Step 5: Commit**

```bash
git add migrations/025_broadcast_progress.sql tests/test_broadcast_background.py
git commit -m "db(broadcast): add progress columns + broadcast_recipients table"
```

---

## Task 2: DB helpers for broadcast progress

**Files:**
- Modify: `src/database.py` (append helpers near existing `save_campaign` at line 3415)
- Modify: `tests/test_broadcast_background.py`

**Step 1: Write the failing test**

Add to `tests/test_broadcast_background.py`:

```python
class BroadcastQueueTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        with patch.dict(os.environ, {"DB_PATH": self._tmp.name}):
            import importlib
            from src import database
            importlib.reload(database)
            self.db = database
            await self.db.init_db()
            # Seed: 1 master, 3 clients linked to master, all with tg_id
            conn = await self.db.get_connection()
            try:
                await conn.execute(
                    "INSERT INTO masters (id, tg_id, name) VALUES (1, 100, 'M')"
                )
                for cid, tgid in [(1, 1001), (2, 1002), (3, 1003)]:
                    await conn.execute(
                        "INSERT INTO clients (id, tg_id, name) VALUES (?, ?, ?)",
                        (cid, tgid, f"Client{cid}"),
                    )
                    await conn.execute(
                        "INSERT INTO master_clients (master_id, client_id) VALUES (1, ?)",
                        (cid,),
                    )
                await conn.commit()
            finally:
                await conn.close()

    async def asyncTearDown(self):
        os.unlink(self._tmp.name)

    async def test_create_broadcast_campaign_seeds_pending_recipients(self):
        campaign_id = await self.db.create_broadcast_campaign(
            master_id=1,
            text="hi {name}",
            segment="all",
            recipients=[
                {"client_id": 1, "tg_id": 1001},
                {"client_id": 2, "tg_id": 1002},
                {"client_id": 3, "tg_id": 1003},
            ],
            media_path=None,
            media_type=None,
        )
        self.assertIsInstance(campaign_id, int)

        status = await self.db.get_broadcast_status(campaign_id)
        self.assertEqual(status["status"], "pending")
        self.assertEqual(status["total_recipients"], 3)
        self.assertEqual(status["sent_count"], 0)
        self.assertEqual(status["failed_count"], 0)

        pending = await self.db.get_pending_broadcast_recipients(campaign_id, limit=10)
        self.assertEqual(len(pending), 3)
        self.assertEqual({r["tg_id"] for r in pending}, {1001, 1002, 1003})

    async def test_mark_recipient_sent_updates_counts(self):
        campaign_id = await self.db.create_broadcast_campaign(
            master_id=1, text="x", segment="all",
            recipients=[{"client_id": 1, "tg_id": 1001}],
            media_path=None, media_type=None,
        )
        await self.db.mark_broadcast_recipient_sent(campaign_id, client_id=1)

        status = await self.db.get_broadcast_status(campaign_id)
        self.assertEqual(status["sent_count"], 1)
        pending = await self.db.get_pending_broadcast_recipients(campaign_id, limit=10)
        self.assertEqual(pending, [])

    async def test_mark_recipient_failed_records_error(self):
        campaign_id = await self.db.create_broadcast_campaign(
            master_id=1, text="x", segment="all",
            recipients=[{"client_id": 1, "tg_id": 1001}],
            media_path=None, media_type=None,
        )
        await self.db.mark_broadcast_recipient_failed(
            campaign_id, client_id=1, error="TelegramForbiddenError", blocked=True
        )
        status = await self.db.get_broadcast_status(campaign_id)
        self.assertEqual(status["failed_count"], 1)

    async def test_finalize_broadcast_sets_done_status(self):
        campaign_id = await self.db.create_broadcast_campaign(
            master_id=1, text="x", segment="all",
            recipients=[{"client_id": 1, "tg_id": 1001}],
            media_path=None, media_type=None,
        )
        await self.db.mark_broadcast_recipient_sent(campaign_id, client_id=1)
        await self.db.finalize_broadcast(campaign_id)

        status = await self.db.get_broadcast_status(campaign_id)
        self.assertEqual(status["status"], "done")

    async def test_find_resumable_campaigns_returns_pending_and_running(self):
        cid = await self.db.create_broadcast_campaign(
            master_id=1, text="x", segment="all",
            recipients=[{"client_id": 1, "tg_id": 1001}],
            media_path=None, media_type=None,
        )
        await self.db.set_broadcast_status(cid, "running")
        ids = await self.db.find_resumable_broadcasts()
        self.assertIn(cid, ids)
```

**Step 2: Run test to verify it fails**

```bash
BROADCAST_MEDIA_DIR=/tmp/mb_test/br APP_ENV=test \
python3.11 -m unittest tests.test_broadcast_background.BroadcastQueueTest -v
```
Expected: FAIL — `AttributeError: module 'src.database' has no attribute 'create_broadcast_campaign'`.

**Step 3: Add helpers**

Append to `src/database.py` after `save_campaign` (around line 3450). Each helper opens its own connection; transactions are kept small per the existing pattern in the file.

```python
async def create_broadcast_campaign(
    *,
    master_id: int,
    text: str,
    segment: str,
    recipients: list[dict],
    media_path: Optional[str],
    media_type: Optional[str],
) -> int:
    """Create a broadcast campaign in 'pending' status and seed its recipient queue.

    Returns the new campaign_id. Recipients must be dicts with keys client_id, tg_id.
    """
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO campaigns
                (master_id, type, text, segment, status, total_recipients,
                 sent_count, failed_count, media_path, media_type,
                 last_progress_at, sent_at)
            VALUES (?, 'broadcast', ?, ?, 'pending', ?, 0, 0, ?, ?, datetime('now'), datetime('now'))
            """,
            (master_id, text, segment, len(recipients), media_path, media_type),
        )
        campaign_id = cursor.lastrowid
        await conn.executemany(
            """
            INSERT INTO broadcast_recipients (campaign_id, client_id, tg_id, status)
            VALUES (?, ?, ?, 'pending')
            """,
            [(campaign_id, r["client_id"], r["tg_id"]) for r in recipients],
        )
        await conn.commit()
        return campaign_id
    finally:
        await conn.close()


async def get_pending_broadcast_recipients(campaign_id: int, *, limit: int = 100) -> list[dict]:
    """Return up to `limit` still-pending recipients for the campaign, oldest first."""
    conn = await get_connection()
    try:
        cur = await conn.execute(
            """
            SELECT br.id, br.client_id, br.tg_id, c.name
            FROM broadcast_recipients br
            LEFT JOIN clients c ON c.id = br.client_id
            WHERE br.campaign_id = ? AND br.status = 'pending'
            ORDER BY br.id
            LIMIT ?
            """,
            (campaign_id, limit),
        )
        return [dict(row) for row in await cur.fetchall()]
    finally:
        await conn.close()


async def mark_broadcast_recipient_sent(campaign_id: int, *, client_id: int) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            """
            UPDATE broadcast_recipients
            SET status='sent', sent_at=datetime('now')
            WHERE campaign_id = ? AND client_id = ? AND status = 'pending'
            """,
            (campaign_id, client_id),
        )
        await conn.execute(
            "UPDATE campaigns SET sent_count = sent_count + 1, last_progress_at = datetime('now') WHERE id = ?",
            (campaign_id,),
        )
        await conn.commit()
    finally:
        await conn.close()


async def mark_broadcast_recipient_failed(
    campaign_id: int, *, client_id: int, error: str, blocked: bool = False
) -> None:
    conn = await get_connection()
    try:
        new_status = "blocked" if blocked else "failed"
        await conn.execute(
            """
            UPDATE broadcast_recipients
            SET status = ?, sent_at = datetime('now'), error = ?
            WHERE campaign_id = ? AND client_id = ? AND status = 'pending'
            """,
            (new_status, error[:500], campaign_id, client_id),
        )
        await conn.execute(
            "UPDATE campaigns SET failed_count = failed_count + 1, last_progress_at = datetime('now') WHERE id = ?",
            (campaign_id,),
        )
        await conn.commit()
    finally:
        await conn.close()


async def set_broadcast_status(campaign_id: int, status: str) -> None:
    """Move the campaign between pending/running/done/failed."""
    assert status in {"pending", "running", "done", "failed"}
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE campaigns SET status = ?, last_progress_at = datetime('now') WHERE id = ?",
            (status, campaign_id),
        )
        await conn.commit()
    finally:
        await conn.close()


async def finalize_broadcast(campaign_id: int) -> None:
    """Mark a finished campaign as done."""
    await set_broadcast_status(campaign_id, "done")


async def get_broadcast_status(campaign_id: int) -> Optional[dict]:
    """Return public-facing status dict, or None if campaign missing."""
    conn = await get_connection()
    try:
        cur = await conn.execute(
            """
            SELECT id, master_id, status, total_recipients, sent_count, failed_count,
                   media_path, media_type, text, segment, last_progress_at
            FROM campaigns
            WHERE id = ? AND type = 'broadcast'
            """,
            (campaign_id,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def find_resumable_broadcasts() -> list[int]:
    """Return campaign IDs that are pending/running and still have unsent recipients.

    Called on startup to recover from a mid-flight crash.
    """
    conn = await get_connection()
    try:
        cur = await conn.execute(
            """
            SELECT id FROM campaigns
            WHERE type = 'broadcast' AND status IN ('pending', 'running')
            """
        )
        return [row["id"] for row in await cur.fetchall()]
    finally:
        await conn.close()
```

**Step 4: Run test to verify it passes**

```bash
BROADCAST_MEDIA_DIR=/tmp/mb_test/br APP_ENV=test \
python3.11 -m unittest tests.test_broadcast_background.BroadcastQueueTest -v
```
Expected: PASS — all five tests green.

**Step 5: Commit**

```bash
git add src/database.py tests/test_broadcast_background.py
git commit -m "db(broadcast): add helpers for queued, resumable broadcasts"
```

---

## Task 3: Background worker function

**Files:**
- Modify: `src/api/routers/master/broadcast.py` — add `_run_broadcast(campaign_id, app)` near the bottom.
- Modify: `tests/test_broadcast_background.py` — add worker test with a fake bot.

**Step 1: Write the failing test**

```python
class BroadcastWorkerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # …same DB bootstrap as BroadcastQueueTest…
        # additionally, build a fake `app` with a fake client_bot capturing calls
        from types import SimpleNamespace
        self.sent_to = []

        class FakeBot:
            async def send_message(_self, chat_id, text):
                self.sent_to.append(("text", chat_id, text))

            async def send_photo(_self, chat_id, photo, caption):
                self.sent_to.append(("photo", chat_id, caption))

            async def send_video(_self, chat_id, video, caption):
                self.sent_to.append(("video", chat_id, caption))

        self.app = SimpleNamespace(state=SimpleNamespace(client_bot=FakeBot()))

    async def test_worker_sends_to_all_pending_and_finalizes(self):
        from src.api.routers.master.broadcast import _run_broadcast
        cid = await self.db.create_broadcast_campaign(
            master_id=1, text="hi", segment="all",
            recipients=[
                {"client_id": 1, "tg_id": 1001},
                {"client_id": 2, "tg_id": 1002},
            ],
            media_path=None, media_type=None,
        )
        await _run_broadcast(cid, self.app, sleep_seconds=0)

        status = await self.db.get_broadcast_status(cid)
        self.assertEqual(status["status"], "done")
        self.assertEqual(status["sent_count"], 2)
        self.assertEqual(len(self.sent_to), 2)
        # text starts with master name prefix "M:\n\n"
        self.assertTrue(self.sent_to[0][2].startswith("M:\n\n"))
```

**Step 2: Run test to verify it fails**

```bash
... -m unittest tests.test_broadcast_background.BroadcastWorkerTest -v
```
Expected: FAIL — `ImportError: cannot import name '_run_broadcast'`.

**Step 3: Implement worker**

Add to `src/api/routers/master/broadcast.py`:

```python
async def _run_broadcast(campaign_id: int, app, *, sleep_seconds: float = 0.05) -> None:
    """Background worker — walks pending recipients for `campaign_id` until empty.

    Idempotent and restart-safe: only touches rows still in 'pending' status, so
    a resumed run after crash picks up where the previous one stopped. Reads
    media bytes from disk if media_path is set on the campaign.
    """
    from src.database import (
        get_broadcast_status,
        get_pending_broadcast_recipients,
        get_master_by_id,
        mark_broadcast_recipient_sent,
        mark_broadcast_recipient_failed,
        set_broadcast_status,
        finalize_broadcast,
    )

    campaign = await get_broadcast_status(campaign_id)
    if not campaign:
        logger.warning(f"broadcast worker: campaign {campaign_id} not found")
        return

    master = await get_master_by_id(campaign["master_id"])
    if not master:
        await set_broadcast_status(campaign_id, "failed")
        return

    client_bot = getattr(app.state, "client_bot", None)
    if not client_bot:
        logger.error("broadcast worker: client_bot not on app.state — marking failed")
        await set_broadcast_status(campaign_id, "failed")
        return

    media_bytes: Optional[bytes] = None
    if campaign["media_path"]:
        try:
            from pathlib import Path
            media_bytes = Path(campaign["media_path"]).read_bytes()
        except FileNotFoundError:
            logger.error(f"broadcast {campaign_id}: media file missing — sending text only")

    await set_broadcast_status(campaign_id, "running")

    text = campaign["text"]
    media_type = campaign["media_type"]

    while True:
        batch = await get_pending_broadcast_recipients(campaign_id, limit=50)
        if not batch:
            break

        for recipient in batch:
            tg_id = recipient["tg_id"]
            client_id = recipient["client_id"]
            personalized = f"{master.name}:\n\n{_personalize(text, recipient.get('name') or '')}"
            try:
                if media_bytes and media_type == "photo":
                    file_obj = BufferedInputFile(media_bytes, filename="photo.jpg")
                    await client_bot.send_photo(chat_id=tg_id, photo=file_obj, caption=personalized)
                elif media_bytes and media_type == "video":
                    file_obj = BufferedInputFile(media_bytes, filename="video.mp4")
                    await client_bot.send_video(chat_id=tg_id, video=file_obj, caption=personalized)
                else:
                    await client_bot.send_message(chat_id=tg_id, text=personalized)
                await mark_broadcast_recipient_sent(campaign_id, client_id=client_id)
            except TelegramForbiddenError:
                await mark_broadcast_recipient_failed(
                    campaign_id, client_id=client_id, error="blocked", blocked=True,
                )
            except Exception as e:
                logger.error(f"broadcast {campaign_id} → {tg_id}: {e}")
                await mark_broadcast_recipient_failed(
                    campaign_id, client_id=client_id, error=str(e),
                )
            if sleep_seconds:
                await asyncio.sleep(sleep_seconds)

    await finalize_broadcast(campaign_id)
```

**Step 4: Run test to verify it passes**

```bash
... -m unittest tests.test_broadcast_background.BroadcastWorkerTest -v
```
Expected: PASS.

**Step 5: Commit**

```bash
git add src/api/routers/master/broadcast.py tests/test_broadcast_background.py
git commit -m "feat(broadcast): add restart-safe background worker"
```

---

## Task 4: Refactor `POST /api/master/broadcast/send` → 202 + create_task

**Files:**
- Modify: `src/api/routers/master/broadcast.py:138-211` — replace inline send loop.
- Modify: `tests/test_broadcast_background.py` — endpoint smoke test using FastAPI TestClient.

**Step 1: Write the failing test**

```python
class BroadcastEndpointTest(unittest.IsolatedAsyncioTestCase):
    async def test_send_returns_202_with_campaign_id_immediately(self):
        # Build an in-process TestClient with overridden get_current_master.
        # Pre-seed the test DB exactly as in BroadcastWorkerTest, plus inject
        # a fake client_bot into fastapi_app.state.
        # Assert: response.status_code == 202; "campaign_id" in JSON;
        # GET /master/broadcast/campaigns/{id} eventually returns status='done'.
        ...
```

(Full test body deferred to implementation — TestClient setup needs the same DB-isolation pattern as the other API tests, see `tests/test_promo_page_task2_api.py` for the closest reference. The fixture overrides `get_current_master` with a stub returning a seeded Master row.)

**Step 2: Run test to verify it fails**

Expected: FAIL — endpoint still returns 200 with `{sent_count, failed_count}`, not 202.

**Step 3: Implement**

Replace the existing `send_broadcast` body (after validation, recipients fetch, and media read) with:

```python
    # Persist media to disk so resume after restart still has the bytes.
    media_path: Optional[str] = None
    if media_bytes:
        from pathlib import Path
        media_dir = Path(os.getenv("BROADCAST_MEDIA_DIR", "/app/data/broadcast"))
        try:
            media_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            media_dir = Path("/tmp/master_bot_broadcast")
            media_dir.mkdir(parents=True, exist_ok=True)
        suffix = ".jpg" if media_type == "photo" else ".mp4"
        media_path = str(media_dir / f"campaign_{master.id}_{int(time.time())}{suffix}")
        Path(media_path).write_bytes(media_bytes)

    from src.database import create_broadcast_campaign
    campaign_id = await create_broadcast_campaign(
        master_id=master.id,
        text=text,
        segment=segment,
        recipients=[
            {"client_id": r["client_id"], "tg_id": r["tg_id"]}
            for r in recipients if r.get("tg_id")
        ],
        media_path=media_path,
        media_type=media_type,
    )

    # Fire and forget — restart-safe via DB state + startup resume hook.
    asyncio.create_task(_run_broadcast(campaign_id, request.app))

    return JSONResponse(
        status_code=202,
        content={"campaign_id": campaign_id, "total_recipients": len(recipients)},
    )
```

Add at the top:
```python
import os
import time
from fastapi.responses import JSONResponse
```

Important: `get_clients_by_segment` returns dicts that must include `client_id` and `tg_id`. Verify the current shape in `src/database.py`; if it uses a different key (e.g. `id`), normalise here. (Spot-check before coding — saves a debug cycle.)

**Step 4: Run test to verify it passes**

Expected: 202 response, `campaign_id` returned, status eventually `done` after a short `asyncio.sleep`.

**Step 5: Commit**

```bash
git add src/api/routers/master/broadcast.py tests/test_broadcast_background.py
git commit -m "feat(broadcast): return 202 + run send in background task"
```

---

## Task 5: `GET /api/master/broadcast/campaigns/{campaign_id}` status endpoint

**Files:**
- Modify: `src/api/routers/master/broadcast.py` — append new GET handler.
- Modify: `tests/test_broadcast_background.py` — endpoint test asserting status payload.

**Step 1: Write the failing test**

```python
async def test_get_campaign_status_returns_progress(self):
    # POST send, then GET /master/broadcast/campaigns/{cid}
    # assert keys: campaign_id, status, total_recipients, sent_count,
    # failed_count, last_progress_at.
```

**Step 2: Run test to verify it fails**

Expected: 404 (route doesn't exist).

**Step 3: Implement**

```python
@router.get("/master/broadcast/campaigns/{campaign_id}")
async def get_broadcast_campaign_status(
    campaign_id: int,
    master: Master = Depends(get_current_master),
):
    """Polled by the Mini App after POST /send returns 202."""
    from src.database import get_broadcast_status
    status = await get_broadcast_status(campaign_id)
    if not status:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if status["master_id"] != master.id:
        raise HTTPException(status_code=403, detail="Not your campaign")
    return {
        "campaign_id": campaign_id,
        "status": status["status"],
        "total_recipients": status["total_recipients"],
        "sent_count": status["sent_count"],
        "failed_count": status["failed_count"],
        "last_progress_at": status["last_progress_at"],
    }
```

**Step 4: Run test to verify it passes**

Expected: 200 with full payload.

**Step 5: Commit**

```bash
git add src/api/routers/master/broadcast.py tests/test_broadcast_background.py
git commit -m "feat(broadcast): add GET /master/broadcast/campaigns/{id}"
```

---

## Task 6: Startup hook — resume orphaned campaigns

**Files:**
- Modify: `src/api/app.py` — add `@app.on_event("startup")` (or new `lifespan`) that scans for resumable campaigns and `asyncio.create_task`s them.
- Modify: `tests/test_broadcast_background.py` — simulate crash by leaving `status='running'` rows then call the hook directly.

**Step 1: Write the failing test**

```python
async def test_startup_resumes_running_broadcast(self):
    cid = await self.db.create_broadcast_campaign(
        master_id=1, text="x", segment="all",
        recipients=[{"client_id": 1, "tg_id": 1001}],
        media_path=None, media_type=None,
    )
    await self.db.set_broadcast_status(cid, "running")  # simulate crash mid-flight

    from src.api.app import resume_pending_broadcasts
    await resume_pending_broadcasts(self.app)

    # Worker is scheduled; give it a tick to drain.
    await asyncio.sleep(0.1)
    status = await self.db.get_broadcast_status(cid)
    self.assertEqual(status["status"], "done")
    self.assertEqual(status["sent_count"], 1)
```

**Step 2: Run test to verify it fails**

Expected: `ImportError: cannot import name 'resume_pending_broadcasts'`.

**Step 3: Implement**

In `src/api/app.py`, after the router includes:

```python
async def resume_pending_broadcasts(target_app=None) -> None:
    """On startup, re-launch any broadcasts that were mid-flight when the
    container last stopped. Idempotent: workers only touch rows still in
    'pending' status."""
    from src.database import find_resumable_broadcasts
    from src.api.routers.master.broadcast import _run_broadcast
    import asyncio
    import logging

    logger = logging.getLogger(__name__)
    bound_app = target_app or app
    ids = await find_resumable_broadcasts()
    if not ids:
        return
    logger.info(f"Resuming {len(ids)} broadcast(s) after restart: {ids}")
    for cid in ids:
        asyncio.create_task(_run_broadcast(cid, bound_app))


@app.on_event("startup")
async def _on_startup() -> None:
    await resume_pending_broadcasts()
```

Note: `@app.on_event("startup")` is deprecated in newer FastAPI but still works on `>=0.110` (matches `requirements.txt`). When migrating to `lifespan` is done elsewhere, fold this in.

**Step 4: Run test to verify it passes**

Expected: PASS — recipient delivered, campaign marked `done`.

**Step 5: Commit**

```bash
git add src/api/app.py tests/test_broadcast_background.py
git commit -m "feat(broadcast): resume orphaned campaigns on API startup"
```

---

## Task 7: Update rate-limit window now that send returns instantly

**Files:**
- Modify: `src/api/ratelimit.py:86` — `broadcast_limiter` is currently `max_calls=2, window_seconds=300`. Tighter limit still makes sense because each `POST /send` now triggers a long background job that holds Telegram quota. Leave value, but document why in a comment.

**Step 1: Just a comment-only patch — no test.**

```python
# Tighten not because of HTTP duration (send now returns in <100ms) but to
# protect downstream Telegram bot quotas and the broadcast_recipients
# queue from being flooded by a single master.
broadcast_limiter = RateLimiter(max_calls=2, window_seconds=300)
```

**Step 2: Commit**

```bash
git add src/api/ratelimit.py
git commit -m "chore(broadcast): document why rate limit stays at 2/5min"
```

---

## Verification pass (after all tasks)

```bash
BONUS_MEDIA_DIR=/tmp/mb_test/bm AVATARS_DIR=/tmp/mb_test/av \
PORTFOLIO_DIR=/tmp/mb_test/pf PROMO_MEDIA_DIR=/tmp/mb_test/pm \
BROADCAST_MEDIA_DIR=/tmp/mb_test/br APP_ENV=test \
python3.11 -m unittest discover -s tests -v
```
Expected: all tests (including the new broadcast suite) pass.

Manual smoke (on staging if available, or against a test bot):
1. `POST /api/master/broadcast/send` with a 3-client segment → 202 + `campaign_id` in <200ms.
2. Poll `GET /api/master/broadcast/campaigns/{id}` every 500ms — `sent_count` increments, `status` flips to `done`.
3. Mid-flight, kill the API container; restart; observe in logs `Resuming N broadcast(s) after restart` and the campaign reaching `done` shortly after.

## Frontend follow-up (not in this plan)

The Mini App currently shows a spinner inside the broadcast form until the old 200 response. After this refactor, it should:
1. POST `/send`, receive 202 + campaign_id.
2. Poll `/campaigns/{id}` every 1–2s.
3. Show progress bar (`sent_count / total_recipients`).
4. Stop polling on `status ∈ {done, failed}`.

Track separately — backend is shipping-stable without it; existing UI will still display a result by virtue of the campaigns endpoint, just synchronously updated by the user closing/reopening the screen.
