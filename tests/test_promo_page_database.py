import tempfile
import unittest
from pathlib import Path

from src import database as db


class PromoPageDatabaseTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        await db.init_db()

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    async def _seed_masters(self):
        conn = await db.get_connection()
        try:
            await conn.execute(
                """
                INSERT INTO masters (id, tg_id, name, sphere, invite_token)
                VALUES (1, 1001, 'Мария Иванова', 'Клининг', 'invite_maria')
                """
            )
            await conn.execute(
                """
                INSERT INTO masters (id, tg_id, name, sphere, invite_token)
                VALUES (2, 1002, 'Мария Иванова', 'Клининг', 'invite_maria_2')
                """
            )
            await conn.commit()
        finally:
            await conn.close()

    async def test_init_db_creates_promo_seed_catalogs(self):
        categories = await db.get_promo_categories()

        self.assertEqual(len(categories), 5)
        cleaning = next(c for c in categories if c["slug"] == "cleaning")
        self.assertEqual(cleaning["name"], "Клининг")
        self.assertGreaterEqual(len(cleaning["styles"]), 3)
        self.assertGreaterEqual(len(cleaning["advantages"]), 6)
        self.assertEqual(cleaning["styles"][0]["config"]["screen_accent"], "#2d8049")
        self.assertEqual(cleaning["styles"][0]["config"]["cta_shadow"], "rgba(31,135,79,.22)")

    async def test_create_update_publish_and_public_read_model(self):
        await self._seed_masters()
        categories = await db.get_promo_categories()
        cleaning = next(c for c in categories if c["slug"] == "cleaning")
        style = cleaning["styles"][0]
        advantages = [
            {"text": item["text"], "icon": item["icon"]}
            for item in cleaning["advantages"][:3]
        ]

        page = await db.create_promo_page(
            master_id=1,
            category_id=cleaning["id"],
            style_id=style["id"],
            display_name="Мария Иванова",
            specialization="Частный клинер",
            tagline="Чистота и порядок без лишних хлопот.",
            badge_text="ЧИСТО БЫСТРО",
            service_name="Уборка квартиры",
            service_price="от 4 000 дин",
            promo_text="-20% на первую уборку",
            promo_enabled=True,
            advantages=advantages,
        )

        self.assertEqual(page["slug"], "mariya-ivanova")
        self.assertTrue(page["promo_enabled"])
        self.assertEqual(page["advantages"], advantages)
        self.assertTrue(await db.promo_style_belongs_to_category(style["id"], cleaning["id"]))

        colliding = await db.create_promo_page(
            master_id=2,
            category_id=cleaning["id"],
            style_id=style["id"],
            display_name="Мария Иванова",
            specialization="Частный клинер",
            tagline="Чистота и порядок без лишних хлопот.",
            service_name="Уборка квартиры",
            service_price="от 4 000 дин",
            advantages=advantages,
        )
        self.assertEqual(colliding["slug"], "mariya-ivanova-1")

        self.assertIsNone(await db.get_promo_public_data("mariya-ivanova"))

        await db.update_promo_page_media(
            master_id=1,
            photo_path="/var/www/crmfit/media/promo/1/photo.jpg",
            photo_url="https://crmfit.ru/media/promo/1/photo.jpg",
            qr_path="/var/www/crmfit/media/promo/1/qr.png",
            qr_url="https://crmfit.ru/media/promo/1/qr.png",
        )
        await db.set_promo_page_published(1, True)

        public_data = await db.get_promo_public_data("mariya-ivanova", increment_view=True)
        self.assertIsNotNone(public_data)
        self.assertEqual(public_data["category"]["slug"], "cleaning")
        self.assertEqual(public_data["style"]["config"]["cta_bg"], "#2d8049")
        self.assertEqual(public_data["views_count"], 1)

        clicked = await db.increment_promo_page_clicks("mariya-ivanova")
        self.assertTrue(clicked)
        updated = await db.get_promo_page_by_master(1)
        self.assertEqual(updated["clicks_count"], 1)

    async def test_manual_slug_validation_rejects_reserved_or_taken_values(self):
        await self._seed_masters()
        categories = await db.get_promo_categories()
        cleaning = next(c for c in categories if c["slug"] == "cleaning")
        style = cleaning["styles"][0]

        await db.create_promo_page(
            master_id=1,
            category_id=cleaning["id"],
            style_id=style["id"],
            display_name="Мария Иванова",
            specialization="Частный клинер",
            tagline="Чистота и порядок без лишних хлопот.",
            service_name="Уборка квартиры",
            service_price="от 4 000 дин",
            advantages=[{"text": "Приеду вовремя", "icon": "⏰"}] * 3,
        )

        with self.assertRaises(ValueError):
            await db.update_promo_page(1, slug="api")

        with self.assertRaises(ValueError):
            await db.update_promo_page(1, slug="кириллица")

    async def test_mark_promo_page_started_is_idempotent(self):
        await self._seed_masters()

        first = await db.mark_promo_page_started(1)
        self.assertIsNotNone(first)

        second = await db.mark_promo_page_started(1)
        self.assertEqual(second, first)

        masters = await db.get_masters()
        master = next(item for item in masters if item.id == 1)
        self.assertEqual(master.promo_page_started_at, first)
