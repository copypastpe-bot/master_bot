import tempfile
import unittest
from pathlib import Path

from src import database as db


class SelfBookingSchemaTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        await db.init_db()

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    async def _cols(self, table: str) -> set[str]:
        conn = await db.get_connection()
        try:
            cur = await conn.execute(f"PRAGMA table_info({table})")
            return {row["name"] for row in await cur.fetchall()}
        finally:
            await conn.close()

    async def test_services_has_duration_minutes(self):
        self.assertIn("duration_minutes", await self._cols("services"))

    async def test_orders_has_booking_metadata(self):
        cols = await self._cols("orders")
        for c in ("source", "cancel_token", "duration_minutes"):
            self.assertIn(c, cols, f"orders.{c} missing")

    async def test_masters_has_booking_settings(self):
        cols = await self._cols("masters")
        for c in ("self_booking_enabled",
                  "booking_cancel_cutoff_hours",
                  "booking_horizon_days"):
            self.assertIn(c, cols, f"masters.{c} missing")

    async def test_master_schedule_weekly_table_shape(self):
        self.assertEqual(
            await self._cols("master_schedule_weekly"),
            {"id", "master_id", "weekday", "start_time", "end_time"},
        )

    async def test_master_schedule_exceptions_table_shape(self):
        self.assertEqual(
            await self._cols("master_schedule_exceptions"),
            {"id", "master_id", "date", "kind", "start_time", "end_time"},
        )
