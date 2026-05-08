import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from src import database as db


class ThemePresetBackendTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        self.old_bonus_media_dir = os.environ.get("BONUS_MEDIA_DIR")
        self.old_avatars_dir = os.environ.get("AVATARS_DIR")
        self.old_portfolio_dir = os.environ.get("PORTFOLIO_DIR")
        self.old_promo_media_dir = os.environ.get("PROMO_MEDIA_DIR")

        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        os.environ["BONUS_MEDIA_DIR"] = str(Path(self.tmp.name) / "bonus")
        os.environ["AVATARS_DIR"] = str(Path(self.tmp.name) / "avatars")
        os.environ["PORTFOLIO_DIR"] = str(Path(self.tmp.name) / "portfolio")
        os.environ["PROMO_MEDIA_DIR"] = str(Path(self.tmp.name) / "promo")

        await db.init_db()
        await self._seed_master()

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        for key, old_value in {
            "BONUS_MEDIA_DIR": self.old_bonus_media_dir,
            "AVATARS_DIR": self.old_avatars_dir,
            "PORTFOLIO_DIR": self.old_portfolio_dir,
            "PROMO_MEDIA_DIR": self.old_promo_media_dir,
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
                VALUES (1, 1001, 'Анна Иванова', 'Маникюр', 'invite_anna')
                """
            )
            await conn.commit()
        finally:
            await conn.close()

    async def test_init_db_adds_theme_preset_column(self):
        conn = await db.get_connection()
        try:
            cursor = await conn.execute("PRAGMA table_info(masters)")
            columns = {row["name"]: row for row in await cursor.fetchall()}
        finally:
            await conn.close()

        self.assertIn("theme_preset", columns)
        self.assertEqual(columns["theme_preset"]["dflt_value"], "'ocean'")

    async def test_master_row_falls_back_to_ocean_for_null_or_empty_theme(self):
        conn = await db.get_connection()
        try:
            await conn.execute("UPDATE masters SET theme_preset = NULL WHERE id = 1")
            await conn.commit()
        finally:
            await conn.close()

        master = await db.get_master_by_id(1)
        self.assertEqual(master.theme_preset, "ocean")

        conn = await db.get_connection()
        try:
            await conn.execute("UPDATE masters SET theme_preset = '' WHERE id = 1")
            await conn.commit()
        finally:
            await conn.close()

        master = await db.get_master_by_id(1)
        self.assertEqual(master.theme_preset, "ocean")

    async def test_master_me_and_dashboard_include_theme_preset(self):
        from src.api.routers.master import dashboard

        dashboard = importlib.reload(dashboard)

        master = await db.get_master_by_id(1)
        me = await dashboard.get_master_me(master=master)
        stats = await dashboard.get_master_dashboard(master=master)

        self.assertEqual(me["theme_preset"], "ocean")
        self.assertEqual(stats["theme_preset"], "ocean")

        await db.update_master(1, theme_preset="lavender")
        master = await db.get_master_by_id(1)
        me = await dashboard.get_master_me(master=master)
        stats = await dashboard.get_master_dashboard(master=master)

        self.assertEqual(me["theme_preset"], "lavender")
        self.assertEqual(stats["theme_preset"], "lavender")

    async def test_theme_preset_endpoint_updates_and_rejects_invalid_values(self):
        from src.api.dependencies import get_current_master

        async def override_master():
            return await db.get_master_by_id(1)

        app_module = importlib.import_module("src.api.app")
        app_module = importlib.reload(app_module)
        app = app_module.app
        app.dependency_overrides[get_current_master] = override_master
        try:
            invalid_status, invalid_body = await self._request_json(
                app,
                "PUT",
                "/api/master/theme-preset",
                {"theme_preset": "invalid"},
            )
            self.assertEqual(invalid_status, 422)
            self.assertIn("Unknown theme preset: invalid", invalid_body["detail"][0]["msg"])

            valid_status, valid_body = await self._request_json(
                app,
                "PUT",
                "/api/master/theme-preset",
                {"theme_preset": "lavender"},
            )
            self.assertEqual(valid_status, 200)
            self.assertEqual(valid_body, {"ok": True})
        finally:
            app.dependency_overrides.clear()

        master = await db.get_master_by_id(1)
        self.assertEqual(master.theme_preset, "lavender")

    async def _request_json(self, app, method: str, path: str, payload: dict) -> tuple[int, dict]:
        body = json.dumps(payload).encode("utf-8")
        headers = [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
        ]
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "path": path,
            "raw_path": path.encode("ascii"),
            "root_path": "",
            "scheme": "http",
            "query_string": b"",
            "headers": headers,
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
        }
        messages = []
        delivered = False

        async def receive():
            nonlocal delivered
            if delivered:
                return {"type": "http.disconnect"}
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        await app(scope, receive, send)

        status_code = next(
            message["status"]
            for message in messages
            if message["type"] == "http.response.start"
        )
        payload_bytes = b"".join(
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        )
        return status_code, json.loads(payload_bytes.decode("utf-8"))
