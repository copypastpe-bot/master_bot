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


class MasterBookingSettingsTest(unittest.IsolatedAsyncioTestCase):
    """Master dataclass + whitelist exposure of new booking-settings columns."""

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        await db.init_db()
        conn = await db.get_connection()
        try:
            await conn.execute(
                "INSERT INTO masters (id, tg_id, name, invite_token) "
                "VALUES (1, 100, 'M', 'tok')"
            )
            await conn.commit()
        finally:
            await conn.close()

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    async def test_defaults_loaded_from_db(self):
        m = await db.get_master_by_id(1)
        self.assertFalse(m.self_booking_enabled)
        self.assertEqual(m.booking_cancel_cutoff_hours, 24)
        self.assertEqual(m.booking_horizon_days, 30)

    async def test_update_master_persists_booking_flags(self):
        await db.update_master(
            1,
            self_booking_enabled=True,
            booking_cancel_cutoff_hours=12,
            booking_horizon_days=14,
        )
        m = await db.get_master_by_id(1)
        self.assertTrue(m.self_booking_enabled)
        self.assertEqual(m.booking_cancel_cutoff_hours, 12)
        self.assertEqual(m.booking_horizon_days, 14)

    async def test_update_master_rejects_unknown_booking_field(self):
        # Whitelist must not silently accept typos.
        with self.assertRaises(ValueError):
            await db.update_master(1, self_booking_enable=True)  # missing 'd'


class WeeklyScheduleTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        await db.init_db()
        conn = await db.get_connection()
        try:
            await conn.execute(
                "INSERT INTO masters (id, tg_id, name, invite_token) "
                "VALUES (1, 100, 'M', 'tok')"
            )
            await conn.commit()
        finally:
            await conn.close()

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    async def test_empty_when_unset(self):
        self.assertEqual(await db.get_master_schedule_weekly(1), [])

    async def test_set_then_get_round_trip(self):
        await db.set_master_schedule_weekly(1, [
            {"weekday": 0, "start": "10:00", "end": "14:00"},
            {"weekday": 0, "start": "16:00", "end": "20:00"},
            {"weekday": 2, "start": "09:00", "end": "18:00"},
        ])
        rows = await db.get_master_schedule_weekly(1)
        self.assertEqual(len(rows), 3)
        # Should be ordered by weekday then start_time.
        self.assertEqual(rows[0]["weekday"], 0)
        self.assertEqual(rows[0]["start_time"], "10:00")
        self.assertEqual(rows[1]["start_time"], "16:00")
        self.assertEqual(rows[2]["weekday"], 2)

    async def test_set_is_idempotent_replace(self):
        await db.set_master_schedule_weekly(1, [
            {"weekday": 0, "start": "10:00", "end": "14:00"},
            {"weekday": 1, "start": "10:00", "end": "14:00"},
        ])
        # Replace with a different set — old rows must be gone.
        await db.set_master_schedule_weekly(1, [
            {"weekday": 3, "start": "12:00", "end": "20:00"},
        ])
        rows = await db.get_master_schedule_weekly(1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["weekday"], 3)

    async def test_set_empty_clears_all(self):
        await db.set_master_schedule_weekly(1, [
            {"weekday": 0, "start": "10:00", "end": "14:00"},
        ])
        await db.set_master_schedule_weekly(1, [])
        self.assertEqual(await db.get_master_schedule_weekly(1), [])

    async def test_does_not_affect_other_masters(self):
        conn = await db.get_connection()
        try:
            await conn.execute(
                "INSERT INTO masters (id, tg_id, name, invite_token) "
                "VALUES (2, 200, 'M2', 'tok2')"
            )
            await conn.commit()
        finally:
            await conn.close()
        await db.set_master_schedule_weekly(1, [
            {"weekday": 0, "start": "10:00", "end": "14:00"},
        ])
        await db.set_master_schedule_weekly(2, [
            {"weekday": 1, "start": "09:00", "end": "12:00"},
        ])
        # Replacing master 1's schedule must leave master 2 intact.
        await db.set_master_schedule_weekly(1, [])
        self.assertEqual(await db.get_master_schedule_weekly(1), [])
        self.assertEqual(len(await db.get_master_schedule_weekly(2)), 1)
