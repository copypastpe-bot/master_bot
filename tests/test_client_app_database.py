import tempfile
import unittest
from pathlib import Path

from src import database as db


class ClientAppDatabaseTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        await db.init_db()

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    async def test_init_db_creates_reviews_and_notify_bonuses(self):
        conn = await db.get_connection()
        try:
            reviews_cols = await conn.execute("PRAGMA table_info(reviews)")
            reviews_names = {row["name"] for row in await reviews_cols.fetchall()}
            master_client_cols = await conn.execute("PRAGMA table_info(master_clients)")
            master_client_names = {row["name"] for row in await master_client_cols.fetchall()}
        finally:
            await conn.close()

        self.assertIn("id", reviews_names)
        self.assertIn("master_id", reviews_names)
        self.assertIn("client_id", reviews_names)
        self.assertIn("order_id", reviews_names)
        self.assertIn("rating", reviews_names)
        self.assertIn("text", reviews_names)
        self.assertIn("is_visible", reviews_names)
        self.assertIn("created_at", reviews_names)
        self.assertIn("notify_bonuses", master_client_names)
