import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from src.models import Client, Master, MasterClient


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

    def test_client_bot_parses_promo_start_payload(self):
        module = importlib.import_module("src.client_bot")

        self.assertEqual(module.parse_start_payload("promo_42"), ("promo", 42))
        self.assertEqual(module.parse_start_payload("promo_bad"), ("invalid_promo", None))
        self.assertEqual(module.parse_start_payload("invite_abc"), ("invite", "abc"))
        self.assertEqual(module.parse_start_payload("plain-token"), ("invite", "plain-token"))
        self.assertEqual(module.parse_start_payload(None), ("empty", None))


class ClientBotPromoStartTest(unittest.IsolatedAsyncioTestCase):
    async def test_promo_start_links_existing_client_to_master_by_id(self):
        module = importlib.import_module("src.client_bot")
        client = Client(id=3, tg_id=777, name="Анна")
        master = Master(id=42, tg_id=1001, name="Мария", invite_token="invite_maria", bonus_welcome=100)
        master_client = MasterClient(id=5, master_id=42, client_id=3, bonus_balance=100)
        message = SimpleNamespace(
            text="/start promo_42",
            from_user=SimpleNamespace(id=777),
            chat=SimpleNamespace(id=777),
            delete=AsyncMock(),
        )
        state = SimpleNamespace(clear=AsyncMock(), update_data=AsyncMock())
        bot = SimpleNamespace(send_message=AsyncMock())

        with (
            patch.object(module, "get_client_by_tg_id", AsyncMock(return_value=client)),
            patch.object(module, "get_master_by_id", AsyncMock(return_value=master)) as get_master_by_id,
            patch.object(module, "get_master_by_invite_token", AsyncMock()) as get_master_by_invite_token,
            patch.object(module, "get_master_client", AsyncMock(side_effect=[None, master_client, master_client])),
            patch.object(module, "link_existing_client_to_master", AsyncMock(return_value=True)) as link_existing,
            patch.object(module, "accrue_welcome_bonus", AsyncMock(return_value=100)) as accrue,
            patch.object(module, "ensure_home_reply_keyboard", AsyncMock()) as ensure_home,
            patch.object(module, "show_home", AsyncMock()) as show_home,
            patch.object(module, "get_all_client_masters_by_tg_id", AsyncMock(return_value=[{"master_id": 42}])),
        ):
            await module.cmd_start(message, state, bot)

        get_master_by_id.assert_awaited_once_with(42)
        get_master_by_invite_token.assert_not_awaited()
        link_existing.assert_awaited_once_with(client.id, master.id)
        accrue.assert_awaited_once_with(master.id, client.id)
        ensure_home.assert_awaited_once_with(bot, message.chat.id)
        show_home.assert_awaited_once_with(bot, client, master, master_client, message.chat.id, force_new=True)
        self.assertTrue(any("100" in call.args[1] for call in bot.send_message.await_args_list))
