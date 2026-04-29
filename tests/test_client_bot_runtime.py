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
