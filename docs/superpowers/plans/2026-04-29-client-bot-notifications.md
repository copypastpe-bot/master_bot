# Client Bot Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify the client Telegram bot into a Mini App entry point and notification channel with inline actions for visit confirmation, contact display, review entry, broadcasts, and manual bonus notifications.

**Architecture:** Keep registration, service commands, and feedback in `src/client_bot.py`, while moving reusable notification formatting/keyboards into `src/notifications.py`. Database helpers in `src/database.py` provide order/contact/notification-setting data so bot callbacks and API notification paths do not duplicate SQL.

**Tech Stack:** Python 3, aiogram, FastAPI, APScheduler, SQLite via `aiosqlite`, unittest, React Mini App.

---

## Files And Responsibilities

- `src/client_bot_legacy.py`: archive copy of the current client bot. It must not be imported by runtime code.
- `src/client_bot.py`: simplified client bot runtime: `/start`, invite registration, `/support`, `/delete_me`, feedback callbacks, confirm/contact callbacks, menu button and scheduler startup.
- `src/notifications.py`: client-facing notification text builders, inline keyboards, and send helpers for new orders, order lifecycle messages, broadcasts, and manual bonus notifications.
- `src/scheduler.py`: 24h reminder and feedback/birthday/subscription jobs. Remove 1h reminder from scheduled runtime.
- `src/database.py`: helper queries for notification settings, order confirmation data, contact data, manual bonus notification data.
- `src/keyboards.py`: remove old client menu keyboard helpers no longer used by runtime.
- `src/states.py`: remove old client-side order/question/media/reschedule/cancel FSM classes no longer used by runtime.
- `src/api/routers/master/orders.py`: preserve create/complete/move/cancel order integration with notification helpers.
- `src/api/routers/master/broadcast.py`: format broadcast notifications and attach Mini App button.
- `src/api/routers/master/clients.py`: send manual positive bonus notifications after successful transaction.
- `miniapp/src/App.jsx`: support Mini App review deep-link start parameter for `order_id`.
- `tests/test_client_bot_notifications.py`: focused tests for database helpers and pure notification formatting/keyboards.
- `tests/test_client_app_database.py`: extend only if helper tests naturally fit existing fixture.
- `tests/test_client_app_api_import.py`: keep import regression passing.

## Task 1: Add Database Helper Tests

**Files:**
- Create: `tests/test_client_bot_notifications.py`
- Modify: `src/database.py`

- [ ] **Step 1: Write failing tests for notification helper data**

Create `tests/test_client_bot_notifications.py`:

```python
import tempfile
import unittest
from pathlib import Path

from src import database as db


class ClientBotNotificationsDatabaseTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        await db.init_db()
        await self._seed()

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    async def _seed(self):
        conn = await db.get_connection()
        try:
            await conn.execute(
                """
                INSERT INTO masters (
                    id, tg_id, name, sphere, invite_token, phone, telegram,
                    contacts, currency
                )
                VALUES (
                    1, 1001, 'Анна Иванова', 'Маникюр', 'anna',
                    '+79990001122', '@anna_nails', '+79990001122', 'RUB'
                )
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
                INSERT INTO master_clients (
                    master_id, client_id, bonus_balance,
                    notify_reminders, notify_marketing, notify_bonuses
                )
                VALUES (1, 1, 150, 1, 1, 1)
                """
            )
            await conn.execute(
                """
                INSERT INTO orders (
                    id, master_id, client_id, status, scheduled_at,
                    address, amount_total, client_confirmed
                )
                VALUES (
                    10, 1, 1, 'confirmed', '2026-05-01T14:30:00',
                    'Невский 1', 3500, 0
                )
                """
            )
            await conn.execute(
                """
                INSERT INTO order_items (order_id, name, price)
                VALUES (10, 'Маникюр', 3500)
                """
            )
            await conn.commit()
        finally:
            await conn.close()

    async def test_get_order_notification_context_returns_contacts_and_settings(self):
        context = await db.get_order_notification_context(10, client_tg_id=2001)

        self.assertEqual(context["order_id"], 10)
        self.assertEqual(context["client_name"], "Мария Петрова")
        self.assertEqual(context["client_tg_id"], 2001)
        self.assertEqual(context["master_name"], "Анна Иванова")
        self.assertEqual(context["master_phone"], "+79990001122")
        self.assertEqual(context["master_telegram"], "@anna_nails")
        self.assertEqual(context["services"], "Маникюр")
        self.assertEqual(context["notify_reminders"], 1)
        self.assertEqual(context["client_confirmed"], 0)

    async def test_get_order_notification_context_rejects_wrong_client(self):
        context = await db.get_order_notification_context(10, client_tg_id=9999)
        self.assertIsNone(context)

    async def test_is_manual_bonus_notification_enabled_reads_notify_bonuses(self):
        enabled = await db.is_manual_bonus_notification_enabled(master_id=1, client_id=1)
        self.assertTrue(enabled)

        conn = await db.get_connection()
        try:
            await conn.execute(
                "UPDATE master_clients SET notify_bonuses = 0 WHERE master_id = 1 AND client_id = 1"
            )
            await conn.commit()
        finally:
            await conn.close()

        disabled = await db.is_manual_bonus_notification_enabled(master_id=1, client_id=1)
        self.assertFalse(disabled)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
./venv/bin/python -m unittest tests.test_client_bot_notifications -v
```

Expected: FAIL with `AttributeError` for `get_order_notification_context`.

- [ ] **Step 3: Add minimal database helpers**

In `src/database.py`, near the reminder and confirmation helpers, add:

```python
async def get_order_notification_context(order_id: int, client_tg_id: int | None = None) -> dict | None:
    """Return order, client, master, settings, and services for client bot notifications."""
    conn = await get_connection()
    try:
        params: list = [order_id]
        client_filter = ""
        if client_tg_id is not None:
            client_filter = "AND c.tg_id = ?"
            params.append(client_tg_id)

        cursor = await conn.execute(
            f"""
            SELECT
                o.id AS order_id,
                o.status,
                o.scheduled_at,
                o.address,
                o.client_confirmed,
                c.id AS client_id,
                c.tg_id AS client_tg_id,
                c.name AS client_name,
                m.id AS master_id,
                m.tg_id AS master_tg_id,
                m.name AS master_name,
                m.phone AS master_phone,
                m.telegram AS master_telegram,
                m.contacts AS master_contacts,
                mc.notify_reminders,
                mc.notify_marketing,
                mc.notify_bonuses,
                mc.bonus_balance,
                GROUP_CONCAT(oi.name, ', ') AS services
            FROM orders o
            JOIN clients c ON c.id = o.client_id
            JOIN masters m ON m.id = o.master_id
            JOIN master_clients mc ON mc.master_id = m.id AND mc.client_id = c.id
            LEFT JOIN order_items oi ON oi.order_id = o.id
            WHERE o.id = ?
              {client_filter}
            GROUP BY o.id
            """,
            params,
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def is_manual_bonus_notification_enabled(master_id: int, client_id: int) -> bool:
    """Return whether standalone positive bonus notifications may be sent."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT notify_bonuses
            FROM master_clients
            WHERE master_id = ? AND client_id = ?
            """,
            (master_id, client_id),
        )
        row = await cursor.fetchone()
        return bool(row and row["notify_bonuses"])
    finally:
        await conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
./venv/bin/python -m unittest tests.test_client_bot_notifications -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add tests/test_client_bot_notifications.py src/database.py
git commit -m "Add client notification database helpers"
```

## Task 2: Add Notification Formatting And Keyboards

**Files:**
- Modify: `tests/test_client_bot_notifications.py`
- Modify: `src/notifications.py`

- [ ] **Step 1: Add failing tests for pure keyboard/text helpers**

Append to `tests/test_client_bot_notifications.py`:

```python
class ClientBotNotificationFormattingTest(unittest.TestCase):
    def test_contact_keyboard_uses_only_available_structured_contacts(self):
        from src.notifications import contact_keyboard

        kb = contact_keyboard(phone="+79990001122", telegram="@anna_nails")
        rows = kb.inline_keyboard

        self.assertEqual(rows[0][0].text, "Позвонить")
        self.assertEqual(rows[0][0].url, "tel:+79990001122")
        self.assertEqual(rows[1][0].text, "Написать в TG")
        self.assertEqual(rows[1][0].url, "https://t.me/anna_nails")
        self.assertEqual(rows[2][0].text, "Открыть приложение")
        self.assertIsNotNone(rows[2][0].web_app)

    def test_reminder_keyboard_has_confirm_contact_and_miniapp(self):
        from src.notifications import reminder_24h_keyboard

        kb = reminder_24h_keyboard(order_id=10)
        buttons = [button for row in kb.inline_keyboard for button in row]

        self.assertEqual(buttons[0].text, "Подтвердить")
        self.assertEqual(buttons[0].callback_data, "confirm_order:10")
        self.assertEqual(buttons[1].text, "Связаться")
        self.assertEqual(buttons[1].callback_data, "contact_order:10")
        self.assertEqual(buttons[2].text, "Открыть приложение")
        self.assertIsNotNone(buttons[2].web_app)

    def test_review_button_adds_order_id_to_client_miniapp_url(self):
        from src.notifications import review_keyboard

        kb = review_keyboard(order_id=10)
        url = kb.inline_keyboard[0][0].web_app.url

        self.assertIn("app=client", url)
        self.assertIn("review_order_id=10", url)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
./venv/bin/python -m unittest tests.test_client_bot_notifications -v
```

Expected: FAIL with import errors for the new helper functions.

- [ ] **Step 3: Add notification helper functions**

In `src/notifications.py`, add imports:

```python
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from src.config import CLIENT_BOT_TOKEN, CLIENT_MINIAPP_URL
```

Then add helper functions near the top, after `format_datetime`:

```python
def _client_miniapp_url(**params: str | int) -> str:
    parts = urlsplit(CLIENT_MINIAPP_URL)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    for key, value in params.items():
        query[key] = str(value)
    return urlunsplit(parts._replace(query=urlencode(query)))


def open_app_button(**params: str | int) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="Открыть приложение",
        web_app=WebAppInfo(url=_client_miniapp_url(**params)),
    )


def order_action_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Связаться", callback_data=f"contact_order:{order_id}"),
            open_app_button(),
        ],
    ])


def reminder_24h_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Подтвердить", callback_data=f"confirm_order:{order_id}"),
            InlineKeyboardButton(text="Связаться", callback_data=f"contact_order:{order_id}"),
        ],
        [open_app_button()],
    ])


def contact_keyboard(phone: str | None, telegram: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    phone_value = (phone or "").strip()
    telegram_value = (telegram or "").strip().lstrip("@")
    if phone_value:
        rows.append([InlineKeyboardButton(text="Позвонить", url=f"tel:{phone_value}")])
    if telegram_value:
        rows.append([InlineKeyboardButton(text="Написать в TG", url=f"https://t.me/{telegram_value}")])
    rows.append([open_app_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def review_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Оставить отзыв",
                web_app=WebAppInfo(url=_client_miniapp_url(review_order_id=order_id)),
            )
        ],
    ])
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
./venv/bin/python -m unittest tests.test_client_bot_notifications -v
```

Expected: 6 tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add tests/test_client_bot_notifications.py src/notifications.py
git commit -m "Add client notification keyboards"
```

## Task 3: Update New Order, Broadcast, And Manual Bonus Notifications

**Files:**
- Modify: `src/notifications.py`
- Modify: `src/api/routers/master/orders.py`
- Modify: `src/api/routers/master/broadcast.py`
- Modify: `src/api/routers/master/clients.py`
- Modify: `src/database.py`

- [ ] **Step 1: Write failing manual bonus data test**

Append to `ClientBotNotificationsDatabaseTest` in `tests/test_client_bot_notifications.py`:

```python
    async def test_get_manual_bonus_notification_context_returns_balance_and_client_tg(self):
        context = await db.get_manual_bonus_notification_context(master_id=1, client_id=1)

        self.assertEqual(context["client_tg_id"], 2001)
        self.assertEqual(context["master_name"], "Анна Иванова")
        self.assertEqual(context["bonus_balance"], 150)
        self.assertEqual(context["notify_bonuses"], 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
./venv/bin/python -m unittest tests.test_client_bot_notifications -v
```

Expected: FAIL with `AttributeError` for `get_manual_bonus_notification_context`.

- [ ] **Step 3: Add manual bonus context helper**

In `src/database.py`, near `is_manual_bonus_notification_enabled`, add:

```python
async def get_manual_bonus_notification_context(master_id: int, client_id: int) -> dict | None:
    """Return data needed to notify a client about standalone manual bonus accrual."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT
                c.tg_id AS client_tg_id,
                m.name AS master_name,
                mc.bonus_balance,
                mc.notify_bonuses
            FROM master_clients mc
            JOIN clients c ON c.id = mc.client_id
            JOIN masters m ON m.id = mc.master_id
            WHERE mc.master_id = ? AND mc.client_id = ?
            """,
            (master_id, client_id),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()
```

- [ ] **Step 4: Update `notify_order_created`**

In `src/notifications.py`, import:

```python
from src.database import get_order_notification_context
```

Change `notify_order_created` so it accepts optional `bot=None`, fetches context by order id, respects `notify_reminders`, and sends the TЗ format:

```python
async def notify_order_created(
    client: Client,
    order: dict,
    master: Master,
    services: list[dict],
    bot=None,
) -> bool:
    """Notify client about a new order if reminder notifications are enabled."""
    if not client.tg_id:
        return False

    context = await get_order_notification_context(order["id"], client_tg_id=client.tg_id)
    if not context or not context.get("notify_reminders"):
        return False

    try:
        scheduled_at = order.get("scheduled_at")
        if isinstance(scheduled_at, str):
            scheduled_at = datetime.fromisoformat(scheduled_at)

        services_text = ", ".join(s["name"] for s in services) or "—"
        date_str = f"{scheduled_at.day} {MONTHS_RU[scheduled_at.month]}"
        time_str = scheduled_at.strftime("%H:%M")
        address = (order.get("address") or "").strip()

        text = (
            f"{master.name} записал(а) вас:\n\n"
            f"{services_text}\n"
            f"{date_str}, {time_str}"
        )
        if address:
            text += f"\n{address}"

        await (bot or client_bot).send_message(
            client.tg_id,
            text,
            reply_markup=order_action_keyboard(order["id"]),
        )
        logger.info("Notification sent to client %s: order created", client.id)
        return True
    except TelegramForbiddenError:
        logger.warning("Client %s blocked the bot", client.id)
        return False
    except TelegramBadRequest as e:
        logger.error("Failed to send notification to client %s: %s", client.id, e)
        return False
    except Exception as e:
        logger.error("Unexpected error sending notification to client %s: %s", client.id, e)
        return False
```

- [ ] **Step 5: Pass API bot instance into new order notification**

In `src/api/routers/master/orders.py`, change the create-order notification call:

```python
await notifications.notify_order_created(
    client=client,
    order={
        "id": order_id,
        "scheduled_at": scheduled_at,
        "address": final_address,
        "amount_total": amount_total,
    },
    master=master,
    services=order_items,
    bot=getattr(request.app.state, "client_bot", None),
)
```

- [ ] **Step 6: Add manual bonus send helper**

In `src/notifications.py`, add:

```python
async def notify_manual_bonus(
    chat_id: int,
    master_name: str,
    amount: int,
    comment: str | None,
    balance: int,
    bot=None,
) -> bool:
    """Notify a client about standalone positive manual bonus accrual."""
    if amount <= 0:
        return False

    comment_text = (comment or "").strip()
    text = f"Начислено +{amount} бонусов"
    if comment_text:
        text += f"\n{comment_text}"
    text += f"\nот {master_name}\n\nВаш баланс: {balance} бонусов"

    try:
        await (bot or client_bot).send_message(chat_id=chat_id, text=text)
        return True
    except TelegramForbiddenError:
        logger.warning("Client %s blocked the bot for manual bonus notification", chat_id)
        return False
    except TelegramBadRequest as e:
        logger.error("Failed to send manual bonus notification to %s: %s", chat_id, e)
        return False
```

- [ ] **Step 7: Send manual bonus notification from API**

In `src/api/routers/master/clients.py`, import:

```python
from src.database import get_manual_bonus_notification_context
from src.notifications import notify_manual_bonus
```

Change the bonus endpoint after `manual_bonus_transaction`:

```python
new_balance = await manual_bonus_transaction(master.id, client_id, body.amount, body.comment)
if body.amount > 0:
    context = await get_manual_bonus_notification_context(master.id, client_id)
    client_bot = getattr(request.app.state, "client_bot", None)
    if context and context.get("client_tg_id") and context.get("notify_bonuses"):
        await notify_manual_bonus(
            chat_id=context["client_tg_id"],
            master_name=context.get("master_name") or master.name,
            amount=body.amount,
            comment=body.comment,
            balance=new_balance,
            bot=client_bot,
        )
return {"ok": True}
```

Also add `request: Request` to the endpoint parameters and import `Request` from FastAPI if missing.

- [ ] **Step 8: Add Mini App button and specialist prefix to broadcast**

In `src/api/routers/master/broadcast.py`, import:

```python
from src.notifications import open_app_button
from aiogram.types import InlineKeyboardMarkup
```

Before the send loop:

```python
reply_markup = InlineKeyboardMarkup(inline_keyboard=[[open_app_button()]])
```

Inside the loop, replace `personalized = _personalize(text, client.get("name") or "")` with:

```python
personalized_body = _personalize(text, client.get("name") or "")
personalized = f"{master.name}:\n\n{personalized_body}"
```

Pass `reply_markup=reply_markup` to `send_photo`, `send_video`, and `send_message`.

- [ ] **Step 9: Run focused tests and compile changed modules**

Run:

```bash
./venv/bin/python -m unittest tests.test_client_bot_notifications -v
./venv/bin/python -m py_compile src/notifications.py src/api/routers/master/orders.py src/api/routers/master/broadcast.py src/api/routers/master/clients.py src/database.py
```

Expected: tests pass and `py_compile` exits 0.

- [ ] **Step 10: Commit**

Run:

```bash
git add tests/test_client_bot_notifications.py src/notifications.py src/api/routers/master/orders.py src/api/routers/master/broadcast.py src/api/routers/master/clients.py src/database.py
git commit -m "Update client notification delivery paths"
```

## Task 4: Replace Scheduler Reminder Runtime

**Files:**
- Modify: `src/scheduler.py`
- Modify: `src/client_bot.py`

- [ ] **Step 1: Remove old 1h scheduler runtime**

In `src/scheduler.py`:

- remove the `write_master_kb` function
- remove `send_reminders_1h`
- remove the `scheduler.add_job(send_reminders_1h, ...)` block from `setup_scheduler`
- keep `get_orders_for_reminder_1h` in `src/database.py` untouched unless no imports remain and cleanup is safe

- [ ] **Step 2: Replace 24h reminder keyboard and text**

In `src/scheduler.py`, import from notifications:

```python
from src.notifications import reminder_24h_keyboard
```

Replace `confirm_order_kb` usage with `reminder_24h_keyboard`.

In `send_reminders_24h`, build the TЗ text:

```python
text = (
    "Напоминание:\n\n"
    f"{services}\n"
    f"Завтра, {time_str} — {master_name}"
)
if address and address != "—":
    text += f"\n{address}"
```

Send:

```python
await client_bot.send_message(
    chat_id=order["client_tg_id"],
    text=text,
    reply_markup=reminder_24h_keyboard(order["order_id"]),
)
```

- [ ] **Step 3: Run compile**

Run:

```bash
./venv/bin/python -m py_compile src/scheduler.py src/client_bot.py
```

Expected: exits 0.

- [ ] **Step 4: Commit**

Run:

```bash
git add src/scheduler.py
git commit -m "Simplify client reminder scheduler"
```

## Task 5: Simplify Client Bot Runtime And Inline Actions

**Files:**
- Create: `src/client_bot_legacy.py`
- Modify: `src/client_bot.py`
- Modify: `src/keyboards.py`
- Modify: `src/states.py`

- [ ] **Step 1: Archive the current client bot**

Run:

```bash
cp src/client_bot.py src/client_bot_legacy.py
```

Expected: `src/client_bot_legacy.py` exists and is not imported anywhere.

- [ ] **Step 2: Add failing import/contract test**

Create `tests/test_client_bot_runtime.py`:

```python
import importlib
import unittest


class ClientBotRuntimeTest(unittest.TestCase):
    def test_client_bot_imports_without_old_runtime_handlers(self):
        module = importlib.import_module("src.client_bot")
        callback_names = {
            item.callback.__name__
            for item in module.router.callback_query.handlers
        }

        self.assertIn("handle_feedback_rating", callback_names)
        self.assertIn("handle_order_confirmation", callback_names)
        self.assertIn("handle_contact_order", callback_names)

        removed = {
            "cb_bonuses",
            "cb_history",
            "cb_promos",
            "cb_order_request",
            "cb_question",
            "cb_media",
            "cb_master_info",
            "cb_notifications",
            "cb_change_master",
            "handle_reschedule_start",
            "handle_cancel_start",
        }
        self.assertTrue(removed.isdisjoint(callback_names))
```

- [ ] **Step 3: Run test to verify it fails**

Run:

```bash
./venv/bin/python -m unittest tests.test_client_bot_runtime -v
```

Expected: FAIL because old handlers are still registered or `handle_contact_order` is missing.

- [ ] **Step 4: Replace rating 5 follow-up**

In `src/client_bot.py`, import:

```python
from src.notifications import (
    contact_keyboard,
    order_action_keyboard,
    review_keyboard,
)
```

In `handle_feedback_rating`, replace the `rating == 5` branch with:

```python
    if rating == 5:
        if callback.message:
            await callback.message.answer(
                "Большое спасибо! Оставьте, пожалуйста, отзыв — это поможет специалисту.",
                reply_markup=review_keyboard(order_id),
            )
```

Keep rating 4 and rating 1-3 branches unchanged.

- [ ] **Step 5: Replace confirm callback logic**

In `src/client_bot.py`, import `get_order_notification_context`.

Replace `handle_order_confirmation` body with:

```python
@router.callback_query(F.data.startswith("confirm_order:"))
async def handle_order_confirmation(callback: CallbackQuery) -> None:
    """Handle order confirmation from 24h reminder."""
    global master_bot

    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Запись больше не активна", show_alert=True)
        return

    order = await get_order_notification_context(order_id, client_tg_id=callback.from_user.id)
    if not order:
        await callback.answer("Запись больше не активна", show_alert=True)
        return

    if order.get("client_confirmed"):
        await callback.answer("Запись уже подтверждена", show_alert=True)
        return

    if order.get("status") not in ("new", "confirmed"):
        await callback.answer("Запись больше не активна", show_alert=True)
        return

    await mark_order_confirmed_by_client(order_id)

    scheduled_at = datetime.fromisoformat(order["scheduled_at"])
    date_str = f"{scheduled_at.day} {MONTHS_RU[scheduled_at.month]}"
    time_str = scheduled_at.strftime("%H:%M")
    services = order.get("services") or "—"
    master_name = order.get("master_name") or "специалист"
    address = (order.get("address") or "").strip()

    new_text = (
        "Вы подтвердили запись:\n\n"
        f"{services}\n"
        f"{date_str}, {time_str} — {master_name}"
    )
    if address:
        new_text += f"\n{address}"
    new_text += "\n\nЖдём вас!"

    if callback.message:
        await callback.message.edit_text(
            text=new_text,
            reply_markup=order_action_keyboard(order_id),
        )

    if master_bot and order.get("master_tg_id"):
        master_text = (
            "Клиент подтвердил запись:\n\n"
            f"{order.get('client_name') or 'Клиент'}\n"
            f"{services}\n"
            f"{date_str}, {time_str}"
        )
        await master_bot.send_message(chat_id=order["master_tg_id"], text=master_text)

    await callback.answer("Запись подтверждена")
```

- [ ] **Step 6: Add contact callback**

In `src/client_bot.py`, add near confirm callback:

```python
@router.callback_query(F.data.startswith("contact_order:"))
async def handle_contact_order(callback: CallbackQuery) -> None:
    """Show specialist contacts for an order notification."""
    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Запись больше не активна", show_alert=True)
        return

    order = await get_order_notification_context(order_id, client_tg_id=callback.from_user.id)
    if not order:
        await callback.answer("Запись больше не активна", show_alert=True)
        return

    phone = (order.get("master_phone") or "").strip()
    telegram = (order.get("master_telegram") or "").strip()
    contacts = (order.get("master_contacts") or "").strip()

    lines = [order.get("master_name") or "Специалист", ""]
    lines.append(f"Телефон: {phone or '—'}")
    lines.append(f"Telegram: {telegram or '—'}")
    if contacts and contacts not in {phone, telegram}:
        lines.extend(["", contacts])

    if callback.message:
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=contact_keyboard(phone=phone, telegram=telegram),
        )
    await callback.answer()
```

- [ ] **Step 7: Delete old client navigation handlers**

In `src/client_bot.py`, remove:

- `show_home`
- `edit_home_message` only if no retained command uses it after simplification
- `show_master_select`
- `HomeButtonMiddleware`
- callback handlers for `home`, `select_master:*`, `change_master`, `bonuses`, `history`, `promos`, `master_info`, `notifications`, `notifications:toggle:*`, `client_settings`, `client_support`, `client_delete_profile`
- all `OrderRequestFSM`, `QuestionFSM`, `MediaFSM` handlers
- all client-side reschedule/cancel handlers

Keep:

- `remove_reply_keyboard`
- `/start`
- `/support`
- `/delete_me`
- `delete:confirm`
- `delete:cancel`
- registration FSM handlers
- `handle_feedback_rating`
- `handle_order_confirmation`
- `handle_contact_order`
- `main`

For `/support` and `/delete_me`, send new standalone messages instead of editing old home messages. Use `ReplyKeyboardRemove()` and `delete_confirm_kb()` for delete confirmation.

- [ ] **Step 8: Clean imports and old keyboards/states**

In `src/client_bot.py`, remove imports for deleted states and keyboards.

In `src/states.py`, delete:

```python
class OrderRequestFSM(StatesGroup): ...
class QuestionFSM(StatesGroup): ...
class MediaFSM(StatesGroup): ...
class ClientRescheduleOrder(StatesGroup): ...
class ClientCancelOrder(StatesGroup): ...
```

In `src/keyboards.py`, delete old client menu helpers that are no longer imported:

- `home_client_kb`
- `client_settings_kb`
- `client_notifications_back_kb`
- `client_bonuses_kb`
- `client_bot_history_kb`
- `client_promos_kb`
- `client_master_info_kb`
- `client_notifications_kb`
- `order_request_services_kb`
- `order_request_comment_kb`
- `order_request_confirm_kb`
- `question_cancel_kb`
- `media_cancel_kb`
- `media_comment_kb`
- `client_home_kb`
- `client_reschedule_calendar_kb`
- `client_reschedule_hour_kb`
- `client_reschedule_minutes_kb`
- `client_reschedule_confirm_kb`
- `client_cancel_reason_kb`
- `client_cancel_confirm_kb`

Keep shared helpers still used by registration and service commands:

- `skip_kb`
- `share_contact_kb`
- `consent_kb`
- `delete_confirm_kb`
- `back_kb` only if still imported elsewhere
- `request_notify_kb` if master/inbound request code still imports it

- [ ] **Step 9: Run runtime tests and compile**

Run:

```bash
./venv/bin/python -m unittest tests.test_client_bot_runtime tests.test_client_bot_notifications -v
./venv/bin/python -m py_compile src/client_bot.py src/client_bot_legacy.py src/keyboards.py src/states.py
```

Expected: tests pass and `py_compile` exits 0.

- [ ] **Step 10: Commit**

Run:

```bash
git add src/client_bot.py src/client_bot_legacy.py src/keyboards.py src/states.py tests/test_client_bot_runtime.py
git commit -m "Simplify client bot runtime"
```

## Task 6: Add Mini App Review Deep-Link Handling

**Files:**
- Modify: `miniapp/src/App.jsx`

- [ ] **Step 1: Inspect existing navigation and review modal state**

Read:

```bash
sed -n '1,280p' miniapp/src/App.jsx
sed -n '1,230p' miniapp/src/pages/Home.jsx
sed -n '1,150p' miniapp/src/components/ReviewModal.jsx
```

Expected: identify how `navigate`, selected master, history/home data, and `ReviewModal` are currently wired.

- [ ] **Step 2: Add review order id parser**

In `miniapp/src/App.jsx`, add a parser near existing start-param helpers:

```javascript
function extractReviewOrderId(startParam, search = window.location.search) {
  const params = new URLSearchParams(search || '');
  const fromQuery = params.get('review_order_id');
  if (fromQuery && /^\d+$/.test(fromQuery)) return Number(fromQuery);

  const raw = startParam || '';
  const match = raw.match(/^review_order_(\d+)$/);
  return match ? Number(match[1]) : null;
}
```

- [ ] **Step 3: Route review deep-link into client app state**

In `App.jsx`, compute:

```javascript
const reviewOrderId = extractReviewOrderId(WebApp?.initDataUnsafe?.start_param);
```

When client data is loaded and `reviewOrderId` is present, navigate to the history or home view that owns review modal opening and pass `{ reviewOrderId }` through the existing page params pattern.

Use the existing `navigate(pageId, params)` convention from the client app redesign. Do not add a stack.

- [ ] **Step 4: Open `ReviewModal` for the matching order**

In the page that receives `reviewOrderId`, find the loaded order by id and call the same state setter used by the `Оставить отзыв` button:

```javascript
useEffect(() => {
  if (!reviewOrderId || !orders?.length) return;
  const target = orders.find((order) => Number(order.id) === Number(reviewOrderId));
  if (target && !target.has_review) {
    setReviewOrder(target);
  }
}, [reviewOrderId, orders]);
```

Use the actual local list variable name in that page. Keep the existing manual review button behavior unchanged.

- [ ] **Step 5: Build Mini App**

Run:

```bash
npm --prefix miniapp run build
```

Expected: build succeeds.

- [ ] **Step 6: Commit**

Run:

```bash
git add miniapp/src/App.jsx miniapp/src/pages/Home.jsx miniapp/src/pages/History.jsx
git commit -m "Add client review deep link"
```

Only add `Home.jsx` or `History.jsx` if modified.

## Task 7: Full Verification And Final Cleanup

**Files:**
- All touched implementation files

- [ ] **Step 1: Search for removed client runtime callbacks**

Run:

```bash
rg -n "cb_bonuses|cb_history|cb_promos|cb_order_request|cb_question|cb_media|cb_master_info|cb_notifications|cb_change_master|handle_reschedule_start|handle_cancel_start|OrderRequestFSM|QuestionFSM|MediaFSM|ClientRescheduleOrder|ClientCancelOrder" src/client_bot.py src/states.py src/keyboards.py
```

Expected: no matches in runtime files.

- [ ] **Step 2: Search for old client navigation labels**

Run:

```bash
rg -n "Мои бонусы|История|Акции|Заказать|Вопрос|Фото/видео|Мой мастер|Сменить мастера|Перенести|Отменить" src/client_bot.py src/scheduler.py src/keyboards.py
```

Expected: no matches in client bot notification runtime. Matches in unrelated master UI files are acceptable only outside these three files.

- [ ] **Step 3: Run Python test suite used by this feature**

Run:

```bash
./venv/bin/python -m unittest tests.test_client_bot_notifications tests.test_client_bot_runtime tests.test_client_app_database tests.test_client_app_api_import -v
```

Expected: all tests pass.

- [ ] **Step 4: Compile core Python modules**

Run:

```bash
./venv/bin/python -m py_compile src/client_bot.py src/client_bot_legacy.py src/notifications.py src/scheduler.py src/database.py src/keyboards.py src/states.py src/api/routers/master/orders.py src/api/routers/master/broadcast.py src/api/routers/master/clients.py
```

Expected: exits 0.

- [ ] **Step 5: Build frontend**

Run:

```bash
npm --prefix miniapp run build
```

Expected: build succeeds.

- [ ] **Step 6: Run final git status**

Run:

```bash
git status --short
```

Expected: no uncommitted implementation files. Existing unrelated untracked paths may remain: `.claude/`, `docs/superpowers/plans/2026-04-20-master-miniapp-style-unification.md`, and `miniapp/.claude/`.

- [ ] **Step 7: Commit final cleanup if needed**

If Step 6 shows tracked implementation changes, commit them:

```bash
git add <tracked implementation files>
git commit -m "Finalize client bot notification cleanup"
```

If only unrelated untracked files remain, do not commit them.

## Self-Review Notes

Spec coverage:

- `/start`, invite registration, service commands, and menu button are covered in Task 5.
- New order notification and `notify_reminders` are covered in Task 3.
- 24h reminder and removal of 1h/reschedule/cancel runtime are covered in Task 4 and Task 5.
- Confirm/contact inline actions are covered in Task 5.
- Rating 5 review button and ratings 1-4 preservation are covered in Task 5.
- Broadcast `notify_marketing` formatting and Mini App button are covered in Task 3.
- Manual positive bonus notification and `notify_bonuses` are covered in Task 3.
- Review deep-link support is covered in Task 6.
- Runtime cleanup verification is covered in Task 7.

Placeholder scan: no placeholder tokens are intentionally left for implementation.

Type consistency:

- Contact callback contract is `contact_order:{order_id}` throughout.
- Confirm callback contract remains `confirm_order:{order_id}`.
- Review URL parameter is `review_order_id`.
- Database helper names are `get_order_notification_context`, `is_manual_bonus_notification_enabled`, and `get_manual_bonus_notification_context`.
