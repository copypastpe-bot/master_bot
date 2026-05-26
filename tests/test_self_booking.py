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


class ScheduleExceptionsTest(unittest.IsolatedAsyncioTestCase):
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

    async def test_add_off_day(self):
        exc_id = await db.add_master_schedule_exception(
            master_id=1, date="2026-06-15", kind="off",
        )
        self.assertIsInstance(exc_id, int)
        rows = await db.get_master_schedule_exceptions(1, date="2026-06-15")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "off")
        self.assertIsNone(rows[0]["start_time"])
        self.assertIsNone(rows[0]["end_time"])

    async def test_add_override_with_hours(self):
        await db.add_master_schedule_exception(
            master_id=1, date="2026-06-16", kind="override",
            start="14:00", end="18:00",
        )
        rows = await db.get_master_schedule_exceptions(1, date="2026-06-16")
        self.assertEqual(rows[0]["start_time"], "14:00")
        self.assertEqual(rows[0]["end_time"], "18:00")

    async def test_delete_by_id_scoped_to_master(self):
        exc_id = await db.add_master_schedule_exception(
            master_id=1, date="2026-06-15", kind="off",
        )
        # Wrong master can't delete it.
        await db.delete_master_schedule_exception(master_id=2, exception_id=exc_id)
        self.assertEqual(len(await db.get_master_schedule_exceptions(1)), 1)
        # Owner can.
        await db.delete_master_schedule_exception(master_id=1, exception_id=exc_id)
        self.assertEqual(await db.get_master_schedule_exceptions(1), [])

    async def test_get_without_date_returns_all_ordered(self):
        await db.add_master_schedule_exception(1, "2026-07-01", "off")
        await db.add_master_schedule_exception(1, "2026-06-15", "off")
        rows = await db.get_master_schedule_exceptions(1)
        self.assertEqual([r["date"] for r in rows], ["2026-06-15", "2026-07-01"])


class SlotGeneratorTest(unittest.TestCase):
    """Pure-function tests — no DB, no event loop. Inputs in, list out."""

    def test_single_window_30min_step(self):
        from src.booking.slot_generator import generate_slots
        slots = generate_slots(
            weekly_intervals=[("10:00", "11:30")],
            exception=None,
            duration_minutes=30,
            existing_bookings=[],
            now=None,
            target_date="2026-06-01",
        )
        self.assertEqual(slots, ["10:00", "10:30", "11:00"])

    def test_60min_duration_in_3h_window(self):
        from src.booking.slot_generator import generate_slots
        slots = generate_slots(
            weekly_intervals=[("10:00", "13:00")],
            exception=None,
            duration_minutes=60,
            existing_bookings=[],
            now=None,
            target_date="2026-06-01",
        )
        # Candidates with 30-min step that fit a 60-min slot in [10:00, 13:00):
        # 10:00 (end 11:00 ≤ 13:00), 10:30, 11:00, 11:30, 12:00 (end 13:00 ≤ 13:00).
        self.assertEqual(slots, ["10:00", "10:30", "11:00", "11:30", "12:00"])

    def test_adjacent_existing_is_not_an_overlap(self):
        """Booking that starts exactly when another ends should be allowed."""
        from src.booking.slot_generator import generate_slots
        slots = generate_slots(
            weekly_intervals=[("10:00", "13:00")],
            exception=None,
            duration_minutes=60,
            existing_bookings=[("10:00", 60)],  # blocks 10:00–11:00 exactly
            now=None,
            target_date="2026-06-01",
        )
        # 10:00 overlaps (same start). 10:30 starts during existing.
        # 11:00 starts exactly when existing ends — adjacent, NOT overlap.
        # 11:30 fine. 12:00 fine.
        self.assertIn("11:00", slots)
        self.assertNotIn("10:00", slots)
        self.assertNotIn("10:30", slots)

    def test_overlap_in_middle_excludes_neighbors(self):
        from src.booking.slot_generator import generate_slots
        slots = generate_slots(
            weekly_intervals=[("10:00", "13:00")],
            exception=None,
            duration_minutes=60,
            existing_bookings=[("11:00", 60)],  # blocks 11:00–12:00
            now=None,
            target_date="2026-06-01",
        )
        # 10:00 (10:00-11:00) — adjacent → OK.
        # 10:30 (10:30-11:30) — overlaps existing 11:00-12:00 → NO.
        # 11:00, 11:30 — overlap → NO. 12:00 (12:00-13:00) — adjacent → OK.
        self.assertEqual(slots, ["10:00", "12:00"])

    def test_off_exception_returns_empty(self):
        from src.booking.slot_generator import generate_slots
        slots = generate_slots(
            weekly_intervals=[("10:00", "18:00")],
            exception={"kind": "off"},
            duration_minutes=30,
            existing_bookings=[],
            now=None,
            target_date="2026-06-01",
        )
        self.assertEqual(slots, [])

    def test_override_exception_replaces_weekly(self):
        from src.booking.slot_generator import generate_slots
        slots = generate_slots(
            weekly_intervals=[("10:00", "18:00")],
            exception={"kind": "override", "start": "14:00", "end": "16:00"},
            duration_minutes=60,
            existing_bookings=[],
            now=None,
            target_date="2026-06-01",
        )
        # Override replaces the 10:00-18:00 weekly with 14:00-16:00.
        # 30-min step over [14:00, 16:00) with 60-min duration:
        # 14:00 (end 15:00), 14:30 (end 15:30), 15:00 (end 16:00).
        self.assertEqual(slots, ["14:00", "14:30", "15:00"])

    def test_past_slots_pruned_for_today(self):
        from src.booking.slot_generator import generate_slots
        from datetime import datetime
        slots = generate_slots(
            weekly_intervals=[("10:00", "13:00")],
            exception=None,
            duration_minutes=60,
            existing_bookings=[],
            now=datetime(2026, 6, 1, 11, 30),
            target_date="2026-06-01",
        )
        # 10:00 — past. 10:30 — past. 11:00 — past (before 11:30 now).
        # 11:30 — exactly now (treat as past, can't book a slot starting "now").
        # 12:00 fits (12:00 + 60 = 13:00 ≤ 13:00).
        self.assertEqual(slots, ["12:00"])

    def test_now_does_not_affect_future_date(self):
        from src.booking.slot_generator import generate_slots
        from datetime import datetime
        # Now is during 2026-06-01 but target is the next day — no pruning.
        slots = generate_slots(
            weekly_intervals=[("10:00", "11:00")],
            exception=None,
            duration_minutes=30,
            existing_bookings=[],
            now=datetime(2026, 6, 1, 23, 59),
            target_date="2026-06-02",
        )
        self.assertEqual(slots, ["10:00", "10:30"])

    def test_split_shift_two_windows(self):
        from src.booking.slot_generator import generate_slots
        slots = generate_slots(
            weekly_intervals=[("10:00", "12:00"), ("16:00", "18:00")],
            exception=None,
            duration_minutes=60,
            existing_bookings=[],
            now=None,
            target_date="2026-06-01",
        )
        self.assertEqual(slots, ["10:00", "10:30", "11:00", "16:00", "16:30", "17:00"])

    def test_duration_larger_than_window_yields_nothing(self):
        from src.booking.slot_generator import generate_slots
        slots = generate_slots(
            weekly_intervals=[("10:00", "10:45")],
            exception=None,
            duration_minutes=60,
            existing_bookings=[],
            now=None,
            target_date="2026-06-01",
        )
        self.assertEqual(slots, [])


class BookingCreationTest(unittest.IsolatedAsyncioTestCase):
    """create_booking_with_overlap_check inserts inside BEGIN IMMEDIATE and
    rejects any overlap with an active order."""

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
            await conn.execute(
                "INSERT INTO clients (id, tg_id, name, phone) "
                "VALUES (1, 200, 'C', '+79991234567')"
            )
            await conn.execute(
                "INSERT INTO master_clients (master_id, client_id) VALUES (1, 1)"
            )
            await conn.commit()
        finally:
            await conn.close()

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    async def test_first_booking_succeeds_and_stamps_metadata(self):
        order_id = await db.create_booking_with_overlap_check(
            master_id=1, client_id=1,
            scheduled_at="2026-06-01 14:00:00",
            duration_minutes=60,
            service_ids=[],
            source="public",
        )
        self.assertIsInstance(order_id, int)
        # Verify stamped metadata.
        conn = await db.get_connection()
        try:
            cur = await conn.execute(
                "SELECT status, source, cancel_token, duration_minutes "
                "FROM orders WHERE id = ?", (order_id,)
            )
            row = await cur.fetchone()
        finally:
            await conn.close()
        self.assertEqual(row["status"], "confirmed")
        self.assertEqual(row["source"], "public")
        self.assertEqual(row["duration_minutes"], 60)
        self.assertIsNotNone(row["cancel_token"])
        self.assertEqual(len(row["cancel_token"]), 32)  # uuid4().hex

    async def test_overlapping_booking_raises(self):
        await db.create_booking_with_overlap_check(
            master_id=1, client_id=1,
            scheduled_at="2026-06-01 14:00:00",
            duration_minutes=60, service_ids=[], source="public",
        )
        from src.database import BookingConflictError
        with self.assertRaises(BookingConflictError):
            await db.create_booking_with_overlap_check(
                master_id=1, client_id=1,
                scheduled_at="2026-06-01 14:30:00",  # overlaps 14:00-15:00
                duration_minutes=60, service_ids=[], source="public",
            )

    async def test_adjacent_booking_succeeds(self):
        await db.create_booking_with_overlap_check(
            master_id=1, client_id=1,
            scheduled_at="2026-06-01 14:00:00",
            duration_minutes=60, service_ids=[], source="public",
        )
        # Starts exactly when the previous ends — no overlap.
        order_id = await db.create_booking_with_overlap_check(
            master_id=1, client_id=1,
            scheduled_at="2026-06-01 15:00:00",
            duration_minutes=60, service_ids=[], source="public",
        )
        self.assertIsInstance(order_id, int)

    async def test_cancelled_does_not_block_slot(self):
        order_id = await db.create_booking_with_overlap_check(
            master_id=1, client_id=1,
            scheduled_at="2026-06-01 14:00:00",
            duration_minutes=60, service_ids=[], source="public",
        )
        conn = await db.get_connection()
        try:
            await conn.execute(
                "UPDATE orders SET status='cancelled' WHERE id = ?", (order_id,)
            )
            await conn.commit()
        finally:
            await conn.close()
        # Rebooking the same slot must now succeed.
        order_id2 = await db.create_booking_with_overlap_check(
            master_id=1, client_id=1,
            scheduled_at="2026-06-01 14:00:00",
            duration_minutes=60, service_ids=[], source="public",
        )
        self.assertIsInstance(order_id2, int)
        self.assertNotEqual(order_id, order_id2)

    async def test_done_status_also_does_not_block(self):
        order_id = await db.create_booking_with_overlap_check(
            master_id=1, client_id=1,
            scheduled_at="2026-06-01 14:00:00",
            duration_minutes=60, service_ids=[], source="public",
        )
        conn = await db.get_connection()
        try:
            await conn.execute(
                "UPDATE orders SET status='done' WHERE id = ?", (order_id,)
            )
            await conn.commit()
        finally:
            await conn.close()
        # done means slot is past — same time can theoretically be reused
        # (we leave that policy to the slot generator's past-time pruning).
        order_id2 = await db.create_booking_with_overlap_check(
            master_id=1, client_id=1,
            scheduled_at="2026-06-01 14:00:00",
            duration_minutes=60, service_ids=[], source="public",
        )
        self.assertIsInstance(order_id2, int)

    async def test_different_master_can_book_same_slot(self):
        conn = await db.get_connection()
        try:
            await conn.execute(
                "INSERT INTO masters (id, tg_id, name, invite_token) "
                "VALUES (2, 200, 'M2', 'tok2')"
            )
            await conn.execute(
                "INSERT INTO master_clients (master_id, client_id) VALUES (2, 1)"
            )
            await conn.commit()
        finally:
            await conn.close()
        await db.create_booking_with_overlap_check(
            master_id=1, client_id=1,
            scheduled_at="2026-06-01 14:00:00",
            duration_minutes=60, service_ids=[], source="public",
        )
        # Different master at the same time is totally fine.
        order_id = await db.create_booking_with_overlap_check(
            master_id=2, client_id=1,
            scheduled_at="2026-06-01 14:00:00",
            duration_minutes=60, service_ids=[], source="public",
        )
        self.assertIsInstance(order_id, int)

    async def test_get_order_by_cancel_token_roundtrip(self):
        order_id = await db.create_booking_with_overlap_check(
            master_id=1, client_id=1,
            scheduled_at="2026-06-01 14:00:00",
            duration_minutes=60, service_ids=[], source="public",
        )
        conn = await db.get_connection()
        try:
            cur = await conn.execute(
                "SELECT cancel_token FROM orders WHERE id = ?", (order_id,)
            )
            token = (await cur.fetchone())["cancel_token"]
        finally:
            await conn.close()
        row = await db.get_order_by_cancel_token(token)
        self.assertEqual(row["id"], order_id)

    async def test_get_order_by_cancel_token_missing(self):
        self.assertIsNone(await db.get_order_by_cancel_token("doesnotexist"))

    async def test_cancel_booking_by_token_marks_cancelled(self):
        order_id = await db.create_booking_with_overlap_check(
            master_id=1, client_id=1,
            scheduled_at="2026-06-01 14:00:00",
            duration_minutes=60, service_ids=[], source="public",
        )
        conn = await db.get_connection()
        try:
            cur = await conn.execute(
                "SELECT cancel_token FROM orders WHERE id = ?", (order_id,)
            )
            token = (await cur.fetchone())["cancel_token"]
        finally:
            await conn.close()
        result = await db.cancel_booking_by_token(token)
        self.assertEqual(result, order_id)
        row = await db.get_order_by_cancel_token(token)
        self.assertEqual(row["status"], "cancelled")
        # Idempotent: cancelling again returns None.
        self.assertIsNone(await db.cancel_booking_by_token(token))

    async def test_concurrent_bookings_only_one_wins(self):
        """Real race: spawn 3 coroutines targeting the same slot at once.
        Exactly one must succeed; the other two must get BookingConflictError.

        Proves the BEGIN IMMEDIATE + WAL + busy_timeout combo from sprint 1
        actually serialises concurrent bookings — without it we'd be hostage
        to whichever conn wrote first, but the overlap check would race."""
        import asyncio
        from src.database import BookingConflictError

        async def book():
            try:
                return await db.create_booking_with_overlap_check(
                    master_id=1, client_id=1,
                    scheduled_at="2026-06-01 14:00:00",
                    duration_minutes=60, service_ids=[], source="public",
                )
            except BookingConflictError:
                return "conflict"

        results = await asyncio.gather(book(), book(), book())
        winners = [r for r in results if isinstance(r, int)]
        losers = [r for r in results if r == "conflict"]
        self.assertEqual(len(winners), 1, f"got results: {results}")
        self.assertEqual(len(losers), 2, f"got results: {results}")


class MasterBookingApiTest(unittest.IsolatedAsyncioTestCase):
    """Master-facing settings + schedule endpoints. Handlers are called
    directly with a stubbed Master dependency (project's existing pattern,
    see tests/test_promo_page_task2_api.py)."""

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

    async def _master(self):
        return await db.get_master_by_id(1)

    async def test_get_returns_defaults_when_empty(self):
        from src.api.routers.master.settings import get_booking_settings
        m = await self._master()
        resp = await get_booking_settings(master=m)
        self.assertEqual(resp["enabled"], False)
        self.assertEqual(resp["cancel_cutoff_hours"], 24)
        self.assertEqual(resp["horizon_days"], 30)
        self.assertEqual(resp["weekly"], [])
        self.assertEqual(resp["exceptions"], [])

    async def test_put_updates_toggle_cutoff_horizon(self):
        from src.api.routers.master.settings import (
            update_booking_settings, BookingSettingsBody,
        )
        m = await self._master()
        await update_booking_settings(
            BookingSettingsBody(enabled=True, cancel_cutoff_hours=12, horizon_days=14),
            master=m,
        )
        updated = await db.get_master_by_id(1)
        self.assertTrue(updated.self_booking_enabled)
        self.assertEqual(updated.booking_cancel_cutoff_hours, 12)
        self.assertEqual(updated.booking_horizon_days, 14)

    async def test_put_rejects_out_of_range_cutoff(self):
        from src.api.routers.master.settings import (
            update_booking_settings, BookingSettingsBody,
        )
        from pydantic import ValidationError
        m = await self._master()
        with self.assertRaises(ValidationError):
            BookingSettingsBody(enabled=True, cancel_cutoff_hours=0, horizon_days=30)
        with self.assertRaises(ValidationError):
            BookingSettingsBody(enabled=True, cancel_cutoff_hours=49, horizon_days=30)

    async def test_replace_weekly_round_trip_via_api(self):
        from src.api.routers.master.settings import (
            replace_weekly_schedule, WeeklyIntervalBody,
        )
        m = await self._master()
        await replace_weekly_schedule(
            [
                WeeklyIntervalBody(weekday=0, start="10:00", end="14:00"),
                WeeklyIntervalBody(weekday=1, start="11:00", end="15:00"),
            ],
            master=m,
        )
        from src.api.routers.master.settings import get_booking_settings
        resp = await get_booking_settings(master=m)
        self.assertEqual(len(resp["weekly"]), 2)
        self.assertEqual(resp["weekly"][0]["weekday"], 0)

    async def test_add_and_delete_exception_via_api(self):
        from src.api.routers.master.settings import (
            add_schedule_exception, remove_schedule_exception, ExceptionBody,
        )
        m = await self._master()
        result = await add_schedule_exception(
            ExceptionBody(date="2026-06-15", kind="off"),
            master=m,
        )
        exc_id = result["id"]
        from src.api.routers.master.settings import get_booking_settings
        resp = await get_booking_settings(master=m)
        self.assertEqual(len(resp["exceptions"]), 1)

        await remove_schedule_exception(exc_id, master=m)
        resp = await get_booking_settings(master=m)
        self.assertEqual(resp["exceptions"], [])

    async def test_add_exception_rejects_unknown_kind(self):
        from src.api.routers.master.settings import (
            add_schedule_exception, ExceptionBody,
        )
        from fastapi import HTTPException
        m = await self._master()
        with self.assertRaises(HTTPException) as ctx:
            await add_schedule_exception(
                ExceptionBody(date="2026-06-15", kind="vacation"),
                master=m,
            )
        self.assertEqual(ctx.exception.status_code, 422)


class ServiceDurationApiTest(unittest.IsolatedAsyncioTestCase):
    """services.duration_minutes round-trip through model / DB / endpoint."""

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

    async def _master(self):
        return await db.get_master_by_id(1)

    async def test_create_service_defaults_to_60_minutes(self):
        service = await db.create_service(master_id=1, name="Haircut", price=2000)
        self.assertEqual(service.duration_minutes, 60)
        # Round-trip via get.
        fetched = await db.get_service_by_id(service.id)
        self.assertEqual(fetched.duration_minutes, 60)

    async def test_create_service_with_explicit_duration(self):
        service = await db.create_service(
            master_id=1, name="Beard trim", price=800, duration_minutes=30,
        )
        self.assertEqual(service.duration_minutes, 30)
        fetched = await db.get_service_by_id(service.id)
        self.assertEqual(fetched.duration_minutes, 30)

    async def test_update_service_changes_duration(self):
        service = await db.create_service(master_id=1, name="x", price=100)
        await db.update_service(service.id, duration_minutes=90)
        fetched = await db.get_service_by_id(service.id)
        self.assertEqual(fetched.duration_minutes, 90)

    async def test_post_endpoint_accepts_duration_minutes(self):
        from src.api.routers.master.settings import (
            create_master_service, ServiceCreateBody,
        )
        m = await self._master()
        resp = await create_master_service(
            ServiceCreateBody(name="Manicure", price=1500, duration_minutes=90),
            master=m,
        )
        self.assertEqual(resp["duration_minutes"], 90)

    async def test_put_endpoint_accepts_duration_minutes(self):
        from src.api.routers.master.settings import (
            create_master_service, update_master_service,
            ServiceCreateBody, ServiceUpdateBody,
        )
        m = await self._master()
        created = await create_master_service(
            ServiceCreateBody(name="x", price=100),
            master=m,
        )
        await update_master_service(
            created["id"],
            ServiceUpdateBody(duration_minutes=45),
            master=m,
        )
        fetched = await db.get_service_by_id(created["id"])
        self.assertEqual(fetched.duration_minutes, 45)


class PublicBookingApiTest(unittest.IsolatedAsyncioTestCase):
    """Public unauthenticated booking flow: slots query + create booking."""

    async def asyncSetUp(self):
        from types import SimpleNamespace
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        await db.init_db()
        conn = await db.get_connection()
        try:
            await conn.execute(
                "INSERT INTO masters (id, tg_id, name, invite_token, self_booking_enabled) "
                "VALUES (1, 100, 'M', 'tok', 1)"
            )
            await conn.execute(
                "INSERT INTO services (id, master_id, name, price, duration_minutes) "
                "VALUES (1, 1, 'Haircut', 1000, 60)"
            )
            await conn.commit()
        finally:
            await conn.close()
        # Seed schedule: Mondays 10:00-18:00.
        await db.set_master_schedule_weekly(1, [
            {"weekday": 0, "start": "10:00", "end": "18:00"},
        ])

        # Capture master_bot notifications.
        self.notifications = []

        class _FakeMasterBot:
            async def send_message(_self, chat_id, text, **_kw):
                self.notifications.append((chat_id, text))

        self.bot = _FakeMasterBot()
        self.app_state = SimpleNamespace(
            state=SimpleNamespace(master_bot=self.bot)
        )
        # Per-IP rate limit is in-memory — reset between tests.
        from src.api.ratelimit import public_book_limiter
        public_book_limiter._buckets.clear()

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    def _request(self, ip="1.2.3.4"):
        from types import SimpleNamespace
        return SimpleNamespace(
            client=SimpleNamespace(host=ip),
            headers={},
            app=self.app_state,
        )

    # --- Slots endpoint ---------------------------------------------------

    async def test_slots_returns_30min_starts_in_window(self):
        from src.api.routers.public_booking import get_public_slots
        resp = await get_public_slots(
            slug="tok", service_id=1, date="2026-06-01",  # Monday
        )
        # 60-min slots at 30-min step in 10:00-18:00 → 10:00..17:00 inclusive.
        self.assertIn("10:00", resp["slots"])
        self.assertIn("17:00", resp["slots"])
        self.assertNotIn("17:30", resp["slots"])

    async def test_slots_404_when_slug_unknown(self):
        from src.api.routers.public_booking import get_public_slots
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await get_public_slots(slug="nope", service_id=1, date="2026-06-01")
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_slots_403_when_self_booking_disabled(self):
        await db.update_master(1, self_booking_enabled=False)
        from src.api.routers.public_booking import get_public_slots
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await get_public_slots(slug="tok", service_id=1, date="2026-06-01")
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_slots_excludes_already_booked(self):
        """End-to-end check: after a real booking, that slot disappears from the slots API."""
        from src.api.routers.public_booking import get_public_slots, public_book, PublicBookBody
        # Book 14:00 via the public endpoint (real flow, no FK shortcuts).
        await public_book(
            request=self._request(),
            body=PublicBookBody(
                slug="tok", service_id=1, date="2026-06-01", start="14:00",
                name="Ivan", phone="+79991234567",
            ),
        )
        resp = await get_public_slots(slug="tok", service_id=1, date="2026-06-01")
        # 60-min service @ 14:00 blocks 13:30 (would end 14:30) and 14:00 itself.
        self.assertNotIn("14:00", resp["slots"])
        self.assertNotIn("13:30", resp["slots"])
        # Adjacent 15:00 must still be free.
        self.assertIn("15:00", resp["slots"])

    # --- Book endpoint ----------------------------------------------------

    async def test_book_creates_order_and_notifies_master(self):
        from src.api.routers.public_booking import public_book, PublicBookBody
        resp = await public_book(
            request=self._request(),
            body=PublicBookBody(
                slug="tok", service_id=1, date="2026-06-01", start="10:00",
                name="Ivan", phone="+79991234567",
            ),
        )
        self.assertEqual(resp.status_code, 201)
        import json
        body = json.loads(bytes(resp.body))
        self.assertIn("order_id", body)
        self.assertIn("cancel_token", body)
        self.assertTrue(body["cancel_url"].endswith("/b/" + body["cancel_token"]))
        # Notification fired.
        self.assertEqual(len(self.notifications), 1)
        self.assertIn("Новая запись", self.notifications[0][1])
        self.assertIn("Ivan", self.notifications[0][1])

    async def test_book_rejects_invalid_phone(self):
        from src.api.routers.public_booking import public_book, PublicBookBody
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await public_book(
                request=self._request(),
                body=PublicBookBody(
                    slug="tok", service_id=1, date="2026-06-01", start="10:00",
                    name="Ivan", phone="notaphone",
                ),
            )
        self.assertEqual(ctx.exception.status_code, 422)

    async def test_book_conflict_when_slot_already_taken(self):
        from src.api.routers.public_booking import public_book, PublicBookBody
        from fastapi import HTTPException
        body = PublicBookBody(
            slug="tok", service_id=1, date="2026-06-01", start="10:00",
            name="Ivan", phone="+79991234567",
        )
        # First booking succeeds.
        await public_book(request=self._request(ip="1.1.1.1"), body=body)
        # Second from a different IP gets 409.
        with self.assertRaises(HTTPException) as ctx:
            await public_book(request=self._request(ip="2.2.2.2"), body=body)
        self.assertEqual(ctx.exception.status_code, 409)

    async def test_book_rate_limit_kicks_in_after_5(self):
        from src.api.routers.public_booking import public_book, PublicBookBody
        from fastapi import HTTPException
        # Six different slots from the same IP — the 6th must be 429.
        slots = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00"]
        req = self._request(ip="3.3.3.3")
        for i, t in enumerate(slots):
            body = PublicBookBody(
                slug="tok", service_id=1, date="2026-06-01", start=t,
                name=f"C{i}", phone="+79991234567",
            )
            if i < 5:
                resp = await public_book(request=req, body=body)
                self.assertEqual(resp.status_code, 201)
            else:
                with self.assertRaises(HTTPException) as ctx:
                    await public_book(request=req, body=body)
                self.assertEqual(ctx.exception.status_code, 429)

    # --- Cancellation endpoint + SSR page (Task 11) ----------------------

    async def test_cancel_endpoint_marks_cancelled_and_notifies(self):
        from src.api.routers.public_booking import public_book, public_cancel, PublicBookBody
        import json
        resp = await public_book(
            request=self._request(ip="5.5.5.5"),
            body=PublicBookBody(
                slug="tok", service_id=1,
                # Use a date far in the future so cutoff doesn't trip.
                date="2099-01-01", start="10:00",
                name="Ivan", phone="+79991234567",
            ),
        )
        body = json.loads(bytes(resp.body))
        token = body["cancel_token"]

        # Master gets the "new booking" notify; clear before cancel.
        self.notifications.clear()

        result = await public_cancel(request=self._request(ip="5.5.5.5"), token=token)
        self.assertEqual(result, {"ok": True})

        order = await db.get_order_by_cancel_token(token)
        self.assertEqual(order["status"], "cancelled")
        self.assertEqual(len(self.notifications), 1)
        self.assertIn("отменил", self.notifications[0][1])

    async def test_cancel_404_for_unknown_token(self):
        from src.api.routers.public_booking import public_cancel
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await public_cancel(request=self._request(), token="bogus")
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_cancel_403_after_cutoff_passed(self):
        from src.api.routers.public_booking import public_book, public_cancel, PublicBookBody
        from fastapi import HTTPException
        import json
        # Master's cutoff is the default 24 h; book a slot 1 hour from now.
        # We use a date in the past relative to "future" but in fact use direct
        # DB insert so that cutoff math fails without waiting wall-clock.
        resp = await public_book(
            request=self._request(ip="6.6.6.6"),
            body=PublicBookBody(
                slug="tok", service_id=1, date="2099-01-01", start="10:00",
                name="Ivan", phone="+79991234567",
            ),
        )
        token = json.loads(bytes(resp.body))["cancel_token"]
        # Force the order into the near future (30 min from now) so cutoff
        # (24h) is exceeded.
        from datetime import datetime, timedelta
        soon = (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        conn = await db.get_connection()
        try:
            await conn.execute(
                "UPDATE orders SET scheduled_at = ? WHERE cancel_token = ?",
                (soon, token),
            )
            await conn.commit()
        finally:
            await conn.close()
        with self.assertRaises(HTTPException) as ctx:
            await public_cancel(request=self._request(ip="6.6.6.6"), token=token)
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_cancel_page_renders_html(self):
        """SSR sanity: /b/{token} returns 200 + the master's name + service."""
        from src.api.routers.public_booking import public_book, PublicBookBody
        from src.api.routers.landing import booking_cancel_page
        from types import SimpleNamespace
        import json
        resp = await public_book(
            request=self._request(ip="7.7.7.7"),
            body=PublicBookBody(
                slug="tok", service_id=1, date="2099-01-01", start="10:00",
                name="Ivan", phone="+79991234567",
            ),
        )
        token = json.loads(bytes(resp.body))["cancel_token"]
        # Forge a minimal Request shim the way landing.py templates expect:
        # Jinja's TemplateResponse needs at minimum scope+receive+send.
        from starlette.requests import Request
        scope = {
            "type": "http", "method": "GET", "path": f"/b/{token}",
            "headers": [], "query_string": b"",
        }
        async def _r():
            return {"type": "http.disconnect"}
        req = Request(scope, _r)
        page = await booking_cancel_page(request=req, token=token)
        self.assertEqual(page.status_code, 200)
        text = bytes(page.body).decode()
        self.assertIn("Ivan", text)        # client name visible
        self.assertIn("Haircut", text)     # service visible
        self.assertIn(token, text)         # token embedded for fetch() call

    async def test_cancel_page_404_for_unknown_token(self):
        from src.api.routers.landing import booking_cancel_page
        from starlette.requests import Request
        scope = {
            "type": "http", "method": "GET", "path": "/b/x",
            "headers": [], "query_string": b"",
        }
        async def _r():
            return {"type": "http.disconnect"}
        req = Request(scope, _r)
        page = await booking_cancel_page(request=req, token="bogus")
        self.assertEqual(page.status_code, 404)

    async def test_book_reuses_existing_client_by_phone(self):
        from src.api.routers.public_booking import public_book, PublicBookBody
        await public_book(
            request=self._request(ip="4.4.4.4"),
            body=PublicBookBody(
                slug="tok", service_id=1, date="2026-06-01", start="10:00",
                name="Ivan", phone="+79991234567",
            ),
        )
        await public_book(
            request=self._request(ip="4.4.4.4"),
            body=PublicBookBody(
                slug="tok", service_id=1, date="2026-06-01", start="11:00",
                name="Ivan", phone="+79991234567",
            ),
        )
        # Both orders must reference the same client (no duplicate clients).
        conn = await db.get_connection()
        try:
            cur = await conn.execute("SELECT COUNT(*) AS c FROM clients")
            self.assertEqual((await cur.fetchone())["c"], 1)
            cur = await conn.execute("SELECT COUNT(*) AS c FROM orders")
            self.assertEqual((await cur.fetchone())["c"], 2)
        finally:
            await conn.close()
