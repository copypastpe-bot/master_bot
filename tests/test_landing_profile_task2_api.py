import importlib
import os
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from src import database as db


class LandingProfileTask2ApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        os.environ["BONUS_MEDIA_DIR"] = self.tmp.name
        await db.init_db()
        await self._seed_landing_fixture()

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    async def _seed_landing_fixture(self):
        conn = await db.get_connection()
        try:
            await conn.execute(
                """
                INSERT INTO masters (
                    id, tg_id, name, sphere, invite_token, about, contacts, socials,
                    work_hours, currency, bonus_enabled, bonus_welcome, avatar_file_id
                )
                VALUES (
                    1, 1001, 'Анна Иванова', 'Маникюр', 'invite_anna',
                    'Делаю аккуратный маникюр', '+79990000000', '@anna_nails',
                    'Пн-Пт 10:00-19:00', 'EUR', 1, 50, 'avatar_file'
                )
                """
            )
            await conn.execute(
                """
                INSERT INTO clients (id, tg_id, name, phone)
                VALUES (1, 2001, 'Мария Петрова', '+79991111111')
                """
            )
            await conn.execute(
                """
                INSERT INTO services (id, master_id, name, price, description, is_active, show_on_landing)
                VALUES
                    (1, 1, 'Гель-лак', 35, 'Покрытие', 1, 1),
                    (2, 1, 'Скрытая услуга', 99, NULL, 1, 0)
                """
            )
            await conn.execute(
                """
                INSERT INTO master_portfolio (id, master_id, file_id, sort_order)
                VALUES (1, 1, 'portfolio_file', 0)
                """
            )
            await conn.execute(
                """
                INSERT INTO orders (id, master_id, client_id, status, scheduled_at, amount_total)
                VALUES (1, 1, 1, 'done', '2026-04-20 10:00:00', 35)
                """
            )
            await conn.execute(
                """
                INSERT INTO reviews (id, master_id, client_id, order_id, rating, text)
                VALUES (1, 1, 1, 1, 5, 'Отлично!')
                """
            )
            await conn.commit()
        finally:
            await conn.close()

    def _reload_app_module(self):
        app_module = importlib.import_module("src.api.app")
        return importlib.reload(app_module)

    async def test_public_master_endpoint_returns_landing_read_model(self):
        from src.api.routers import public

        response = await public.get_public_master("invite_anna")

        self.assertEqual(response["name"], "Анна Иванова")
        self.assertEqual(response["about"], "Делаю аккуратный маникюр")
        self.assertEqual(response["avatar_url"], "/api/public/photo/avatar_file")
        self.assertEqual(response["portfolio"], [
            {"id": 1, "url": "/api/public/photo/portfolio_file"}
        ])
        self.assertEqual(response["services"], [
            {"name": "Гель-лак", "price": 35}
        ])
        self.assertEqual(response["reviews"][0]["client_name"], "Мария П.")
        self.assertEqual(response["reviews"][0]["rating"], 5)
        self.assertTrue(response["cta_link"].endswith("?start=invite_anna"))

    async def test_public_master_endpoint_returns_404_for_unknown_token(self):
        from src.api.routers import public

        with self.assertRaises(HTTPException) as ctx:
            await public.get_public_master("missing")

        self.assertEqual(ctx.exception.status_code, 404)

    def test_public_photo_route_is_registered(self):
        app_module = self._reload_app_module()
        paths = {route.path for route in app_module.app.routes}

        self.assertIn("/api/public/photo/{file_id:path}", paths)

    async def test_master_profile_portfolio_and_service_landing_api(self):
        from src.api.routers.master import settings
        from src.models import Master

        master = Master(id=1, tg_id=1001, name="Анна Иванова", invite_token="invite_anna")

        await settings.update_master_profile(
            settings.ProfileUpdateBody(about="Новое описание", avatar_file_id="new_avatar"),
            master=master,
        )
        portfolio_result = await settings.add_master_portfolio_photo(
            settings.PortfolioPhotoBody(file_id="new_portfolio"),
            master=master,
        )
        portfolio = await settings.get_master_portfolio_api(master=master)
        await settings.update_master_service(
            1,
            settings.ServiceUpdateBody(show_on_landing=False),
            master=master,
        )

        updated_master = await db.get_master_by_id(1)
        service = await db.get_service_by_id(1)

        self.assertEqual(updated_master.about, "Новое описание")
        self.assertEqual(updated_master.avatar_file_id, "new_avatar")
        self.assertEqual(portfolio_result["id"], 2)
        self.assertEqual(portfolio[-1]["file_id"], "new_portfolio")
        self.assertFalse(service.show_on_landing)
