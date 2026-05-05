import importlib
import os
import tempfile
import unittest


class ClientAppApiImportTest(unittest.TestCase):
    def test_client_app_router_is_registered(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["BONUS_MEDIA_DIR"] = tmp
            os.environ["AVATARS_DIR"] = tmp
            os.environ["PORTFOLIO_DIR"] = tmp

            app_module = importlib.import_module("src.api.app")
            importlib.reload(app_module)

            paths = {route.path for route in app_module.app.routes}

        self.assertIn("/api/client/master/{master_id}/profile", paths)
        self.assertIn("/api/client/master/{master_id}/activity", paths)
        self.assertIn("/api/client/master/{master_id}/history", paths)
        self.assertIn("/api/client/master/{master_id}/settings", paths)
        self.assertIn("/api/client/orders/{order_id}/confirm", paths)
        self.assertIn("/api/client/orders/{order_id}/review", paths)
        self.assertIn("/api/client/review", paths)
        self.assertIn("/api/public/master/{invite_token}", paths)
        self.assertIn("/api/public/photo/{file_id:path}", paths)
        self.assertIn("/api/master/portfolio", paths)
