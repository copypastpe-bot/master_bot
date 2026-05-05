import unittest


class ClientBotKeyboardTest(unittest.TestCase):
    def test_home_client_keyboard_has_inline_sections_and_optional_master_switch(self):
        from src.keyboards import home_client_kb

        single = home_client_kb(multi_master=False)
        single_buttons = [button for row in single.inline_keyboard for button in row]
        self.assertEqual(
            [button.callback_data for button in single_buttons],
            ["bonuses", "history", "promos", "master_info", "client_settings"],
        )

        multi = home_client_kb(multi_master=True)
        multi_buttons = [button for row in multi.inline_keyboard for button in row]
        self.assertEqual(multi_buttons[-1].text, "👥 Сменить мастера")
        self.assertEqual(multi_buttons[-1].callback_data, "change_master")

    def test_client_notification_keyboard_toggles_all_supported_fields(self):
        from src.keyboards import client_notifications_back_kb

        kb = client_notifications_back_kb(
            notify_24h=True,
            notify_1h=False,
            notify_marketing=True,
            notify_promos=False,
        )
        buttons = [button for row in kb.inline_keyboard for button in row]

        self.assertEqual(buttons[0].text, "✅ Напоминание за 24ч")
        self.assertEqual(buttons[0].callback_data, "notifications:toggle:notify_24h")
        self.assertEqual(buttons[1].text, "❌ Напоминание за 1ч")
        self.assertEqual(buttons[1].callback_data, "notifications:toggle:notify_1h")
        self.assertEqual(buttons[2].text, "✅ Маркетинг")
        self.assertEqual(buttons[2].callback_data, "notifications:toggle:notify_marketing")
        self.assertEqual(buttons[3].text, "❌ Акции")
        self.assertEqual(buttons[3].callback_data, "notifications:toggle:notify_promos")
        self.assertEqual(buttons[4].callback_data, "client_settings")
