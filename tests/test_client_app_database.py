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
                INSERT INTO orders (id, master_id, client_id, status, scheduled_at, amount_total, client_confirmed)
                VALUES (2, 1, 1, 'confirmed', '2026-04-24 12:00:00', 2500, 1)
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
            await conn.commit()
        finally:
            await conn.close()

        orders = await db.get_client_orders_for_app(master_id=1, client_id=1, limit=20, offset=0)
        by_id = {order["id"]: order for order in orders}
        self.assertEqual(by_id[2]["display_status"], "confirmed")
        self.assertEqual(by_id[1]["services"], "Маникюр")
        self.assertFalse(by_id[1]["has_review"])

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
