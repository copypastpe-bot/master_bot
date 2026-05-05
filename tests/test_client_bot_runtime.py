import importlib
import unittest


class ClientBotRuntimeTest(unittest.TestCase):
    def test_client_bot_registers_inline_navigation_handlers(self):
        module = importlib.import_module("src.client_bot")
        callback_names = {
            item.callback.__name__
            for item in module.router.callback_query.handlers
        }

        expected = {
            "cb_home",
            "cb_bonuses",
            "cb_history",
            "cb_promos",
            "cb_master_info",
            "cb_master_call",
            "cb_client_settings",
            "cb_notifications",
            "cb_notifications_toggle",
            "cb_client_support",
            "cb_client_delete_profile",
            "cb_change_master",
            "cb_select_master",
            "handle_feedback_rating",
            "handle_order_confirmation",
            "handle_contact_order",
        }
        self.assertTrue(expected.issubset(callback_names))

        removed = {
            "cb_order_request",
            "cb_question",
            "cb_media",
            "handle_reschedule_start",
            "handle_cancel_start",
        }
        self.assertTrue(removed.isdisjoint(callback_names))

    def test_client_bot_has_no_miniapp_webapp_entrypoints(self):
        module = importlib.import_module("src.client_bot")
        callback_names = {
            item.callback.__name__
            for item in module.router.callback_query.handlers
        }

        self.assertIn("handle_feedback_rating", callback_names)
        self.assertIn("handle_order_confirmation", callback_names)
        self.assertIn("handle_contact_order", callback_names)

        self.assertFalse(hasattr(module, "client_miniapp_entry_kb"))
        self.assertFalse(hasattr(module, "build_miniapp_entry_text"))
        self.assertFalse(hasattr(module, "send_miniapp_entry"))
