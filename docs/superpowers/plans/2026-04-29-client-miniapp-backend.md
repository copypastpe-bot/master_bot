# Client Mini App Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend support for the redesigned client Mini App, using the current project architecture instead of blindly following the Claude-written TЗ.

**Architecture:** Add a focused client-app API router under `/api/client/...` and keep legacy `/api/me`, `/api/orders`, `/api/bonuses`, `/api/promos`, `/api/services` working. Store text reviews in a new `reviews` table, keep quick bot feedback in `orders.rating`, keep client confirmation in `orders.client_confirmed`, and use existing `campaigns` as publication-shaped news for now. Simplify `client_bot.py` only as the Mini App entry point; do not redesign notifications in this plan.

**Tech Stack:** Python 3, FastAPI, aiogram 3, aiosqlite, SQLite migrations, `unittest` for local regression tests.

---

## Required Context

Read before implementing:

- `CLAUDE.md`
- `docs/superpowers/specs/2026-04-29-client-miniapp-backend-design.md`
- `prompts/files/PROMPT_CLIENT_APP_CODEX.md`
- `prompts/files/PROMPT_CLIENT_APP_CLAUDE_CODE.md`
- `src/database.py`
- `src/api/app.py`
- `src/api/dependencies.py`
- `src/api/routers/client_masters.py`
- `src/client_bot.py`

Important constraints:

- Do not create `orders.status = 'confirmed_by_client'`.
- Do not add a `publications` table in this pass.
- Do not redesign the React client Mini App in this pass.
- Do not rewrite client-bot notification flows in this pass.
- Existing dirty files may be present. Do not revert or include unrelated changes.

---

## File Structure

Create:

- `migrations/014_client_app_reviews.sql` - schema for text reviews and `notify_bonuses`.
- `src/api/routers/client_app.py` - new client Mini App endpoints.
- `tests/test_client_app_database.py` - database behavior tests using temporary SQLite.
- `tests/test_client_app_api_import.py` - router/app import smoke tests.

Modify:

- `src/database.py` - add review, activity/history, settings, public profile, and client app helper functions.
- `src/models.py` - add `notify_bonuses` to `MasterClient`.
- `src/api/app.py` - include the new router.
- `src/api/routers/client_masters.py` - normalize `/api/client/masters` response for frontend compatibility.
- `src/client_bot.py` - simplify `/start` entry rendering while preserving invite-token linking.
- `src/keyboards.py` - add a compact Mini App entry keyboard if needed.

Do not modify:

- React UI files under `miniapp/src/pages` for this backend pass.
- Master Mini App screens.
- Payment/subscription behavior.

---

## Task 1: Add Migration For Reviews And Bonus Notification Toggle

**Files:**
- Create: `migrations/014_client_app_reviews.sql`
- Test: `tests/test_client_app_database.py`

- [ ] **Step 1: Write the failing migration test**

Create `tests/test_client_app_database.py` with this initial content:

```python
import os
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
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python -m unittest tests.test_client_app_database.ClientAppDatabaseTest.test_init_db_creates_reviews_and_notify_bonuses -v
```

Expected: FAIL because `reviews` and/or `notify_bonuses` do not exist.

- [ ] **Step 3: Add the migration**

Create `migrations/014_client_app_reviews.sql`:

```sql
-- Migration 014: client Mini App reviews and notification settings

CREATE TABLE IF NOT EXISTS reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id       INTEGER NOT NULL REFERENCES masters(id),
    client_id       INTEGER NOT NULL REFERENCES clients(id),
    order_id        INTEGER REFERENCES orders(id),
    rating          INTEGER,
    text            TEXT NOT NULL,
    is_visible      BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(order_id)
);

CREATE INDEX IF NOT EXISTS idx_reviews_master
ON reviews(master_id, is_visible, created_at DESC);

ALTER TABLE master_clients ADD COLUMN notify_bonuses BOOLEAN DEFAULT TRUE;
```

Note: `init_db()` already skips duplicate-column migration errors. This matches the project’s existing migration style.

- [ ] **Step 4: Run the test and verify it passes**

Run:

```bash
python -m unittest tests.test_client_app_database.ClientAppDatabaseTest.test_init_db_creates_reviews_and_notify_bonuses -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git status --short
git add migrations/014_client_app_reviews.sql tests/test_client_app_database.py
git commit -m "Add client app review schema"
```

Only include the migration and test file.

---

## Task 2: Add Database Helpers For Reviews

**Files:**
- Modify: `src/database.py`
- Modify: `tests/test_client_app_database.py`

- [ ] **Step 1: Add failing review tests**

Append these methods to `ClientAppDatabaseTest`:

```python
    async def _seed_review_fixture(self):
        conn = await db.get_connection()
        try:
            await conn.execute(
                """
                INSERT INTO masters (id, tg_id, name, sphere, invite_token)
                VALUES (1, 1001, 'Анна Иванова', 'Маникюр', 'invite_anna')
                """
            )
            await conn.execute(
                """
                INSERT INTO clients (id, tg_id, name, phone)
                VALUES (1, 2001, 'Мария Петрова', '+79990000000')
                """
            )
            await conn.execute(
                """
                INSERT INTO master_clients (master_id, client_id, bonus_balance)
                VALUES (1, 1, 120)
                """
            )
            await conn.execute(
                """
                INSERT INTO orders (id, master_id, client_id, status, scheduled_at, amount_total)
                VALUES (1, 1, 1, 'done', '2026-04-20 10:00:00', 3000)
                """
            )
            await conn.commit()
        finally:
            await conn.close()

    async def test_create_review_returns_id_and_prevents_duplicate_order_review(self):
        await self._seed_review_fixture()

        review_id = await db.create_review(
            master_id=1,
            client_id=1,
            order_id=1,
            text="Отличный визит, всё понравилось",
            rating=5,
        )
        self.assertIsInstance(review_id, int)

        existing = await db.get_review_by_order(1)
        self.assertEqual(existing["id"], review_id)
        self.assertEqual(existing["text"], "Отличный визит, всё понравилось")

        with self.assertRaises(Exception):
            await db.create_review(
                master_id=1,
                client_id=1,
                order_id=1,
                text="Повторный отзыв по тому же заказу",
                rating=5,
            )

    async def test_get_reviews_shortens_client_name_and_hides_invisible_reviews(self):
        await self._seed_review_fixture()
        review_id = await db.create_review(
            master_id=1,
            client_id=1,
            order_id=1,
            text="Очень хороший специалист",
            rating=5,
        )

        reviews = await db.get_reviews(master_id=1, limit=20, offset=0)
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["client_name"], "Мария П.")
        self.assertEqual(reviews[0]["rating"], 5)

        changed = await db.toggle_review_visibility(review_id, master_id=1, is_visible=False)
        self.assertTrue(changed)

        reviews_after_hide = await db.get_reviews(master_id=1, limit=20, offset=0)
        self.assertEqual(reviews_after_hide, [])
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python -m unittest tests.test_client_app_database.ClientAppDatabaseTest -v
```

Expected: FAIL because `create_review`, `get_review_by_order`, `get_reviews`, and `toggle_review_visibility` are missing.

- [ ] **Step 3: Implement review helpers**

Add these helpers near other client/order helpers in `src/database.py`:

```python
def _short_client_name(name: str | None) -> str:
    """Return public client name like 'Анна М.'."""
    if not name:
        return "Клиент"
    parts = str(name).strip().split()
    if len(parts) >= 2 and parts[1]:
        return f"{parts[0]} {parts[1][0]}."
    return parts[0] if parts else "Клиент"


async def create_review(
    master_id: int,
    client_id: int,
    order_id: int,
    text: str,
    rating: int | None = None,
) -> int:
    """Create a public text review. One review per order."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO reviews (master_id, client_id, order_id, rating, text)
            VALUES (?, ?, ?, ?, ?)
            """,
            (master_id, client_id, order_id, rating, text),
        )
        await conn.commit()
        return cursor.lastrowid
    finally:
        await conn.close()


async def get_review_by_order(order_id: int) -> Optional[dict]:
    """Return review for an order if it exists."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM reviews WHERE order_id = ?",
            (order_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def get_reviews(master_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
    """Return visible public reviews for a specialist."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT r.*, c.name as raw_client_name
            FROM reviews r
            JOIN clients c ON c.id = r.client_id
            WHERE r.master_id = ? AND r.is_visible = 1
            ORDER BY r.created_at DESC, r.id DESC
            LIMIT ? OFFSET ?
            """,
            (master_id, limit, offset),
        )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["client_name"] = _short_client_name(item.pop("raw_client_name", None))
            result.append(item)
        return result
    finally:
        await conn.close()


async def count_reviews(master_id: int) -> int:
    """Count visible public reviews for a specialist."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT COUNT(*) as cnt FROM reviews WHERE master_id = ? AND is_visible = 1",
            (master_id,),
        )
        row = await cursor.fetchone()
        return int(row["cnt"]) if row else 0
    finally:
        await conn.close()


async def toggle_review_visibility(review_id: int, master_id: int, is_visible: bool) -> bool:
    """Hide or show a public review."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            UPDATE reviews
            SET is_visible = ?
            WHERE id = ? AND master_id = ?
            """,
            (1 if is_visible else 0, review_id, master_id),
        )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
python -m unittest tests.test_client_app_database.ClientAppDatabaseTest -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git status --short
git add src/database.py tests/test_client_app_database.py
git commit -m "Add client review database helpers"
```

---

## Task 3: Add Database Helpers For Client Settings

**Files:**
- Modify: `src/database.py`
- Modify: `src/models.py`
- Modify: `tests/test_client_app_database.py`

- [ ] **Step 1: Add failing settings sync test**

Append this method to `ClientAppDatabaseTest`:

```python
    async def test_update_client_notification_settings_syncs_legacy_flags(self):
        await self._seed_review_fixture()

        ok = await db.update_client_notification_settings(
            master_id=1,
            client_id=1,
            notify_reminders=False,
            notify_marketing=False,
            notify_bonuses=False,
        )
        self.assertTrue(ok)

        conn = await db.get_connection()
        try:
            cursor = await conn.execute(
                """
                SELECT notify_reminders, notify_24h, notify_1h,
                       notify_marketing, notify_promos, notify_bonuses
                FROM master_clients
                WHERE master_id = 1 AND client_id = 1
                """
            )
            row = await cursor.fetchone()
        finally:
            await conn.close()

        self.assertEqual(dict(row), {
            "notify_reminders": 0,
            "notify_24h": 0,
            "notify_1h": 0,
            "notify_marketing": 0,
            "notify_promos": 0,
            "notify_bonuses": 0,
        })
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python -m unittest tests.test_client_app_database.ClientAppDatabaseTest.test_update_client_notification_settings_syncs_legacy_flags -v
```

Expected: FAIL because `update_client_notification_settings` is missing.

- [ ] **Step 3: Implement settings helper and whitelists**

In `src/models.py`, add the field to `MasterClient`:

```python
    notify_bonuses: bool = True
```

In `src/database.py`, add `notify_bonuses` to both `ALLOWED_MASTER_CLIENT_FIELDS` and `ALLOWED_NOTIFICATION_FIELDS`.

In `_parse_master_client_row`, pass the new field:

```python
        notify_bonuses=bool(row["notify_bonuses"]) if "notify_bonuses" in row.keys() else True,
```

Then add:

```python
async def update_client_notification_settings(
    master_id: int,
    client_id: int,
    notify_reminders: bool | None = None,
    notify_marketing: bool | None = None,
    notify_bonuses: bool | None = None,
) -> bool:
    """Update client notification settings for the redesigned Mini App."""
    updates: dict[str, int] = {}

    if notify_reminders is not None:
        value = 1 if notify_reminders else 0
        updates["notify_reminders"] = value
        updates["notify_24h"] = value
        updates["notify_1h"] = value

    if notify_marketing is not None:
        value = 1 if notify_marketing else 0
        updates["notify_marketing"] = value
        updates["notify_promos"] = value

    if notify_bonuses is not None:
        updates["notify_bonuses"] = 1 if notify_bonuses else 0

    if not updates:
        return True

    _validate_fields(set(updates.keys()), ALLOWED_MASTER_CLIENT_FIELDS, "master_clients")
    set_clause = ", ".join(f"{field} = ?" for field in updates)
    values = list(updates.values()) + [master_id, client_id]

    conn = await get_connection()
    try:
        cursor = await conn.execute(
            f"UPDATE master_clients SET {set_clause} WHERE master_id = ? AND client_id = ?",
            values,
        )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
python -m unittest tests.test_client_app_database.ClientAppDatabaseTest -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git status --short
git add src/database.py src/models.py tests/test_client_app_database.py
git commit -m "Add client notification settings sync"
```

---

## Task 4: Add Database Helpers For Client App Orders, Activity, Publications, And Profiles

**Files:**
- Modify: `src/database.py`
- Modify: `tests/test_client_app_database.py`

- [ ] **Step 1: Add failing feed/profile tests**

Append this method to `ClientAppDatabaseTest`:

```python
    async def test_client_app_feed_profile_and_publications_use_current_architecture(self):
        await self._seed_review_fixture()
        conn = await db.get_connection()
        try:
            await conn.execute(
                """
                INSERT INTO services (id, master_id, name, price, description, is_active)
                VALUES (1, 1, 'Маникюр', 3000, 'Классический маникюр', 1)
                """
            )
            await conn.execute(
                """
                INSERT INTO order_items (order_id, service_id, name, price)
                VALUES (1, 1, 'Маникюр', 3000)
                """
            )
            await conn.execute(
                """
                INSERT INTO bonus_log (master_id, client_id, order_id, type, amount, comment, created_at)
                VALUES (1, 1, NULL, 'manual', 50, 'Подарок', '2026-04-21 10:00:00')
                """
            )
            await conn.execute(
                """
                INSERT INTO campaigns (master_id, type, title, text, active_from, active_to, created_at)
                VALUES (1, 'promo', 'Скидка', 'Минус 10%', '2026-04-01', '2026-12-31', '2026-04-22 10:00:00')
                """
            )
            await conn.execute("UPDATE orders SET client_confirmed = 1 WHERE id = 1")
            await conn.commit()
        finally:
            await conn.close()

        orders = await db.get_client_orders_for_app(master_id=1, client_id=1, limit=20, offset=0)
        self.assertEqual(orders[0]["display_status"], "confirmed")
        self.assertEqual(orders[0]["services"], "Маникюр")
        self.assertFalse(orders[0]["has_review"])

        feed = await db.get_client_activity_feed(master_id=1, client_id=1, limit=10, offset=0)
        self.assertEqual({item["type"] for item in feed}, {"order", "bonus"})

        publications, total = await db.get_client_publications(master_id=1, limit=20, offset=0)
        self.assertEqual(total, 1)
        self.assertEqual(publications[0]["type"], "promo")
        self.assertEqual(publications[0]["title"], "Скидка")

        profile = await db.get_master_public_profile(master_id=1)
        self.assertEqual(profile["name"], "Анна Иванова")
        self.assertEqual(profile["review_count"], 0)
        self.assertGreaterEqual(profile["years_on_platform"], 0)
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python -m unittest tests.test_client_app_database.ClientAppDatabaseTest.test_client_app_feed_profile_and_publications_use_current_architecture -v
```

Expected: FAIL because feed/profile/publication helpers are missing.

- [ ] **Step 3: Implement display status helper**

Add to `src/database.py`:

```python
def _client_display_status(order: dict) -> str:
    """Return client-facing order status without changing stored status."""
    status = order.get("status") or "new"
    if status == "done":
        return "done"
    if status == "cancelled":
        return "cancelled"
    if status == "moved":
        return "moved"
    if order.get("client_confirmed"):
        return "confirmed"
    if order.get("reminder_24h_sent"):
        return "reminder"
    if status == "confirmed":
        return "new"
    return status
```

- [ ] **Step 4: Implement order and feed helpers**

Add to `src/database.py`:

```python
async def get_client_orders_for_app(
    master_id: int,
    client_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """Return client orders shaped for the redesigned Mini App."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT
                o.*,
                GROUP_CONCAT(oi.name, ', ') as services,
                CASE WHEN r.id IS NULL THEN 0 ELSE 1 END as has_review
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN reviews r ON r.order_id = o.id
            WHERE o.master_id = ? AND o.client_id = ?
            GROUP BY o.id
            ORDER BY
                CASE
                    WHEN o.status IN ('confirmed', 'new') THEN 0
                    WHEN o.status = 'done' THEN 1
                    WHEN o.status = 'cancelled' THEN 2
                    ELSE 3
                END,
                o.scheduled_at DESC
            LIMIT ? OFFSET ?
            """,
            (master_id, client_id, limit, offset),
        )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["has_review"] = bool(item.get("has_review"))
            item["client_confirmed"] = bool(item.get("client_confirmed")) if "client_confirmed" in item else False
            item["display_status"] = _client_display_status(item)
            item["type"] = "order"
            result.append(item)
        return result
    finally:
        await conn.close()


async def get_client_activity_feed(
    master_id: int,
    client_id: int,
    limit: int = 10,
    offset: int = 0,
) -> list[dict]:
    """Return mixed order and standalone bonus activity for the client."""
    orders = await get_client_orders_for_app(master_id, client_id, limit=limit, offset=0)

    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT
                id,
                'bonus' as type,
                created_at,
                amount,
                comment,
                type as bonus_type
            FROM bonus_log
            WHERE master_id = ? AND client_id = ? AND order_id IS NULL
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (master_id, client_id, limit),
        )
        bonus_rows = [dict(row) for row in await cursor.fetchall()]
    finally:
        await conn.close()

    items = orders + bonus_rows
    items.sort(key=lambda item: str(item.get("scheduled_at") or item.get("created_at") or ""), reverse=True)
    return items[offset:offset + limit]
```

- [ ] **Step 5: Implement publications and profile helpers**

Add to `src/database.py`:

```python
async def get_client_publications(
    master_id: int,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Return active campaigns in publication-shaped format."""
    conn = await get_connection()
    try:
        today = date.today().isoformat()
        count_cursor = await conn.execute(
            """
            SELECT COUNT(*) as cnt
            FROM campaigns
            WHERE master_id = ?
              AND type = 'promo'
              AND (active_from IS NULL OR active_from <= ?)
              AND (active_to IS NULL OR active_to >= ?)
            """,
            (master_id, today, today),
        )
        count_row = await count_cursor.fetchone()
        total = int(count_row["cnt"]) if count_row else 0

        cursor = await conn.execute(
            """
            SELECT *
            FROM campaigns
            WHERE master_id = ?
              AND type = 'promo'
              AND (active_from IS NULL OR active_from <= ?)
              AND (active_to IS NULL OR active_to >= ?)
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (master_id, today, today, limit, offset),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "type": "promo",
                "title": row["title"],
                "text": row["text"],
                "image_url": None,
                "scheduled_date": None,
                "active_from": row["active_from"],
                "active_to": row["active_to"],
                "created_at": row["created_at"],
            }
            for row in rows
        ], total
    finally:
        await conn.close()


async def get_master_public_profile(master_id: int) -> Optional[dict]:
    """Return public specialist profile data for connected or public views."""
    master = await get_master_by_id(master_id)
    if not master:
        return None

    review_count = await count_reviews(master_id)
    created_at = master.created_at or _utcnow()
    if isinstance(created_at, str):
        created_dt = _parse_db_datetime(created_at) or _utcnow()
    else:
        created_dt = created_at
    years_on_platform = max(0, int((_utcnow() - created_dt).days // 365))

    return {
        "id": master.id,
        "name": master.name,
        "sphere": master.sphere,
        "bio": master.contacts,
        "contacts": master.contacts,
        "phone": master.phone,
        "telegram": master.telegram,
        "instagram": master.instagram,
        "website": master.website,
        "contact_address": master.contact_address,
        "socials": master.socials,
        "work_hours": master.work_hours,
        "work_mode": master.work_mode,
        "work_address_default": master.work_address_default,
        "invite_token": master.invite_token,
        "review_count": review_count,
        "years_on_platform": years_on_platform,
        "created_at": created_dt.isoformat() if created_dt else None,
    }


async def get_master_by_invite_token_public(invite_token: str) -> Optional[dict]:
    """Return public specialist profile by invite token."""
    master = await get_master_by_invite_token(invite_token)
    if not master:
        return None
    return await get_master_public_profile(master.id)
```

- [ ] **Step 6: Run tests and verify they pass**

Run:

```bash
python -m unittest tests.test_client_app_database.ClientAppDatabaseTest -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git status --short
git add src/database.py tests/test_client_app_database.py
git commit -m "Add client app feed database helpers"
```

---

## Task 5: Add Database Helper For Client Confirmation

**Files:**
- Modify: `src/database.py`
- Modify: `tests/test_client_app_database.py`

- [ ] **Step 1: Add failing confirmation test**

Append this method to `ClientAppDatabaseTest`:

```python
    async def test_confirm_order_by_client_uses_client_confirmed_flag(self):
        await self._seed_review_fixture()
        conn = await db.get_connection()
        try:
            await conn.execute("UPDATE orders SET status = 'confirmed', client_confirmed = 0 WHERE id = 1")
            await conn.commit()
        finally:
            await conn.close()

        ok = await db.confirm_order_by_client(order_id=1, client_id=1)
        self.assertTrue(ok)

        conn = await db.get_connection()
        try:
            cursor = await conn.execute("SELECT status, client_confirmed FROM orders WHERE id = 1")
            row = await cursor.fetchone()
        finally:
            await conn.close()

        self.assertEqual(row["status"], "confirmed")
        self.assertEqual(row["client_confirmed"], 1)
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python -m unittest tests.test_client_app_database.ClientAppDatabaseTest.test_confirm_order_by_client_uses_client_confirmed_flag -v
```

Expected: FAIL because `confirm_order_by_client` is missing.

- [ ] **Step 3: Implement helper**

Add to `src/database.py`:

```python
async def confirm_order_by_client(order_id: int, client_id: int) -> bool:
    """Confirm a client order using existing client_confirmed architecture."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            UPDATE orders
            SET client_confirmed = 1
            WHERE id = ?
              AND client_id = ?
              AND status IN ('new', 'confirmed')
            """,
            (order_id, client_id),
        )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
python -m unittest tests.test_client_app_database.ClientAppDatabaseTest -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git status --short
git add src/database.py tests/test_client_app_database.py
git commit -m "Add client order confirmation helper"
```

---

## Task 6: Add Client App API Router

**Files:**
- Create: `src/api/routers/client_app.py`
- Create: `tests/test_client_app_api_import.py`
- Modify: `src/api/app.py`

- [ ] **Step 1: Add failing API import test**

Create `tests/test_client_app_api_import.py`:

```python
import unittest


class ClientAppApiImportTest(unittest.TestCase):
    def test_client_app_router_is_registered(self):
        from src.api.app import app

        paths = {route.path for route in app.routes}
        self.assertIn("/api/client/master/{master_id}/profile", paths)
        self.assertIn("/api/client/master/{master_id}/activity", paths)
        self.assertIn("/api/client/master/{master_id}/history", paths)
        self.assertIn("/api/client/master/{master_id}/settings", paths)
        self.assertIn("/api/client/orders/{order_id}/confirm", paths)
        self.assertIn("/api/client/orders/{order_id}/review", paths)
        self.assertIn("/api/public/master/{invite_token}", paths)
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python -m unittest tests.test_client_app_api_import.ClientAppApiImportTest.test_client_app_router_is_registered -v
```

Expected: FAIL because the router is not registered.

- [ ] **Step 3: Create router skeleton with real dependencies**

Create `src/api/routers/client_app.py`:

```python
"""Redesigned client Mini App endpoints."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.auth import extract_tg_id, validate_init_data
from src.config import APP_ENV, CLIENT_BOT_TOKEN
from src.database import (
    anonymize_client,
    confirm_order_by_client,
    create_review,
    get_client_activity_feed,
    get_client_by_tg_id,
    get_client_masters,
    get_client_orders_for_app,
    get_client_publications,
    get_master_by_id,
    get_master_client,
    get_master_public_profile,
    get_master_by_invite_token_public,
    get_review_by_order,
    get_reviews,
    get_services,
    update_client_notification_settings,
)
from src.models import Client, Master, MasterClient

router = APIRouter(tags=["client-app"])


def _review_response(review: dict) -> dict:
    return {
        "id": review["id"],
        "client_name": review.get("client_name") or "Клиент",
        "text": review["text"],
        "rating": review.get("rating"),
        "created_at": review.get("created_at"),
    }


async def _require_client_master(
    requested_master_id: int,
    x_init_data: Optional[str],
) -> tuple[Client, Master, MasterClient]:
    """Resolve a client against the path master_id.

    Do not use get_current_client here: that dependency chooses the master from
    query ?master_id=, while the redesigned API has master_id in the path.
    """
    client = await _resolve_client(x_init_data)
    master = await get_master_by_id(requested_master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    master_client = await get_master_client(master.id, client.id)
    if not master_client:
        raise HTTPException(status_code=403, detail="Not linked to this master")
    return client, master, master_client


async def _resolve_tg_id(x_init_data: Optional[str]) -> int:
    """Validate client initData and return Telegram user id."""
    if not x_init_data:
        raise HTTPException(status_code=401, detail="Missing X-Init-Data header")
    if APP_ENV == "development" and x_init_data == "dev":
        return 999999999
    validated = validate_init_data(x_init_data, CLIENT_BOT_TOKEN)
    if not validated:
        raise HTTPException(status_code=401, detail="Invalid initData")
    tg_id = extract_tg_id(validated)
    if not tg_id:
        raise HTTPException(status_code=401, detail="No user data")
    return tg_id


async def _resolve_client(x_init_data: Optional[str]) -> Client:
    """Return authenticated client without choosing a master."""
    tg_id = await _resolve_tg_id(x_init_data)
    client = await get_client_by_tg_id(tg_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not registered")
    return client


@router.get("/client/master/{master_id}/profile")
async def get_client_master_profile(
    master_id: int,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    client, master, master_client = await _require_client_master(master_id, x_init_data)
    profile = await get_master_public_profile(master.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Master not found")

    masters = await get_client_masters(client.id)
    current = next((item for item in masters if item["master_id"] == master.id), {})

    return {
        **profile,
        "bonus_balance": master_client.bonus_balance,
        "visit_count": current.get("visit_count") or current.get("order_count") or 0,
    }


@router.get("/client/master/{master_id}/activity")
async def get_client_master_activity(
    master_id: int,
    limit: int = Query(3, ge=1, le=50),
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    client, master, _master_client = await _require_client_master(master_id, x_init_data)
    items = await get_client_activity_feed(master.id, client.id, limit=limit, offset=0)
    return {"items": items}


@router.get("/client/master/{master_id}/history")
async def get_client_master_history(
    master_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    client, master, master_client = await _require_client_master(master_id, x_init_data)
    items = await get_client_activity_feed(master.id, client.id, limit=limit, offset=offset)
    return {"items": items, "total": len(items), "bonus_balance": master_client.bonus_balance}


@router.get("/client/master/{master_id}/services")
async def get_client_master_services(
    master_id: int,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    _client, master, _master_client = await _require_client_master(master_id, x_init_data)
    services = await get_services(master.id, active_only=True)
    return {
        "services": [
            {
                "id": service.id,
                "name": service.name,
                "price": service.price,
                "description": service.description,
            }
            for service in services
        ]
    }


@router.get("/client/master/{master_id}/news")
async def get_client_master_news(
    master_id: int,
    limit: int = Query(1, ge=1, le=20),
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    _client, master, _master_client = await _require_client_master(master_id, x_init_data)
    publications, total = await get_client_publications(master.id, limit=limit, offset=0)
    return {"publications": publications, "total": total}


@router.get("/client/master/{master_id}/publications")
async def get_client_master_publications(
    master_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    _client, master, _master_client = await _require_client_master(master_id, x_init_data)
    publications, total = await get_client_publications(master.id, limit=limit, offset=offset)
    return {"publications": publications, "total": total}


@router.get("/client/master/{master_id}/settings")
async def get_client_master_settings(
    master_id: int,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    _client, _master, master_client = await _require_client_master(master_id, x_init_data)
    return {
        "notify_reminders": master_client.notify_reminders,
        "notify_marketing": master_client.notify_marketing,
        "notify_bonuses": getattr(master_client, "notify_bonuses", True),
    }


class ClientNotificationSettingsPatch(BaseModel):
    notify_reminders: Optional[bool] = None
    notify_marketing: Optional[bool] = None
    notify_bonuses: Optional[bool] = None


@router.patch("/client/master/{master_id}/settings")
async def patch_client_master_settings(
    master_id: int,
    body: ClientNotificationSettingsPatch,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    client, master, _master_client = await _require_client_master(master_id, x_init_data)
    ok = await update_client_notification_settings(
        master_id=master.id,
        client_id=client.id,
        notify_reminders=body.notify_reminders,
        notify_marketing=body.notify_marketing,
        notify_bonuses=body.notify_bonuses,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Master-client link not found")
    return {"ok": True}


@router.post("/client/orders/{order_id}/confirm")
async def confirm_client_order(
    order_id: int,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    client = await _resolve_client(x_init_data)
    ok = await confirm_order_by_client(order_id=order_id, client_id=client.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Order not found or cannot be confirmed")
    return {"ok": True, "client_confirmed": True, "display_status": "confirmed"}


class ReviewCreateRequest(BaseModel):
    text: str = Field(..., min_length=10)
    rating: Optional[int] = Field(None, ge=1, le=5)


@router.post("/client/orders/{order_id}/review")
async def create_client_order_review(
    order_id: int,
    body: ReviewCreateRequest,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    client = await _resolve_client(x_init_data)
    masters = await get_client_masters(client.id)
    orders = []
    master_id = None
    for item in masters:
        current_orders = await get_client_orders_for_app(item["master_id"], client.id, limit=100, offset=0)
        found = next((order for order in current_orders if order["id"] == order_id), None)
        if found:
            orders = current_orders
            master_id = item["master_id"]
            break
    order = next((item for item in orders if item["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get("status") != "done":
        raise HTTPException(status_code=409, detail="Review is available only for completed orders")
    if await get_review_by_order(order_id):
        raise HTTPException(status_code=409, detail="Review already exists")

    review_id = await create_review(
        master_id=master_id,
        client_id=client.id,
        order_id=order_id,
        text=body.text.strip(),
        rating=body.rating,
    )
    return {"ok": True, "review_id": review_id}


@router.get("/client/master/{master_id}/reviews")
async def get_client_master_reviews(
    master_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    _client, master, _master_client = await _require_client_master(master_id, x_init_data)
    reviews = await get_reviews(master.id, limit=limit, offset=offset)
    return {"reviews": [_review_response(r) for r in reviews], "total": len(reviews)}


@router.get("/public/master/{invite_token}")
async def get_public_master(invite_token: str):
    profile = await get_master_by_invite_token_public(invite_token)
    if not profile:
        raise HTTPException(status_code=404, detail="Master not found")
    services = await get_services(profile["id"], active_only=True)
    reviews = await get_reviews(profile["id"], limit=10, offset=0)
    return {
        **profile,
        "services": [
            {
                "id": service.id,
                "name": service.name,
                "price": service.price,
                "description": service.description,
            }
            for service in services
        ],
        "reviews": [_review_response(r) for r in reviews],
    }


@router.delete("/client/profile")
async def delete_client_profile(
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    client = await _resolve_client(x_init_data)
    ok = await anonymize_client(client.id)
    return {"ok": ok}
```

- [ ] **Step 4: Include router in app**

Modify `src/api/app.py`:

```python
from src.api.routers import client, orders, bonuses, promos, services
from src.api.routers import client_app
```

And include:

```python
app.include_router(client_app.router, prefix="/api")
```

- [ ] **Step 5: Run import test and fix issues**

Run:

```bash
python -m unittest tests.test_client_app_api_import.ClientAppApiImportTest -v
```

Expected: PASS.

- [ ] **Step 6: Run database tests**

Run:

```bash
python -m unittest tests.test_client_app_database.ClientAppDatabaseTest -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git status --short
git add src/api/routers/client_app.py src/api/app.py tests/test_client_app_api_import.py
git commit -m "Add redesigned client app API router"
```

---

## Task 7: Normalize `/api/client/masters`

**Files:**
- Modify: `src/database.py`
- Modify: `src/api/routers/client_masters.py`
- Modify: `tests/test_client_app_database.py`

- [ ] **Step 1: Add failing masters list test**

Append this method to `ClientAppDatabaseTest`:

```python
    async def test_get_client_masters_returns_new_and_legacy_field_names(self):
        await self._seed_review_fixture()

        masters = await db.get_client_masters(client_id=1)
        self.assertEqual(len(masters), 1)
        item = masters[0]
        self.assertEqual(item["master_id"], 1)
        self.assertEqual(item["name"], "Анна Иванова")
        self.assertEqual(item["master_name"], "Анна Иванова")
        self.assertEqual(item["visit_count"], 1)
        self.assertEqual(item["order_count"], 1)
        self.assertEqual(item["bonus_balance"], 120)
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python -m unittest tests.test_client_app_database.ClientAppDatabaseTest.test_get_client_masters_returns_new_and_legacy_field_names -v
```

Expected: FAIL because `name` and/or `visit_count` are missing.

- [ ] **Step 3: Update `get_client_masters`**

In `src/database.py`, adjust `get_client_masters` query to return both new and legacy aliases:

```sql
SELECT m.id as master_id,
       m.name as name,
       m.name as master_name,
       m.sphere,
       mc.bonus_balance,
       mc.last_visit,
       (SELECT COUNT(*) FROM orders
        WHERE master_id = m.id AND client_id = ? AND status = 'done') as visit_count,
       (SELECT COUNT(*) FROM orders
        WHERE master_id = m.id AND client_id = ? AND status = 'done') as order_count
FROM masters m
JOIN master_clients mc ON m.id = mc.master_id
WHERE mc.client_id = ?
ORDER BY mc.last_visit DESC NULLS LAST
```

Pass parameters `(client_id, client_id, client_id)`.

- [ ] **Step 4: Keep router response compatible**

`src/api/routers/client_masters.py` can keep returning `{"masters": masters, "count": len(masters)}`. Confirm it does not strip new keys.

- [ ] **Step 5: Run tests and verify they pass**

Run:

```bash
python -m unittest tests.test_client_app_database.ClientAppDatabaseTest -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git status --short
git add src/database.py src/api/routers/client_masters.py tests/test_client_app_database.py
git commit -m "Normalize client masters response"
```

---

## Task 8: Simplify Client Bot `/start` Entry Point

**Files:**
- Modify: `src/client_bot.py`
- Modify: `src/keyboards.py` if a helper keyboard is useful

- [ ] **Step 1: Inspect current `/start` flow carefully**

Read the full `cmd_start` handler in `src/client_bot.py`. Preserve:

- invite-token registration/linking behavior
- welcome bonus accrual
- consent handling if currently required
- multi-master linking behavior

Do not preserve old function navigation as the primary UI after the welcome message.

- [ ] **Step 2: Add a small rendering helper**

In `src/client_bot.py`, add a helper near `build_home_text`:

```python
def build_miniapp_entry_text(client, masters: list[dict]) -> str:
    """Build simplified client bot entry text."""
    if not masters:
        return (
            f"👋 Привет, {client.name}!\n\n"
            "Пока нет подключённых специалистов.\n"
            "Откройте ссылку-приглашение от специалиста, чтобы подключиться."
        )

    lines = [f"👋 Привет, {client.name}!", "", "Ваши специалисты:"]
    for item in masters:
        name = item.get("name") or item.get("master_name") or "Специалист"
        sphere = item.get("sphere")
        balance = item.get("bonus_balance") or 0
        title = f"• {name}"
        if sphere:
            title += f" · {sphere}"
        lines.append(title)
        lines.append(f"  Бонусы: {balance}")
    lines.extend(["", "Все функции доступны в приложении."])
    return "\n".join(lines)
```

- [ ] **Step 3: Add Mini App inline keyboard helper**

Either in `src/client_bot.py` or `src/keyboards.py`, create:

```python
def client_miniapp_entry_kb() -> InlineKeyboardMarkup:
    """Open redesigned client Mini App."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Открыть приложение",
            web_app=WebAppInfo(url=CLIENT_MINIAPP_URL),
        )],
    ])
```

If placed in `src/keyboards.py`, import `CLIENT_MINIAPP_URL`, `WebAppInfo`, and `InlineKeyboardButton` there. If placed in `src/client_bot.py`, reuse already imported aiogram types and config.

- [ ] **Step 4: Update non-invite existing-client branch**

In `cmd_start`, replace the branch that currently calls `show_home(...)` for already registered clients without token with sending/editing the simplified Mini App entry message:

```python
masters = await get_all_client_masters_by_tg_id(tg_id)
text = build_miniapp_entry_text(client, masters)
await bot.send_message(
    message.chat.id,
    text,
    reply_markup=client_miniapp_entry_kb(),
)
```

For invite-token flows that currently end with `show_home(...)`, keep the successful linking behavior but send the new entry message after linking instead of old functional home navigation.

- [ ] **Step 5: Manual syntax/import check**

Run:

```bash
python -m py_compile src/client_bot.py src/keyboards.py
```

Expected: no output and exit code 0.

- [ ] **Step 6: Commit**

Run:

```bash
git status --short
git add src/client_bot.py src/keyboards.py
git commit -m "Simplify client bot miniapp entry"
```

Only add `src/keyboards.py` if it was actually changed.

---

## Task 9: Final Verification

**Files:**
- No new files unless fixing issues found by verification.

- [ ] **Step 1: Run database tests**

Run:

```bash
python -m unittest tests.test_client_app_database.ClientAppDatabaseTest -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run API import tests**

Run:

```bash
python -m unittest tests.test_client_app_api_import.ClientAppApiImportTest -v
```

Expected: all tests PASS.

- [ ] **Step 3: Run Python compile checks**

Run:

```bash
python -m py_compile src/database.py src/api/app.py src/api/routers/client_app.py src/api/routers/client_masters.py src/client_bot.py
```

Expected: no output and exit code 0.

- [ ] **Step 4: Run Mini App build only if frontend files were accidentally touched**

Check:

```bash
git diff --name-only HEAD
```

If output includes `miniapp/`, stop and inspect why. This backend plan should not modify frontend files.

- [ ] **Step 5: Check worktree scope**

Run:

```bash
git status --short
```

Expected: only pre-existing unrelated dirty files may remain. The implementation commits should not include:

- `miniapp/src/theme.css`
- `.claude/`
- `miniapp/.claude/`
- `docs/superpowers/plans/2026-04-20-master-miniapp-style-unification.md`

- [ ] **Step 6: Update central agent context**

Following `CLAUDE.md`, update:

- `/Users/evgenijpastusenko/Projects/agent1/project_ai_context/master-bot/AGENT_STATE.md`
- `/Users/evgenijpastusenko/Projects/agent1/project_ai_context/master-bot/SESSION_LOG.md`

Keep both short and factual. Mention commits created, tests run, and any remaining scope.

- [ ] **Step 7: Final summary**

Report:

- commit hashes
- files changed
- verification commands and results
- explicit note that React frontend redesign and full notification inline-action redesign are not included in this pass

---

## Plan Self-Review Checklist

- Every backend requirement from the design spec has an implementation task.
- The plan keeps current architecture for `client_confirmed`, `orders.rating`, and `campaigns`.
- The plan adds only `reviews` and `notify_bonuses` as new data shape.
- The plan avoids frontend redesign.
- The plan keeps client-bot work scoped to `/start` Mini App entry.
- Tests are based on stdlib `unittest`, so no new test dependency is required.
