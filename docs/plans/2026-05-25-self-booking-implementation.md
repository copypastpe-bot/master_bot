# Client Self-Booking Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the client self-booking feature end-to-end on the backend (DB, API, SSR public pages, client_bot integration, master notifications). The master Mini App React UI is **explicitly out of scope** for this plan — it is a follow-up that depends on the stable API contract established here.

**Architecture:** Reuse the existing `orders` table with new metadata columns. Add a per-master toggle, two schedule tables (weekly template + date exceptions), and a service-duration column. Public flow runs over SSR Jinja templates served from FastAPI. Concurrent bookings are serialised through `BEGIN IMMEDIATE` + an overlap check against existing orders (builds on the WAL/busy_timeout shipped in sprint 1). Anti-spam via the existing `RateLimiter`. Master notifications go through `master_bot.send_message` synchronously after commit.

**Tech Stack:** Python 3.11, FastAPI, aiosqlite, aiogram, Jinja2, phonenumbers (already in `requirements.txt`).

**Design source of truth:** `docs/plans/2026-05-25-self-booking-design.md` (commit 9d914bb).

**Deferred follow-up (not in this plan):** Master Mini App React UI — settings panel, weekly schedule editor, exceptions calendar, services duration field, calendar view that distinguishes auto-bookings. The backend API from this plan is the contract that follow-up will consume.

---

## Pre-flight

All tasks share these env vars when running tests locally:

```
BONUS_MEDIA_DIR=/tmp/mb_test/bm AVATARS_DIR=/tmp/mb_test/av \
PORTFOLIO_DIR=/tmp/mb_test/pf PROMO_MEDIA_DIR=/tmp/mb_test/pm \
BROADCAST_MEDIA_DIR=/tmp/mb_test/br APP_ENV=test
```

Define once and reuse:

```bash
export TEST_ENV="BONUS_MEDIA_DIR=/tmp/mb_test/bm AVATARS_DIR=/tmp/mb_test/av PORTFOLIO_DIR=/tmp/mb_test/pf PROMO_MEDIA_DIR=/tmp/mb_test/pm BROADCAST_MEDIA_DIR=/tmp/mb_test/br APP_ENV=test"
```

Each `Run tests` step becomes `env $TEST_ENV python3.11 -m unittest tests.test_self_booking[.NestedClass] -v`.

All new tests live in **one** file: `tests/test_self_booking.py`. Each task appends a class to it.

---

## Task 1: Migration 026 — schema for self-booking

**Files:**
- Create: `migrations/026_self_booking.sql`
- Create: `tests/test_self_booking.py`

**Step 1: Write failing test**

```python
# tests/test_self_booking.py
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

    async def _cols(self, table):
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
        for c in ("self_booking_enabled", "booking_cancel_cutoff_hours",
                  "booking_horizon_days"):
            self.assertIn(c, cols, f"masters.{c} missing")

    async def test_master_schedule_weekly_exists(self):
        self.assertEqual(
            await self._cols("master_schedule_weekly"),
            {"id", "master_id", "weekday", "start_time", "end_time"},
        )

    async def test_master_schedule_exceptions_exists(self):
        self.assertEqual(
            await self._cols("master_schedule_exceptions"),
            {"id", "master_id", "date", "kind", "start_time", "end_time"},
        )
```

**Step 2: Verify it fails**

```
env $TEST_ENV python3.11 -m unittest tests.test_self_booking.SelfBookingSchemaTest -v
```
Expected: 5 failures — columns/tables don't exist.

**Step 3: Write migration**

```sql
-- migrations/026_self_booking.sql

-- Service duration drives slot-grid math and overlap detection.
-- 60 minutes is a reasonable default; masters tune per service.
ALTER TABLE services ADD COLUMN duration_minutes INTEGER NOT NULL DEFAULT 60;

-- Booking metadata on the shared orders table (no separate bookings entity).
-- source distinguishes manual master entries from self-bookings.
ALTER TABLE orders ADD COLUMN source TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE orders ADD COLUMN cancel_token TEXT;
ALTER TABLE orders ADD COLUMN duration_minutes INTEGER;
CREATE INDEX IF NOT EXISTS idx_orders_cancel_token
    ON orders(cancel_token) WHERE cancel_token IS NOT NULL;

-- Per-master self-booking settings.
ALTER TABLE masters ADD COLUMN self_booking_enabled BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE masters ADD COLUMN booking_cancel_cutoff_hours INTEGER NOT NULL DEFAULT 24;
ALTER TABLE masters ADD COLUMN booking_horizon_days INTEGER NOT NULL DEFAULT 30;

-- Weekly schedule template. Multiple rows per (master, weekday) allowed
-- to support split shifts (e.g. 10-14 + 16-20).
CREATE TABLE IF NOT EXISTS master_schedule_weekly (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id   INTEGER NOT NULL REFERENCES masters(id),
    weekday     INTEGER NOT NULL,
    start_time  TEXT NOT NULL,
    end_time    TEXT NOT NULL,
    UNIQUE(master_id, weekday, start_time)
);

-- Date-level overrides: 'off' nukes the day, 'override' replaces weekly.
CREATE TABLE IF NOT EXISTS master_schedule_exceptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id   INTEGER NOT NULL REFERENCES masters(id),
    date        TEXT NOT NULL,
    kind        TEXT NOT NULL,
    start_time  TEXT,
    end_time    TEXT,
    UNIQUE(master_id, date, start_time)
);
```

**Step 4: Verify passing**

```
env $TEST_ENV python3.11 -m unittest tests.test_self_booking.SelfBookingSchemaTest -v
```
Expected: 5/5 OK.

**Step 5: Commit**

```bash
git add migrations/026_self_booking.sql tests/test_self_booking.py
git commit -m "db(booking): add schema for self-booking (migration 026)"
```

---

## Task 2: Settings model — masters booking flags

**Files:**
- Modify: `src/database.py` — append helpers; widen `ALLOWED_MASTER_FIELDS` whitelist near top of file (search for `ALLOWED_MASTER_FIELDS`).
- Modify: `src/models.py` — append fields to `Master` dataclass.
- Modify: `tests/test_self_booking.py`

**Step 1: Write failing test (new class)**

```python
class MasterBookingSettingsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        await db.init_db()
        conn = await db.get_connection()
        try:
            await conn.execute(
                "INSERT INTO masters (id, tg_id, name, invite_token) VALUES (1, 100, 'M', 'tok')"
            )
            await conn.commit()
        finally:
            await conn.close()

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    async def test_defaults_loaded_on_master(self):
        m = await db.get_master_by_id(1)
        self.assertFalse(m.self_booking_enabled)
        self.assertEqual(m.booking_cancel_cutoff_hours, 24)
        self.assertEqual(m.booking_horizon_days, 30)

    async def test_update_master_persists_booking_flags(self):
        await db.update_master(1,
            self_booking_enabled=True,
            booking_cancel_cutoff_hours=12,
            booking_horizon_days=14,
        )
        m = await db.get_master_by_id(1)
        self.assertTrue(m.self_booking_enabled)
        self.assertEqual(m.booking_cancel_cutoff_hours, 12)
        self.assertEqual(m.booking_horizon_days, 14)
```

**Step 2: Verify fail** — `AttributeError: 'Master' object has no attribute 'self_booking_enabled'`.

**Step 3: Implement**

Edit `src/models.py` — append to `Master` dataclass (after existing fields like `gc_credentials`):

```python
    self_booking_enabled: bool = False
    booking_cancel_cutoff_hours: int = 24
    booking_horizon_days: int = 30
```

Edit `src/database.py`:
1. Find `ALLOWED_MASTER_FIELDS = (...)` near top. Add three names: `"self_booking_enabled"`, `"booking_cancel_cutoff_hours"`, `"booking_horizon_days"`.
2. Find the SELECT list used by `get_master_by_id` (the constant `MASTER_COLUMNS` or similar — grep `"invite_token", "sphere"` to locate). Add the same three names.
3. Find the Master constructor call inside `_row_to_master` (or equivalent helper) and add:
   ```python
   self_booking_enabled=bool(row["self_booking_enabled"]),
   booking_cancel_cutoff_hours=row["booking_cancel_cutoff_hours"],
   booking_horizon_days=row["booking_horizon_days"],
   ```

**Step 4: Verify pass.**

**Step 5: Commit**

```bash
git add src/models.py src/database.py tests/test_self_booking.py
git commit -m "db(booking): master self-booking settings (toggle/cutoff/horizon)"
```

---

## Task 3: Weekly schedule CRUD

**Files:**
- Modify: `src/database.py`
- Modify: `tests/test_self_booking.py`

**Step 1: Failing test**

```python
class WeeklyScheduleTest(unittest.IsolatedAsyncioTestCase):
    # same setUp/tearDown pattern as MasterBookingSettingsTest, master id=1 seeded

    async def test_set_weekly_replaces_existing(self):
        await db.set_master_schedule_weekly(1, [
            {"weekday": 0, "start": "10:00", "end": "14:00"},
            {"weekday": 0, "start": "16:00", "end": "20:00"},
            {"weekday": 2, "start": "09:00", "end": "18:00"},
        ])
        rows = await db.get_master_schedule_weekly(1)
        self.assertEqual(len(rows), 3)

        # Replace with a smaller set — old rows must be gone.
        await db.set_master_schedule_weekly(1, [
            {"weekday": 1, "start": "10:00", "end": "12:00"},
        ])
        rows = await db.get_master_schedule_weekly(1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["weekday"], 1)
```

**Step 2: Verify fail.**

**Step 3: Implement (append to `src/database.py` near `update_master`)**

```python
async def get_master_schedule_weekly(master_id: int) -> list[dict]:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "SELECT id, weekday, start_time, end_time FROM master_schedule_weekly "
            "WHERE master_id = ? ORDER BY weekday, start_time",
            (master_id,),
        )
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await conn.close()


async def set_master_schedule_weekly(master_id: int, intervals: list[dict]) -> None:
    """Idempotently replace the master's weekly template. Each interval dict has
    keys weekday (0=Mon), start (HH:MM), end (HH:MM)."""
    conn = await get_connection()
    try:
        await conn.execute("BEGIN IMMEDIATE")
        await conn.execute(
            "DELETE FROM master_schedule_weekly WHERE master_id = ?", (master_id,)
        )
        await conn.executemany(
            "INSERT INTO master_schedule_weekly (master_id, weekday, start_time, end_time) "
            "VALUES (?, ?, ?, ?)",
            [(master_id, i["weekday"], i["start"], i["end"]) for i in intervals],
        )
        await conn.commit()
    finally:
        await conn.close()
```

**Step 4: Pass.**

**Step 5: Commit**

```bash
git commit -m "db(booking): weekly schedule template CRUD"
```

---

## Task 4: Schedule exceptions CRUD

Same pattern as Task 3 — new test class `ScheduleExceptionsTest` covering:
- Add `kind='off'` for a date → `get_master_schedule_exceptions(master_id, "2026-06-15")` returns it.
- Add `kind='override'` with start/end → returned with the times.
- Delete by id → gone.

Helpers to add in `src/database.py`:

```python
async def add_master_schedule_exception(
    master_id: int, date: str, kind: str,
    start: Optional[str] = None, end: Optional[str] = None,
) -> int:
    assert kind in ("off", "override")
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "INSERT INTO master_schedule_exceptions (master_id, date, kind, start_time, end_time) "
            "VALUES (?, ?, ?, ?, ?)",
            (master_id, date, kind, start, end),
        )
        await conn.commit()
        return cur.lastrowid
    finally:
        await conn.close()


async def delete_master_schedule_exception(master_id: int, exception_id: int) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            "DELETE FROM master_schedule_exceptions WHERE id = ? AND master_id = ?",
            (exception_id, master_id),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_master_schedule_exceptions(
    master_id: int, date: Optional[str] = None,
) -> list[dict]:
    conn = await get_connection()
    try:
        if date is not None:
            cur = await conn.execute(
                "SELECT * FROM master_schedule_exceptions "
                "WHERE master_id = ? AND date = ? ORDER BY start_time",
                (master_id, date),
            )
        else:
            cur = await conn.execute(
                "SELECT * FROM master_schedule_exceptions WHERE master_id = ? "
                "ORDER BY date, start_time",
                (master_id,),
            )
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await conn.close()
```

Commit: `db(booking): schedule exceptions CRUD`.

---

## Task 5: Slot generator (pure function)

The heart of the feature. Keep it pure and well-tested — every booking flow funnels through this.

**Files:**
- Create: `src/booking/slot_generator.py` (new package: also add `src/booking/__init__.py` empty).
- Modify: `tests/test_self_booking.py`

**Step 1: Failing test**

```python
class SlotGeneratorTest(unittest.TestCase):
    # No DB — purely on inputs. This is a sync test.

    def test_returns_starts_within_interval_for_30min_step(self):
        from src.booking.slot_generator import generate_slots
        slots = generate_slots(
            weekly_intervals=[("10:00", "11:30")],
            exception=None,
            duration_minutes=30,
            existing_bookings=[],
            now=None,  # any time, treat all as future
            target_date="2026-06-01",
        )
        self.assertEqual(slots, ["10:00", "10:30", "11:00"])

    def test_excludes_overlapping_existing(self):
        from src.booking.slot_generator import generate_slots
        slots = generate_slots(
            weekly_intervals=[("10:00", "12:00")],
            exception=None,
            duration_minutes=60,
            existing_bookings=[("10:30", 60)],  # blocks 10:30–11:30
            now=None,
            target_date="2026-06-01",
        )
        # Candidates at 30-min step: 10:00, 10:30, 11:00.
        # 10:00 booking would end at 11:00, overlaps 10:30–11:30. EXCLUDE.
        # 10:30 == existing start. EXCLUDE.
        # 11:00 starts during existing. EXCLUDE.
        # Only 11:30? No — 11:30+60=12:30 exceeds end. Actually with end 12:00,
        # 11:00 would be last candidate. So no slots.
        self.assertEqual(slots, [])

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
        self.assertEqual(slots, ["14:00", "15:00"])

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
        # 10:00 — past. 11:00 — past (before 11:30 now). 12:00 — future. Last 12:00+60=13:00 OK.
        self.assertEqual(slots, ["12:00"])
```

**Step 2: Verify fail** (module doesn't exist).

**Step 3: Implement**

```python
# src/booking/__init__.py — empty file

# src/booking/slot_generator.py
"""Pure function: given a master's available windows for a date and
existing bookings, return the list of available start times.

No DB access — caller assembles inputs from DB and passes them in.
This keeps the algorithm testable without fixtures and gives one place
to evolve the rules.
"""
from datetime import date as date_cls, datetime, time, timedelta
from typing import Optional


SLOT_STEP_MINUTES = 30


def _to_dt(target_date: str, hhmm: str) -> datetime:
    d = date_cls.fromisoformat(target_date)
    h, m = map(int, hhmm.split(":"))
    return datetime.combine(d, time(h, m))


def _fmt(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def generate_slots(
    *,
    weekly_intervals: list[tuple[str, str]],
    exception: Optional[dict],   # {kind, start?, end?} or None
    duration_minutes: int,
    existing_bookings: list[tuple[str, int]],  # [(start_hhmm, duration_minutes)]
    now: Optional[datetime],
    target_date: str,
) -> list[str]:
    """Return available start times in HH:MM, ordered."""
    if exception is not None:
        if exception["kind"] == "off":
            return []
        if exception["kind"] == "override":
            intervals = [(exception["start"], exception["end"])]
        else:
            intervals = weekly_intervals
    else:
        intervals = weekly_intervals

    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=SLOT_STEP_MINUTES)

    existing_ranges = [
        (_to_dt(target_date, s), _to_dt(target_date, s) + timedelta(minutes=d))
        for s, d in existing_bookings
    ]

    results = []
    for win_start, win_end in intervals:
        cursor = _to_dt(target_date, win_start)
        end_dt = _to_dt(target_date, win_end)
        while cursor + duration <= end_dt:
            cand_end = cursor + duration
            # Past-time prune for today.
            if now is not None and cursor < now:
                cursor += step
                continue
            # Overlap with existing: existing.start < cand.end AND existing.end > cand.start
            overlap = any(
                e_start < cand_end and e_end > cursor
                for e_start, e_end in existing_ranges
            )
            if not overlap:
                results.append(_fmt(cursor))
            cursor += step

    return results
```

**Step 4: Pass.**

**Step 5: Commit**

```bash
git add src/booking/ tests/test_self_booking.py
git commit -m "feat(booking): pure slot-generator with TDD tests"
```

---

## Task 6: Booking creation helper with overlap check

**Files:**
- Modify: `src/database.py`
- Modify: `tests/test_self_booking.py`

**Step 1: Failing test (race condition)**

```python
class BookingCreationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        await db.init_db()
        conn = await db.get_connection()
        try:
            await conn.execute(
                "INSERT INTO masters (id, tg_id, name, invite_token) VALUES (1, 100, 'M', 'tok')"
            )
            await conn.execute(
                "INSERT INTO clients (id, tg_id, name, phone) VALUES (1, 200, 'C', '+79991234567')"
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

    async def test_first_booking_succeeds(self):
        order_id = await db.create_booking_with_overlap_check(
            master_id=1, client_id=1,
            scheduled_at="2026-06-01 14:00:00",
            duration_minutes=60,
            service_ids=[],
            source="public",
        )
        self.assertIsInstance(order_id, int)

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
        # 15:00 starts exactly when previous ends — no overlap.
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
        # Now we can rebook the same slot.
        order_id2 = await db.create_booking_with_overlap_check(
            master_id=1, client_id=1,
            scheduled_at="2026-06-01 14:00:00",
            duration_minutes=60, service_ids=[], source="public",
        )
        self.assertIsInstance(order_id2, int)
```

**Step 2: Fail.**

**Step 3: Implement (append to `src/database.py`)**

```python
import uuid as _uuid


class BookingConflictError(Exception):
    """Raised when a self-booking would overlap an existing active order."""


async def create_booking_with_overlap_check(
    *,
    master_id: int,
    client_id: int,
    scheduled_at: str,           # ISO "YYYY-MM-DD HH:MM:SS"
    duration_minutes: int,
    service_ids: list[int],
    source: str,
    amount_total: int = 0,
) -> int:
    """Insert an order in a serialised transaction. Overlap = any active
    order on the same master whose interval intersects [scheduled_at,
    scheduled_at + duration_minutes). 'Active' = status NOT IN
    ('cancelled','done')."""
    cancel_token = _uuid.uuid4().hex
    conn = await get_connection()
    try:
        await conn.execute("BEGIN IMMEDIATE")
        # Overlap check — SQLite has no real datetime arithmetic with intervals,
        # so we compute the candidate end and compare strings (ISO sorts lexically).
        cur = await conn.execute(
            """
            SELECT id FROM orders
            WHERE master_id = ?
              AND status NOT IN ('cancelled', 'done')
              AND scheduled_at IS NOT NULL
              AND datetime(scheduled_at) <
                  datetime(?, '+' || ? || ' minutes')
              AND datetime(scheduled_at, '+' || COALESCE(duration_minutes, 60) || ' minutes')
                  > datetime(?)
            LIMIT 1
            """,
            (master_id, scheduled_at, duration_minutes, scheduled_at),
        )
        if await cur.fetchone():
            await conn.rollback()
            raise BookingConflictError(
                f"slot {scheduled_at} already taken for master {master_id}"
            )
        cur = await conn.execute(
            """
            INSERT INTO orders
              (master_id, client_id, scheduled_at, status, source,
               cancel_token, duration_minutes, amount_total)
            VALUES (?, ?, ?, 'confirmed', ?, ?, ?, ?)
            """,
            (master_id, client_id, scheduled_at, source,
             cancel_token, duration_minutes, amount_total),
        )
        order_id = cur.lastrowid
        for service_id in service_ids:
            await conn.execute(
                "INSERT INTO order_items (order_id, service_id) VALUES (?, ?)",
                (order_id, service_id),
            )
        await conn.commit()
        return order_id
    finally:
        await conn.close()


async def get_order_by_cancel_token(token: str) -> Optional[dict]:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "SELECT * FROM orders WHERE cancel_token = ?", (token,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def cancel_booking_by_token(token: str) -> Optional[int]:
    """Mark booking as cancelled. Returns order_id on success, None if token
    not found or already cancelled/done."""
    conn = await get_connection()
    try:
        await conn.execute("BEGIN IMMEDIATE")
        cur = await conn.execute(
            "SELECT id, status FROM orders WHERE cancel_token = ?", (token,)
        )
        row = await cur.fetchone()
        if not row or row["status"] in ("cancelled", "done"):
            await conn.rollback()
            return None
        await conn.execute(
            "UPDATE orders SET status='cancelled', cancel_reason='client_self_cancel' "
            "WHERE id = ?", (row["id"],)
        )
        await conn.commit()
        return row["id"]
    finally:
        await conn.close()
```

**Step 4: Pass.**

**Step 5: Commit**

```bash
git commit -m "feat(booking): create_booking_with_overlap_check + cancel helpers"
```

---

## Task 7: Concurrency test (real race)

A second test that actually launches two coroutines racing on the same slot. Catches mistakes in `BEGIN IMMEDIATE` placement.

**Files:**
- Modify: `tests/test_self_booking.py` — add to `BookingCreationTest`

```python
    async def test_concurrent_bookings_only_one_wins(self):
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
        self.assertEqual(len(losers), 2)
```

Run → pass (the prior task already enforces this). Commit:

```bash
git commit -m "test(booking): real-race concurrency test"
```

---

## Task 8: Master settings API

**Files:**
- Modify: `src/api/routers/master/settings.py` (or create dedicated `booking.py` router under same prefix). Pick whichever has the master `Depends(get_current_master)` already wired; settings.py likely does.
- Modify: `src/api/app.py` — include new router only if you created one.
- Modify: `tests/test_self_booking.py`

**Step 1: Failing test (call the handler function directly, the project's existing pattern)**

```python
class MasterBookingApiTest(unittest.IsolatedAsyncioTestCase):
    # Standard setUp + seed master id=1.

    async def _master(self):
        return await db.get_master_by_id(1)

    async def test_get_returns_defaults(self):
        from src.api.routers.master.settings import get_booking_settings
        m = await self._master()
        resp = await get_booking_settings(master=m)
        self.assertEqual(resp, {
            "enabled": False,
            "cancel_cutoff_hours": 24,
            "horizon_days": 30,
            "weekly": [],
            "exceptions": [],
        })

    async def test_put_updates_toggle_and_cutoff(self):
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
```

**Step 2: Fail.**

**Step 3: Implement** — append to `src/api/routers/master/settings.py` (read top 20 lines first to confirm router instance name and `get_current_master` import):

```python
from pydantic import BaseModel, Field

from src.database import (
    get_master_schedule_weekly, get_master_schedule_exceptions,
    set_master_schedule_weekly, add_master_schedule_exception,
    delete_master_schedule_exception, update_master,
)


class BookingSettingsBody(BaseModel):
    enabled: bool
    cancel_cutoff_hours: int = Field(ge=1, le=48)
    horizon_days: int = Field(ge=1, le=60)


class WeeklyIntervalBody(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start: str
    end: str


class ExceptionBody(BaseModel):
    date: str
    kind: str  # 'off' | 'override'
    start: Optional[str] = None
    end: Optional[str] = None


@router.get("/master/booking-settings")
async def get_booking_settings(master: Master = Depends(get_current_master)):
    return {
        "enabled": master.self_booking_enabled,
        "cancel_cutoff_hours": master.booking_cancel_cutoff_hours,
        "horizon_days": master.booking_horizon_days,
        "weekly": await get_master_schedule_weekly(master.id),
        "exceptions": await get_master_schedule_exceptions(master.id),
    }


@router.put("/master/booking-settings")
async def update_booking_settings(
    body: BookingSettingsBody,
    master: Master = Depends(get_current_master),
):
    await update_master(master.id,
        self_booking_enabled=body.enabled,
        booking_cancel_cutoff_hours=body.cancel_cutoff_hours,
        booking_horizon_days=body.horizon_days,
    )
    return {"ok": True}


@router.put("/master/schedule/weekly")
async def replace_weekly(
    intervals: list[WeeklyIntervalBody],
    master: Master = Depends(get_current_master),
):
    await set_master_schedule_weekly(master.id, [i.model_dump() for i in intervals])
    return {"ok": True, "count": len(intervals)}


@router.post("/master/schedule/exceptions")
async def add_exception(
    body: ExceptionBody,
    master: Master = Depends(get_current_master),
):
    if body.kind not in ("off", "override"):
        raise HTTPException(status_code=422, detail="kind must be off|override")
    exc_id = await add_master_schedule_exception(
        master.id, body.date, body.kind, body.start, body.end,
    )
    return {"id": exc_id}


@router.delete("/master/schedule/exceptions/{exc_id}")
async def remove_exception(
    exc_id: int,
    master: Master = Depends(get_current_master),
):
    await delete_master_schedule_exception(master.id, exc_id)
    return {"ok": True}
```

**Step 4: Pass.**

**Step 5: Commit**

```bash
git commit -m "feat(api): master booking-settings + schedule endpoints"
```

---

## Task 9: Service duration in services API

**Files:**
- Modify: `src/api/routers/master/services_router.py` (or wherever PUT /master/services lives — grep `@router.put.*services`).
- Modify: `tests/test_self_booking.py`

**Step 1: Test that PUT accepts duration_minutes and GET returns it.**

Reuse the existing API; just verify the new field flows in and out. Append a small test, then extend the existing endpoint's request model to include `duration_minutes: Optional[int] = None` and pass it through to `update_service`. Likewise on POST and GET.

`update_service` in `database.py` already uses kwargs whitelist (`ALLOWED_SERVICE_FIELDS`). Add `"duration_minutes"` to that whitelist.

Commit: `feat(api): expose service duration_minutes in master services endpoints`.

---

## Task 10: Public booking API — slots + book

**Files:**
- Create: `src/api/routers/public_booking.py`
- Modify: `src/api/app.py` — `app.include_router(public_booking.router, prefix="/api")`
- Modify: `src/api/ratelimit.py` — add `public_book_limiter = RateLimiter(5, 3600)` next to existing limiters.
- Modify: `tests/test_self_booking.py`

**Step 1: Failing test**

```python
class PublicBookingApiTest(unittest.IsolatedAsyncioTestCase):
    # setUp seeds: master id=1 with self_booking_enabled=True,
    # services row (id=1, duration_minutes=60),
    # weekly: Mon 10:00-18:00.

    async def test_slots_returns_starts(self):
        from src.api.routers.public_booking import get_public_slots
        # Pick a Monday in the future; format date as ISO.
        resp = await get_public_slots(
            slug="tok",  # using invite_token as slug for simplicity
            service_id=1,
            date="2026-06-01",  # Monday
        )
        # Expect 30-min step slots covering 10:00-17:00 (last 60-min slot starts 17:00).
        self.assertIn("10:00", resp["slots"])
        self.assertIn("17:00", resp["slots"])
        self.assertNotIn("17:30", resp["slots"])

    async def test_book_creates_order_and_returns_cancel_token(self):
        from src.api.routers.public_booking import (
            public_book, PublicBookBody,
        )
        from types import SimpleNamespace
        # Inject fake request with client.host for rate-limit key.
        req = SimpleNamespace(
            client=SimpleNamespace(host="1.2.3.4"),
            headers={},
            app=SimpleNamespace(state=SimpleNamespace(master_bot=_FakeMasterBot())),
        )
        body = PublicBookBody(
            slug="tok", service_id=1, date="2026-06-01", start="10:00",
            name="Ivan", phone="+79991234567",
        )
        resp = await public_book(request=req, body=body)
        self.assertEqual(resp.status_code, 201)
        import json
        data = json.loads(bytes(resp.body))
        self.assertIn("cancel_token", data)
        self.assertIn("order_id", data)
```

(Define `_FakeMasterBot` once at top of file with an async `send_message` capturing calls.)

**Step 2: Fail.**

**Step 3: Implement**

```python
# src/api/routers/public_booking.py
"""Public (unauthenticated) booking endpoints — slots query and create.

Reachable by anonymous browsers via the master's public minisite. Anti-spam
via per-IP rate limit; phone validation via the `phonenumbers` lib already
in requirements. Identity stored on a fresh or existing clients row;
overlap check protected by BEGIN IMMEDIATE + WAL (sprint 1)."""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.api.ratelimit import public_book_limiter
from src.booking.slot_generator import generate_slots
from src.config import MINIAPP_URL
from src.database import (
    BookingConflictError,
    create_booking_with_overlap_check,
    get_client_by_phone,
    get_client_by_tg_id,
    get_master_by_invite_token,
    get_master_schedule_exceptions,
    get_master_schedule_weekly,
    get_service_by_id,
    link_client_to_master,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["public"])


def _normalize_phone(raw: str) -> Optional[str]:
    try:
        import phonenumbers
        parsed = phonenumbers.parse(raw, "RU")
        if not phonenumbers.is_valid_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        return None


async def _load_master(slug: str):
    """Slug resolution: try promo slug first, fall back to invite_token."""
    # NOTE: We start with invite_token only. Promo-slug lookup is added later
    # to keep this commit small. The minisite already accepts invite_token.
    m = await get_master_by_invite_token(slug)
    if not m:
        raise HTTPException(status_code=404, detail="Master not found")
    if not m.self_booking_enabled:
        raise HTTPException(status_code=403, detail="Self-booking disabled")
    return m


@router.get("/public/{slug}/slots")
async def get_public_slots(slug: str, service_id: int, date: str):
    master = await _load_master(slug)
    service = await get_service_by_id(service_id)
    if not service or service.master_id != master.id:
        raise HTTPException(status_code=404, detail="Service not found")

    # Build inputs for the pure generator.
    weekday = datetime.fromisoformat(date).weekday()
    weekly_rows = await get_master_schedule_weekly(master.id)
    weekly_intervals = [
        (r["start_time"], r["end_time"])
        for r in weekly_rows if r["weekday"] == weekday
    ]
    exc_rows = await get_master_schedule_exceptions(master.id, date)
    exception = None
    if exc_rows:
        e = exc_rows[0]
        exception = {"kind": e["kind"], "start": e["start_time"], "end": e["end_time"]}

    # Existing active bookings on that date for overlap pruning.
    from src.database import get_connection
    conn = await get_connection()
    try:
        cur = await conn.execute(
            """SELECT scheduled_at, duration_minutes FROM orders
               WHERE master_id = ? AND date(scheduled_at) = ?
                 AND status NOT IN ('cancelled', 'done')""",
            (master.id, date),
        )
        existing = []
        for row in await cur.fetchall():
            sched = row["scheduled_at"]
            # Extract HH:MM portion regardless of T- or space-separator.
            t = sched.split("T")[-1].split(" ")[-1][:5]
            existing.append((t, row["duration_minutes"] or 60))
    finally:
        await conn.close()

    slots = generate_slots(
        weekly_intervals=weekly_intervals,
        exception=exception,
        duration_minutes=service.duration_minutes,
        existing_bookings=existing,
        now=datetime.now() if date == datetime.now().date().isoformat() else None,
        target_date=date,
    )
    return {"slots": slots}


class PublicBookBody(BaseModel):
    slug: str
    service_id: int
    date: str
    start: str
    name: str = Field(min_length=1, max_length=80)
    phone: str
    tg_username: Optional[str] = None
    tg_id: Optional[int] = None


@router.post("/public/book")
async def public_book(request: Request, body: PublicBookBody):
    # Rate limit by IP.
    ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() \
        or (request.client.host if request.client else "unknown")
    if not public_book_limiter.is_allowed(f"ip:{ip}"):
        raise HTTPException(status_code=429, detail="Too many bookings from this IP")

    master = await _load_master(body.slug)
    service = await get_service_by_id(body.service_id)
    if not service or service.master_id != master.id:
        raise HTTPException(status_code=404, detail="Service not found")

    phone = _normalize_phone(body.phone)
    if phone is None:
        raise HTTPException(status_code=422, detail="Invalid phone number")

    # Upsert client.
    client = None
    if body.tg_id:
        client = await get_client_by_tg_id(body.tg_id)
    if client is None:
        client = await get_client_by_phone(phone)
    if client is None:
        # Create minimal record. tg_id may be None.
        from src.database import create_client_minimal
        client_id = await create_client_minimal(
            name=body.name, phone=phone,
            tg_id=body.tg_id, tg_username=body.tg_username,
        )
    else:
        client_id = client.id

    await link_client_to_master(master.id, client_id)

    scheduled_at = f"{body.date} {body.start}:00"
    try:
        order_id = await create_booking_with_overlap_check(
            master_id=master.id, client_id=client_id,
            scheduled_at=scheduled_at,
            duration_minutes=service.duration_minutes,
            service_ids=[service.id],
            source="public",
        )
    except BookingConflictError:
        raise HTTPException(status_code=409, detail="Slot already taken")

    # Resolve cancel_token to return to client + send master notification.
    from src.database import get_order_by_cancel_token
    # We need the token — re-read by order_id:
    from src.database import get_connection
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "SELECT cancel_token FROM orders WHERE id = ?", (order_id,)
        )
        cancel_token = (await cur.fetchone())["cancel_token"]
    finally:
        await conn.close()

    # Notification to master (best-effort).
    master_bot = getattr(request.app.state, "master_bot", None)
    if master_bot:
        try:
            await master_bot.send_message(
                chat_id=master.tg_id,
                text=(
                    f"🆕 Новая запись\n"
                    f"{body.name}, {phone}\n"
                    f"{service.name}, {body.date} {body.start}"
                ),
            )
        except Exception as e:
            logger.warning(f"master notify failed: {e}")

    cancel_url = f"{MINIAPP_URL.rsplit('/', 1)[0]}/b/{cancel_token}"
    return JSONResponse(
        status_code=201,
        content={"order_id": order_id, "cancel_token": cancel_token,
                 "cancel_url": cancel_url},
    )
```

You'll also need `create_client_minimal` in `src/database.py` — small helper that inserts into `clients` with optional `tg_id`/`tg_username` and returns the id.

**Step 4: Pass.**

**Step 5: Commit**

```bash
git commit -m "feat(api): public booking endpoints (slots query + book)"
```

---

## Task 11: Cancellation API + page

**Files:**
- Modify: `src/api/routers/public_booking.py` — add `POST /api/public/cancel/{token}`.
- Create: `src/api/templates/booking_cancel.html` — minimal Jinja page.
- Modify: `src/api/routers/landing.py` — add `GET /b/{token}` handler that loads order, renders template.
- Modify: `tests/test_self_booking.py`

Endpoints:

```python
# in public_booking.py
from src.database import cancel_booking_by_token, get_order_by_cancel_token
from src.api.routers.master.dashboard import _moscow_now  # or just datetime.now()

@router.post("/public/cancel/{token}")
async def public_cancel(token: str, request: Request):
    order = await get_order_by_cancel_token(token)
    if not order:
        raise HTTPException(status_code=404, detail="Booking not found")
    if order["status"] in ("cancelled", "done"):
        raise HTTPException(status_code=409, detail="Already finalized")

    master = await get_master_by_id(order["master_id"])
    cutoff = master.booking_cancel_cutoff_hours
    scheduled = datetime.fromisoformat(order["scheduled_at"].replace(" ", "T"))
    if (scheduled - datetime.now()).total_seconds() < cutoff * 3600:
        raise HTTPException(status_code=403, detail="Cutoff passed — contact master")

    cancelled_id = await cancel_booking_by_token(token)
    if cancelled_id is None:
        raise HTTPException(status_code=409, detail="Already finalized")

    master_bot = getattr(request.app.state, "master_bot", None)
    if master_bot:
        try:
            await master_bot.send_message(
                chat_id=master.tg_id,
                text=f"❌ Клиент отменил запись\norder #{cancelled_id}",
            )
        except Exception as e:
            logger.warning(f"cancel notify failed: {e}")

    return {"ok": True}
```

`GET /b/{token}` in `landing.py`:

```python
@router.get("/b/{token}", response_class=HTMLResponse)
async def booking_cancel_page(request: Request, token: str):
    from src.database import get_order_by_cancel_token, get_master_by_id, get_service_by_id
    order = await get_order_by_cancel_token(token)
    if not order:
        return templates.TemplateResponse(
            request=request, name="booking_cancel.html",
            context={"missing": True}, status_code=404,
        )
    master = await get_master_by_id(order["master_id"])
    # Fetch service via order_items.
    conn = await db.get_connection()
    try:
        cur = await conn.execute(
            "SELECT service_id FROM order_items WHERE order_id = ? LIMIT 1",
            (order["id"],),
        )
        row = await cur.fetchone()
        service = await get_service_by_id(row["service_id"]) if row else None
    finally:
        await conn.close()
    scheduled = order["scheduled_at"]
    cutoff_passed = (
        datetime.fromisoformat(scheduled.replace(" ", "T")) - datetime.now()
    ).total_seconds() < master.booking_cancel_cutoff_hours * 3600
    return templates.TemplateResponse(
        request=request, name="booking_cancel.html",
        context={
            "missing": False,
            "service_name": service.name if service else "услуга",
            "master_name": master.name,
            "master_phone": master.phone,
            "scheduled_at": scheduled,
            "status": order["status"],
            "can_cancel": order["status"] == "confirmed" and not cutoff_passed,
            "token": token,
        },
    )
```

`booking_cancel.html` is a minimal page with a button that POSTs to `/api/public/cancel/{token}` via fetch. Keep ≤80 lines.

Tests: GET renders 200, POST cancellation works, POST after cutoff returns 403, POST with bogus token returns 404.

Commit: `feat(api): public cancellation page and endpoint`.

---

## Task 12: client_bot /book command

**Files:**
- Modify: `src/client_bot.py` — add a `/book` command handler that walks the user through a 4-step inline flow and POSTs to the same public booking helper (or call the DB layer directly — bypassing HTTP avoids initData/ratelimit complications since the bot already has tg_id).
- Modify: `tests/test_self_booking.py`

Skeleton (call DB layer directly, since the bot already has authenticated tg_id):

```python
# src/client_bot.py
@router.message(Command("book"))
async def cmd_book(message: Message, bot: Bot):
    masters = await get_all_client_masters_by_tg_id(message.from_user.id)
    if not masters:
        await message.answer("Вы не привязаны к мастеру.")
        return
    # If one master — pick automatically; otherwise show inline picker.
    # … For brevity: assume one master in MVP; multi-master picker is a follow-up.
    master_id = masters[0]["master_id"]
    services = await get_services(master_id, active_only=True)
    if not services:
        await message.answer("У мастера нет активных услуг.")
        return
    # Build inline keyboard with services.
    # … (see existing keyboards.py patterns for inline picker examples)
```

This task is the heaviest of the twelve in code volume; treat it as **the** follow-up if time pressed and ship the rest. Keep the bot's confirmation step calling `create_booking_with_overlap_check` directly with `source="telegram_bot"`. Same notification path.

Tests: a happy-path integration test that simulates `/book` via the bot's existing test harness pattern (see `tests/test_client_bot_runtime.py` for reference) — but at minimum, verify that calling the booking helper with `source="telegram_bot"` lands an order and master gets notified.

Commit: `feat(client_bot): /book command (thin wrapper over booking helper)`.

---

## Verification after all tasks

```bash
env $TEST_ENV python3.11 -m unittest discover -s tests
```
Expected: 64 (prior) + 16 (new) = **80 tests OK** (≈ ±2 depending on test consolidation).

```bash
env $TEST_ENV python3.11 -m compileall -q src tests main.py && echo COMPILE OK
```

Manual smoke after deploy:
- In master Mini App (via direct API for now, frontend follow-up): `PUT /api/master/booking-settings` enable=true, set weekly Mon-Fri 10:00-18:00.
- Open `https://api.abooking.org/api/public/{invite_token}/slots?service_id=X&date=YYYY-MM-DD` — should return slots JSON.
- Open `https://api.abooking.org/m/{token}/book` — manual booking flow renders.
- POST a booking → 201 + master gets a Telegram push.
- Open the returned `cancel_url` → cancellation page renders.
- POST cancel → 200 + master gets cancellation push.

## Out of scope reminders

These are tracked in the design doc — do not invent them during implementation:
- Master Mini App React UI (settings panel, calendar visual). Backend API from this plan is the contract.
- Multi-tz support. Everything in MSK.
- Multi-service bundling.
- SMS / email channels.
- Rescheduling by client.
