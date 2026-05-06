import importlib
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image
from starlette.requests import Request

from src import database as db
from src.models import Master


class PromoPageTask2ApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        self.old_bonus_media_dir = os.environ.get("BONUS_MEDIA_DIR")
        self.old_avatars_dir = os.environ.get("AVATARS_DIR")
        self.old_portfolio_dir = os.environ.get("PORTFOLIO_DIR")
        self.old_promo_media_dir = os.environ.get("PROMO_MEDIA_DIR")
        self.old_public_base_url = os.environ.get("PROMO_PUBLIC_BASE_URL")

        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        os.environ["BONUS_MEDIA_DIR"] = str(Path(self.tmp.name) / "bonus")
        os.environ["AVATARS_DIR"] = str(Path(self.tmp.name) / "avatars")
        os.environ["PORTFOLIO_DIR"] = str(Path(self.tmp.name) / "portfolio")
        os.environ["PROMO_MEDIA_DIR"] = str(Path(self.tmp.name) / "promo")
        os.environ["PROMO_PUBLIC_BASE_URL"] = "https://crmfit.ru"

        await db.init_db()
        await self._seed_master()

        from src.api.routers import promo_pages

        self.promo_pages = importlib.reload(promo_pages)
        self.master = Master(id=1, tg_id=1001, name="Мария Иванова", invite_token="invite_maria")

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        for key, old_value in {
            "BONUS_MEDIA_DIR": self.old_bonus_media_dir,
            "AVATARS_DIR": self.old_avatars_dir,
            "PORTFOLIO_DIR": self.old_portfolio_dir,
            "PROMO_MEDIA_DIR": self.old_promo_media_dir,
            "PROMO_PUBLIC_BASE_URL": self.old_public_base_url,
        }.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value
        self.tmp.cleanup()

    async def _seed_master(self):
        conn = await db.get_connection()
        try:
            await conn.execute(
                """
                INSERT INTO masters (id, tg_id, name, sphere, invite_token)
                VALUES (1, 1001, 'Мария Иванова', 'Клининг', 'invite_maria')
                """
            )
            await conn.commit()
        finally:
            await conn.close()

    async def _body(self):
        categories = await db.get_promo_categories()
        cleaning = next(c for c in categories if c["slug"] == "cleaning")
        style = cleaning["styles"][0]
        advantages = [
            self.promo_pages.PromoAdvantageBody(text=item["text"], icon=item["icon"])
            for item in cleaning["advantages"][:3]
        ]
        return self.promo_pages.PromoPageBody(
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
            sub_button_text="Запишитесь в пару кликов",
        )

    def _upload_image(self, size=(320, 260), image_format="PNG") -> UploadFile:
        buffer = BytesIO()
        Image.new("RGB", size, (46, 125, 50)).save(buffer, format=image_format)
        buffer.seek(0)
        return UploadFile(file=buffer, filename=f"photo.{image_format.lower()}")

    def _request(self, path: str) -> Request:
        return Request({
            "type": "http",
            "method": "GET",
            "path": path,
            "root_path": "",
            "scheme": "https",
            "server": ("api.crmfit.ru", 443),
            "client": ("127.0.0.1", 12345),
            "headers": [(b"host", b"api.crmfit.ru")],
            "query_string": b"",
        })

    async def _render_response(self, response, request: Request) -> tuple[int, str]:
        chunks: list[bytes] = []
        status_code = 0

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))

        await response(request.scope, receive, send)
        return status_code, b"".join(chunks).decode("utf-8")

    async def _create_page(self):
        body = await self._body()
        return await self.promo_pages.create_promo_page_api(body, master=self.master)

    async def test_create_upload_publish_public_json_and_click_flow(self):
        created = await self._create_page()

        self.assertEqual(created["slug"], "mariya-ivanova")
        self.assertEqual(created["page_url"], "https://crmfit.ru/m/mariya-ivanova")
        self.assertEqual(created["qr_url"], "/media/promo/1/qr.png")
        self.assertTrue((Path(self.tmp.name) / "promo" / "1" / "qr.png").is_file())

        with self.assertRaises(HTTPException) as publish_before_photo:
            await self.promo_pages.publish_promo_page_api(master=self.master)
        self.assertEqual(publish_before_photo.exception.status_code, 400)

        upload = await self.promo_pages.upload_promo_photo_api(
            file=self._upload_image(),
            master=self.master,
        )
        self.assertEqual(upload["photo_url"], "/media/promo/1/photo.jpg")
        self.assertTrue((Path(self.tmp.name) / "promo" / "1" / "photo.jpg").is_file())
        self.assertTrue((Path(self.tmp.name) / "promo" / "1" / "photo_original.png").is_file())

        published = await self.promo_pages.publish_promo_page_api(master=self.master)
        self.assertTrue(published["is_published"])

        public = await self.promo_pages.get_public_promo_page_api("mariya-ivanova")
        self.assertEqual(public["display_name"], "Мария Иванова")
        self.assertEqual(public["style"]["button_bg"], "#2E7D32")
        self.assertTrue(public["bot_link"].endswith("?start=promo_1"))

        clicked = await self.promo_pages.track_public_promo_click_api("mariya-ivanova")
        self.assertEqual(clicked, {"ok": True})
        page = await db.get_promo_page_by_master(1)
        self.assertEqual(page["views_count"], 1)
        self.assertEqual(page["clicks_count"], 1)

    async def test_slug_check_and_update_regenerates_qr(self):
        await self._create_page()

        reserved = await self.promo_pages.check_promo_slug_api("api", master=self.master)
        self.assertFalse(reserved["available"])
        self.assertEqual(reserved["suggestions"], ["api-page"])

        updated = await self.promo_pages.update_promo_slug_api(
            self.promo_pages.SlugBody(slug="maria-cleaning"),
            master=self.master,
        )
        self.assertEqual(updated["slug"], "maria-cleaning")
        self.assertEqual(updated["page_url"], "https://crmfit.ru/m/maria-cleaning")
        self.assertTrue((Path(self.tmp.name) / "promo" / "1" / "qr.png").is_file())

    async def test_invalid_or_small_photo_is_rejected(self):
        await self._create_page()

        with self.assertRaises(HTTPException) as too_small:
            await self.promo_pages.upload_promo_photo_api(
                file=self._upload_image(size=(100, 100)),
                master=self.master,
            )
        self.assertEqual(too_small.exception.status_code, 400)

        with self.assertRaises(HTTPException) as unsupported:
            await self.promo_pages.upload_promo_photo_api(
                file=UploadFile(file=BytesIO(b"not image"), filename="photo.txt"),
                master=self.master,
            )
        self.assertEqual(unsupported.exception.status_code, 415)

    async def test_app_routes_static_mount_and_ssr_promo_page(self):
        await self._create_page()
        await self.promo_pages.upload_promo_photo_api(file=self._upload_image(), master=self.master)
        await self.promo_pages.publish_promo_page_api(master=self.master)

        app_module = importlib.import_module("src.api.app")
        app_module = importlib.reload(app_module)
        paths = {route.path for route in app_module.app.routes}

        self.assertIn("/api/promo/categories", paths)
        self.assertIn("/api/promo/public/{slug}", paths)
        self.assertIn("/m/{page_key}", paths)
        self.assertIn("/media/promo", paths)

        from src.api.routers import landing

        landing = importlib.reload(landing)
        promo_request = self._request("/m/mariya-ivanova")
        promo_response = await landing.landing_page(promo_request, "mariya-ivanova")
        promo_status, promo_html = await self._render_response(promo_response, promo_request)
        self.assertEqual(promo_status, 200)
        self.assertIn("Мария Иванова", promo_html)
        self.assertIn("navigator.sendBeacon('/api/promo/public/mariya-ivanova/click')", promo_html)
        self.assertIn('property="og:title"', promo_html)

        legacy_request = self._request("/m/invite_maria")
        legacy_response = await landing.landing_page(legacy_request, "invite_maria")
        legacy_status, legacy_html = await self._render_response(legacy_response, legacy_request)
        self.assertEqual(legacy_status, 200)
        self.assertIn("Мария Иванова", legacy_html)
