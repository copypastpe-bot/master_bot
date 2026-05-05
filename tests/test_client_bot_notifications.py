import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path


class ClientBotNotificationsDatabaseTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from src import database as db

        self.db = db
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = self.db.DB_PATH
        self.db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        await self.db.init_db()
        await self._seed()

    async def asyncTearDown(self):
        self.db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    async def _seed(self):
        conn = await self.db.get_connection()
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
        context = await self.db.get_order_notification_context(10, client_tg_id=2001)

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
        context = await self.db.get_order_notification_context(10, client_tg_id=9999)
        self.assertIsNone(context)

    async def test_is_manual_bonus_notification_enabled_reads_notify_bonuses(self):
        enabled = await self.db.is_manual_bonus_notification_enabled(master_id=1, client_id=1)
        self.assertTrue(enabled)

        conn = await self.db.get_connection()
        try:
            await conn.execute(
                "UPDATE master_clients SET notify_bonuses = 0 WHERE master_id = 1 AND client_id = 1"
            )
            await conn.commit()
        finally:
            await conn.close()

        disabled = await self.db.is_manual_bonus_notification_enabled(master_id=1, client_id=1)
        self.assertFalse(disabled)

    async def test_get_manual_bonus_notification_context_returns_balance_and_client_tg(self):
        context = await self.db.get_manual_bonus_notification_context(master_id=1, client_id=1)

        self.assertEqual(context["client_tg_id"], 2001)
        self.assertEqual(context["master_name"], "Анна Иванова")
        self.assertEqual(context["bonus_balance"], 150)
        self.assertEqual(context["notify_bonuses"], 1)


class ClientBotNotificationFormattingTest(unittest.TestCase):
    def import_notifications(self):
        sys.modules.pop("src.notifications", None)
        original_database = sys.modules.get("src.database")
        database_stub = types.ModuleType("src.database")

        async def get_order_notification_context(*_args, **_kwargs):
            return None

        database_stub.get_order_notification_context = get_order_notification_context
        sys.modules["src.database"] = database_stub
        try:
            return importlib.import_module("src.notifications")
        finally:
            if original_database is not None:
                sys.modules["src.database"] = original_database
            else:
                sys.modules.pop("src.database", None)

    def test_contact_keyboard_uses_only_available_structured_contacts(self):
        contact_keyboard = self.import_notifications().contact_keyboard

        kb = contact_keyboard(phone="+79990001122", telegram="@anna_nails")
        rows = kb.inline_keyboard

        self.assertEqual(rows[0][0].text, "Позвонить")
        self.assertEqual(rows[0][0].url, "tel:+79990001122")
        self.assertEqual(rows[1][0].text, "Написать в TG")
        self.assertEqual(rows[1][0].url, "https://t.me/anna_nails")
        self.assertEqual(len(rows), 2)

    def test_reminder_keyboard_has_only_confirm_and_contact(self):
        reminder_24h_keyboard = self.import_notifications().reminder_24h_keyboard

        kb = reminder_24h_keyboard(order_id=10)
        buttons = [button for row in kb.inline_keyboard for button in row]

        self.assertEqual(len(buttons), 2)
        self.assertEqual(buttons[0].text, "Подтвердить")
        self.assertEqual(buttons[0].callback_data, "confirm_order:10")
        self.assertEqual(buttons[1].text, "Связаться")
        self.assertEqual(buttons[1].callback_data, "contact_order:10")

    def test_event_keyboards_do_not_include_miniapp_buttons(self):
        notifications = self.import_notifications()
        contact_keyboard = notifications.contact_keyboard
        order_action_keyboard = notifications.order_action_keyboard
        reminder_24h_keyboard = notifications.reminder_24h_keyboard

        keyboards = [
            order_action_keyboard(order_id=10, master_id=1),
            reminder_24h_keyboard(order_id=10, master_id=1),
            contact_keyboard(phone="+79990001122", telegram="@anna_nails", master_id=1),
        ]

        for kb in keyboards:
            buttons = [button for row in kb.inline_keyboard for button in row]
            self.assertNotIn("Открыть приложение", [button.text for button in buttons])
            self.assertTrue(all(getattr(button, "web_app", None) is None for button in buttons))

    def test_review_keyboard_is_removed(self):
        notifications = self.import_notifications()
        self.assertFalse(hasattr(notifications, "review_keyboard"))
