import tempfile
import unittest
from pathlib import Path

from src import database as db


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
