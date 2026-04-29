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
