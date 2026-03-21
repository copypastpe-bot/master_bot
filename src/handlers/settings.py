"""Settings handlers: profile, bonus program, services, Google Calendar."""

import asyncio
import io
import qrcode

from aiogram import Bot, Router, F
from aiogram.types import (
    Message, CallbackQuery, BufferedInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from src.config import CLIENT_BOT_USERNAME
from src.database import (
    get_master_by_tg_id,
    update_master,
    update_master_bonus_setting,
    get_services,
    get_service_by_id,
    create_service,
    update_service,
    archive_service,
    get_archived_services,
    restore_service,
)
from src.keyboards import (
    settings_kb,
    settings_profile_kb,
    settings_bonus_kb,
    settings_services_kb,
    settings_invite_kb,
    timezone_kb,
    currency_kb,
    stub_kb,
    gc_connected_kb,
    gc_not_connected_kb,
    gc_disconnect_confirm_kb,
    bonus_message_kb,
    service_edit_kb,
    service_archived_kb,
)
from src.states import (
    ProfileEdit,
    BonusSettingsEdit,
    BonusMessageEdit,
    ServiceAdd,
    ServiceEdit,
)
from src.utils import (
    get_timezone_display,
    get_currency_display,
    get_currency_symbol,
    render_bonus_message,
    DEFAULT_WELCOME_MESSAGE,
    DEFAULT_BIRTHDAY_MESSAGE,
)
from src.handlers.common import edit_home_message
from src import google_calendar

router = Router(name="settings")


# =============================================================================
# Settings Section
# =============================================================================

@router.callback_query(F.data == "settings")
async def cb_settings(callback: CallbackQuery, state: FSMContext) -> None:
    """Show settings section."""
    await state.update_data(current_screen="settings")

    text = (
        "⚙️ Настройки\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_kb())
    await callback.answer()


@router.callback_query(F.data == "settings:profile")
async def cb_settings_profile(callback: CallbackQuery) -> None:
    """Show profile settings."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    tz_display = get_timezone_display(master.timezone)
    curr_display = get_currency_display(master.currency)

    text = (
        "👤 Профиль\n"
        "━━━━━━━━━━━━━━━\n"
        f"Имя: {master.name or 'не указано'}\n"
        f"Сфера: {master.sphere or 'не указано'}\n"
        f"Контакты: {master.contacts or 'не указано'}\n"
        f"Соцсети: {master.socials or 'не указано'}\n"
        f"Режим работы: {master.work_hours or 'не указано'}\n"
        f"Часовой пояс: {tz_display}\n"
        f"Валюта: {curr_display}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_profile_kb())
    await callback.answer()


@router.callback_query(F.data == "profile:timezone")
async def cb_profile_timezone(callback: CallbackQuery) -> None:
    """Show timezone selection."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    tz_display = get_timezone_display(master.timezone)

    text = (
        "🕐 Часовой пояс\n"
        "━━━━━━━━━━━━━━━\n"
        f"Текущий: {tz_display}\n"
        "━━━━━━━━━━━━━━━\n"
        "Выберите ваш часовой пояс:"
    )

    await edit_home_message(callback, text, timezone_kb("settings:profile"))
    await callback.answer()


@router.callback_query(F.data.startswith("set_timezone:"))
async def cb_set_timezone(callback: CallbackQuery) -> None:
    """Set master timezone."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    tz_code = callback.data.split(":")[1]
    tz_display = get_timezone_display(tz_code)

    await update_master_bonus_setting(master.id, "timezone", tz_code)

    await callback.answer(f"✅ Часовой пояс: {tz_display}")

    # Return to profile
    master = await get_master_by_tg_id(tg_id)
    new_tz_display = get_timezone_display(master.timezone)
    curr_display = get_currency_display(master.currency)

    text = (
        "👤 Профиль\n"
        "━━━━━━━━━━━━━━━\n"
        f"Имя: {master.name or 'не указано'}\n"
        f"Сфера: {master.sphere or 'не указано'}\n"
        f"Контакты: {master.contacts or 'не указано'}\n"
        f"Соцсети: {master.socials or 'не указано'}\n"
        f"Режим работы: {master.work_hours or 'не указано'}\n"
        f"Часовой пояс: {new_tz_display}\n"
        f"Валюта: {curr_display}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_profile_kb())


@router.callback_query(F.data == "profile:currency")
async def cb_profile_currency(callback: CallbackQuery) -> None:
    """Show currency selection."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    curr_display = get_currency_display(master.currency)

    text = (
        "💰 Валюта\n"
        "━━━━━━━━━━━━━━━\n"
        f"Текущая: {curr_display}\n"
        "━━━━━━━━━━━━━━━\n"
        "Выберите валюту:"
    )

    await edit_home_message(callback, text, currency_kb("settings:profile"))
    await callback.answer()


@router.callback_query(F.data.startswith("set_currency:"))
async def cb_set_currency(callback: CallbackQuery) -> None:
    """Set master currency."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    curr_code = callback.data.split(":")[1]
    curr_display = get_currency_display(curr_code)

    await update_master(master.id, currency=curr_code)

    await callback.answer(f"✅ Валюта: {curr_display}")

    # Return to profile
    master = await get_master_by_tg_id(tg_id)
    new_curr_display = get_currency_display(master.currency)
    tz_display = get_timezone_display(master.timezone)

    text = (
        "👤 Профиль\n"
        "━━━━━━━━━━━━━━━\n"
        f"Имя: {master.name or 'не указано'}\n"
        f"Сфера: {master.sphere or 'не указано'}\n"
        f"Контакты: {master.contacts or 'не указано'}\n"
        f"Соцсети: {master.socials or 'не указано'}\n"
        f"Режим работы: {master.work_hours or 'не указано'}\n"
        f"Часовой пояс: {tz_display}\n"
        f"Валюта: {new_curr_display}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_profile_kb())


# =============================================================================
# Profile Edit FSM
# =============================================================================

PROFILE_FIELDS = {
    "name": ("Имя", "name"),
    "sphere": ("Сфера деятельности", "sphere"),
    "contacts": ("Контакты", "contacts"),
    "socials": ("Соцсети", "socials"),
    "work_hours": ("Режим работы", "work_hours"),
}


@router.callback_query(F.data.startswith("profile:edit:"))
async def cb_profile_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing a profile field."""
    field = callback.data.split(":")[2]

    if field not in PROFILE_FIELDS:
        await callback.answer("Неизвестное поле")
        return

    field_name, db_field = PROFILE_FIELDS[field]
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    current_value = getattr(master, db_field) or "не указано"

    await state.update_data(profile_edit_field=db_field)

    text = (
        f"✏️ Изменить: {field_name}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Текущее значение: {current_value}\n"
        f"━━━━━━━━━━━━━━━\n"
        "Введите новое значение:"
    )

    await edit_home_message(callback, text, stub_kb("settings:profile"))
    await state.set_state(ProfileEdit.waiting_value)
    await callback.answer()


@router.message(ProfileEdit.waiting_value)
async def profile_edit_value(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save new profile field value."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    db_field = data.get("profile_edit_field")

    value = message.text.strip()[:500]

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await update_master(master.id, **{db_field: value})
    await state.clear()

    # Refresh master data and show updated profile
    master = await get_master_by_tg_id(tg_id)

    text = (
        "👤 Профиль\n"
        "━━━━━━━━━━━━━━━\n"
        f"Имя: {master.name or 'не указано'}\n"
        f"Сфера: {master.sphere or 'не указано'}\n"
        f"Контакты: {master.contacts or 'не указано'}\n"
        f"Соцсети: {master.socials or 'не указано'}\n"
        f"Режим работы: {master.work_hours or 'не указано'}\n"
        f"━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=settings_profile_kb()
            )
        except TelegramBadRequest:
            pass


@router.callback_query(F.data == "profile:gc")
async def cb_profile_gc(callback: CallbackQuery) -> None:
    """Show Google Calendar settings."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    # Check if connected
    email = await google_calendar.get_calendar_account(master.id)

    if email:
        text = (
            "📅 Google Calendar\n"
            "━━━━━━━━━━━━━━━\n"
            f"Статус: ✅ Подключён\n"
            f"Аккаунт: {email}"
        )
        kb = gc_connected_kb()
    else:
        text = (
            "📅 Google Calendar\n"
            "━━━━━━━━━━━━━━━\n"
            "Статус: ❌ Не подключён\n\n"
            "Подключите свой Google Calendar —\n"
            "заказы будут автоматически появляться\n"
            "в вашем расписании."
        )
        kb = gc_not_connected_kb()

    await edit_home_message(callback, text, kb)
    await callback.answer()


@router.callback_query(F.data == "gc:connect")
async def cb_gc_connect(callback: CallbackQuery) -> None:
    """Generate OAuth URL and send to master."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    url = await google_calendar.get_oauth_url(master.id)

    text = (
        "🔗 Для подключения Google Calendar:\n\n"
        f"1. Перейдите по ссылке:\n{url}\n\n"
        "2. Авторизуйтесь в Google\n"
        "3. Разрешите доступ к календарю\n\n"
        "После авторизации бот получит\n"
        "уведомление автоматически."
    )

    await edit_home_message(callback, text, gc_not_connected_kb())
    await callback.answer()


@router.callback_query(F.data == "gc:disconnect")
async def cb_gc_disconnect(callback: CallbackQuery) -> None:
    """Confirm Google Calendar disconnect."""
    text = (
        "❌ Отключить Google Calendar?\n\n"
        "Новые заказы больше не будут\n"
        "добавляться в календарь."
    )

    await edit_home_message(callback, text, gc_disconnect_confirm_kb())
    await callback.answer()


@router.callback_query(F.data == "gc:disconnect:confirm")
async def cb_gc_disconnect_confirm(callback: CallbackQuery) -> None:
    """Disconnect Google Calendar."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    await google_calendar.disconnect_calendar(master.id)

    text = (
        "📅 Google Calendar\n"
        "━━━━━━━━━━━━━━━\n"
        "Статус: ❌ Не подключён\n\n"
        "Google Calendar отключён.\n"
        "Вы можете подключить его снова."
    )

    await edit_home_message(callback, text, gc_not_connected_kb())
    await callback.answer("Отключено")


# =============================================================================
# Bonus Program Settings
# =============================================================================

@router.callback_query(F.data == "settings:bonus")
async def cb_settings_bonus(callback: CallbackQuery) -> None:
    """Show bonus program settings."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

    status = "✅ Включена" if master.bonus_enabled else "❌ Выключена"

    welcome_str = f"{master.bonus_welcome} {curr}" if master.bonus_welcome > 0 else "выкл"

    text = (
        "🎁 Бонусная программа\n"
        "━━━━━━━━━━━━━━━\n"
        f"Статус: {status}\n"
        f"Начисление: {master.bonus_rate}% от суммы заказа\n"
        f"Макс. списание: {master.bonus_max_spend}% суммы заказа\n"
        "━━━━━━━━━━━━━━━\n"
        f"🎉 Приветственный: {welcome_str}\n"
        f"🎂 Бонус на ДР: {master.bonus_birthday} {curr}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_bonus_kb(master.bonus_enabled))
    await callback.answer()


@router.callback_query(F.data == "bonus:toggle")
async def cb_bonus_toggle(callback: CallbackQuery) -> None:
    """Toggle bonus program on/off."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    new_value = not master.bonus_enabled
    await update_master(master.id, bonus_enabled=new_value)

    # Refresh and show updated screen
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)
    status = "✅ Включена" if master.bonus_enabled else "❌ Выключена"

    welcome_str = f"{master.bonus_welcome} {curr}" if master.bonus_welcome > 0 else "выкл"

    text = (
        "🎁 Бонусная программа\n"
        "━━━━━━━━━━━━━━━\n"
        f"Статус: {status}\n"
        f"Начисление: {master.bonus_rate}% от суммы заказа\n"
        f"Макс. списание: {master.bonus_max_spend}% суммы заказа\n"
        "━━━━━━━━━━━━━━━\n"
        f"🎉 Приветственный: {welcome_str}\n"
        f"🎂 Бонус на ДР: {master.bonus_birthday} {curr}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_bonus_kb(master.bonus_enabled))
    await callback.answer("Настройка обновлена!")


BONUS_FIELDS = {
    "rate": ("% начисления", "bonus_rate", "Введите процент начисления (0-100):"),
    "max_spend": ("% списания", "bonus_max_spend", "Введите макс. процент списания (0-100):"),
    "birthday": ("Бонус на ДР", "bonus_birthday", "Введите сумму бонуса на день рождения:"),
}


@router.callback_query(F.data.startswith("bonus:edit:"))
async def cb_bonus_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing a bonus field."""
    field = callback.data.split(":")[2]

    if field not in BONUS_FIELDS:
        await callback.answer("Неизвестное поле")
        return

    field_name, db_field, prompt = BONUS_FIELDS[field]
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    current_value = getattr(master, db_field)

    await state.update_data(bonus_edit_field=db_field, bonus_field_type=field)

    text = (
        f"✏️ Изменить: {field_name}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Текущее значение: {current_value}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{prompt}"
    )

    await edit_home_message(callback, text, stub_kb("settings:bonus"))
    await state.set_state(BonusSettingsEdit.waiting_value)
    await callback.answer()


@router.message(BonusSettingsEdit.waiting_value)
async def bonus_edit_value(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save new bonus field value."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    db_field = data.get("bonus_edit_field")
    field_type = data.get("bonus_field_type")

    try:
        value = int(message.text.strip())
        if field_type in ("rate", "max_spend"):
            if value < 0 or value > 100:
                raise ValueError("Процент должен быть от 0 до 100")
        elif field_type == "birthday":
            if value < 0:
                raise ValueError("Сумма должна быть положительной")
    except ValueError as e:
        await message.answer(str(e) if str(e) else "Введите целое число")
        return

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await update_master(master.id, **{db_field: value})
    await state.clear()

    # Refresh and show updated screen
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)
    status = "✅ Включена" if master.bonus_enabled else "❌ Выключена"
    welcome_str = f"{master.bonus_welcome} {curr}" if master.bonus_welcome > 0 else "выкл"

    text = (
        "🎁 Бонусная программа\n"
        "━━━━━━━━━━━━━━━\n"
        f"Статус: {status}\n"
        f"Начисление: {master.bonus_rate}% от суммы заказа\n"
        f"Макс. списание: {master.bonus_max_spend}% суммы заказа\n"
        "━━━━━━━━━━━━━━━\n"
        f"🎉 Приветственный: {welcome_str}\n"
        f"🎂 Бонус на ДР: {master.bonus_birthday} {curr}\n"
        f"━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=settings_bonus_kb(master.bonus_enabled)
            )
        except TelegramBadRequest:
            pass


# =============================================================================
# Welcome & Birthday Bonus Message Settings
# =============================================================================

@router.callback_query(F.data == "bonus:welcome")
async def cb_bonus_welcome(callback: CallbackQuery) -> None:
    """Show welcome bonus settings."""
    await callback.answer()
    master = await get_master_by_tg_id(callback.from_user.id)
    curr = get_currency_symbol(master.currency)

    amount_str = f"{master.bonus_welcome} {curr}" if master.bonus_welcome > 0 else "выкл"
    text_str = "свой" if master.welcome_message else "стандартный"
    photo_str = "есть" if master.welcome_photo_id else "нет"

    text = (
        "🎉 Приветственный бонус\n"
        "━━━━━━━━━━━━━━━\n"
        f"Сумма: {amount_str}\n"
        f"Текст: {text_str}\n"
        f"Картинка: {photo_str}\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, bonus_message_kb("welcome"))


@router.callback_query(F.data == "bonus:birthday")
async def cb_bonus_birthday(callback: CallbackQuery) -> None:
    """Show birthday bonus settings."""
    await callback.answer()
    master = await get_master_by_tg_id(callback.from_user.id)
    curr = get_currency_symbol(master.currency)

    text_str = "свой" if master.birthday_message else "стандартный"
    photo_str = "есть" if master.birthday_photo_id else "нет"

    text = (
        "🎂 Бонус на день рождения\n"
        "━━━━━━━━━━━━━━━\n"
        f"Сумма: {master.bonus_birthday} {curr}\n"
        f"Текст: {text_str}\n"
        f"Картинка: {photo_str}\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, bonus_message_kb("birthday"))


@router.callback_query(F.data.regexp(r"^bonus:(welcome|birthday):amount$"))
async def cb_bonus_message_amount(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt for bonus amount."""
    await callback.answer()
    bonus_type = callback.data.split(":")[1]

    await state.update_data(bonus_type=bonus_type)
    await state.set_state(BonusMessageEdit.waiting_amount)

    text = "💰 Введите сумму бонуса (0 = выключить):"
    await edit_home_message(callback, text, stub_kb(f"bonus:{bonus_type}"))


@router.callback_query(F.data.regexp(r"^bonus:(welcome|birthday):text$"))
async def cb_bonus_message_text(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt for custom message text."""
    await callback.answer()
    bonus_type = callback.data.split(":")[1]

    await state.update_data(bonus_type=bonus_type)
    await state.set_state(BonusMessageEdit.waiting_text)

    variables = "{имя}, {мастер}, {бонус}" + (", {баланс}" if bonus_type == "birthday" else "")
    text = (
        f"✏️ Введите текст сообщения.\n\n"
        f"Переменные: {variables}\n\n"
        f"Отправьте «сброс» для возврата к стандартному."
    )
    await edit_home_message(callback, text, stub_kb(f"bonus:{bonus_type}"))


@router.callback_query(F.data.regexp(r"^bonus:(welcome|birthday):photo$"))
async def cb_bonus_message_photo(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt for photo upload."""
    await callback.answer()
    bonus_type = callback.data.split(":")[1]

    await state.update_data(bonus_type=bonus_type)
    await state.set_state(BonusMessageEdit.waiting_photo)

    text = "🖼 Отправьте картинку или «удалить» для удаления."
    await edit_home_message(callback, text, stub_kb(f"bonus:{bonus_type}"))


@router.callback_query(F.data.regexp(r"^bonus:(welcome|birthday):preview$"))
async def cb_bonus_message_preview(callback: CallbackQuery, bot: Bot) -> None:
    """Send preview of bonus message."""
    await callback.answer("Отправляю предпросмотр...")
    bonus_type = callback.data.split(":")[1]
    master = await get_master_by_tg_id(callback.from_user.id)

    if bonus_type == "welcome":
        template = master.welcome_message
        default = DEFAULT_WELCOME_MESSAGE
        amount = master.bonus_welcome
        photo_id = master.welcome_photo_id
        balance = 0
    else:
        template = master.birthday_message
        default = DEFAULT_BIRTHDAY_MESSAGE
        amount = master.bonus_birthday
        photo_id = master.birthday_photo_id
        balance = 1500

    text = render_bonus_message(
        template=template,
        default=default,
        client_name="Анна",
        master_name=master.name,
        bonus_amount=amount,
        balance=balance,
        currency=get_currency_symbol(master.currency),
    )

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Вернуться", callback_data=f"bonus:{bonus_type}:back")]
    ])

    try:
        if photo_id:
            await bot.send_photo(callback.from_user.id, photo_id, caption=text, reply_markup=back_kb)
        else:
            await bot.send_message(callback.from_user.id, text, reply_markup=back_kb)
    except Exception as e:
        await bot.send_message(callback.from_user.id, f"❌ Ошибка: {e}")


@router.callback_query(F.data.regexp(r"^bonus:(welcome|birthday):back$"))
async def cb_bonus_message_back(callback: CallbackQuery, bot: Bot) -> None:
    """Return from preview to bonus menu - delete preview message."""
    bonus_type = callback.data.split(":")[1]

    # Delete the preview message
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    # Show bonus submenu in home message
    master = await get_master_by_tg_id(callback.from_user.id)
    curr = get_currency_symbol(master.currency)

    if bonus_type == "welcome":
        amount_str = f"{master.bonus_welcome} {curr}" if master.bonus_welcome > 0 else "выкл"
        text_str = "свой" if master.welcome_message else "стандартный"
        photo_str = "есть" if master.welcome_photo_id else "нет"
        text = (
            "🎉 Приветственный бонус\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {amount_str}\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )
    else:
        text_str = "свой" if master.birthday_message else "стандартный"
        photo_str = "есть" if master.birthday_photo_id else "нет"
        text = (
            "🎂 Бонус на день рождения\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {master.bonus_birthday} {curr}\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )

    # Edit home message
    if master.home_message_id:
        try:
            await bot.edit_message_text(
                text,
                chat_id=callback.from_user.id,
                message_id=master.home_message_id,
                reply_markup=bonus_message_kb(bonus_type)
            )
        except Exception:
            pass

    await callback.answer()


@router.message(BonusMessageEdit.waiting_amount)
async def on_bonus_message_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save bonus amount."""
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    data = await state.get_data()
    bonus_type = data.get("bonus_type")
    master = await get_master_by_tg_id(message.from_user.id)

    try:
        amount = int(message.text.strip())
        if amount < 0:
            raise ValueError()
    except ValueError:
        error_msg = await bot.send_message(message.chat.id, "❌ Введите число >= 0")
        await asyncio.sleep(2)
        try:
            await error_msg.delete()
        except TelegramBadRequest:
            pass
        return

    field = "bonus_welcome" if bonus_type == "welcome" else "bonus_birthday"
    await update_master_bonus_setting(master.id, field, amount)
    await state.clear()

    # Return to bonus submenu
    master = await get_master_by_tg_id(message.from_user.id)
    curr = get_currency_symbol(master.currency)

    if bonus_type == "welcome":
        amount_str = f"{master.bonus_welcome} {curr}" if master.bonus_welcome > 0 else "выкл"
        text_str = "свой" if master.welcome_message else "стандартный"
        photo_str = "есть" if master.welcome_photo_id else "нет"
        text = (
            "🎉 Приветственный бонус\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {amount_str}\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )
    else:
        text_str = "свой" if master.birthday_message else "стандартный"
        photo_str = "есть" if master.birthday_photo_id else "нет"
        text = (
            "🎂 Бонус на день рождения\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {master.bonus_birthday} {curr}\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=bonus_message_kb(bonus_type)
            )
        except TelegramBadRequest:
            pass


@router.message(BonusMessageEdit.waiting_text)
async def on_bonus_message_text(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save custom message text."""
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    data = await state.get_data()
    bonus_type = data.get("bonus_type")
    master = await get_master_by_tg_id(message.from_user.id)

    text_input = message.text.strip()
    value = None if text_input.lower() == "сброс" else text_input

    field = "welcome_message" if bonus_type == "welcome" else "birthday_message"
    await update_master_bonus_setting(master.id, field, value)
    await state.clear()

    # Return to bonus submenu
    master = await get_master_by_tg_id(message.from_user.id)
    curr = get_currency_symbol(master.currency)

    if bonus_type == "welcome":
        amount_str = f"{master.bonus_welcome} {curr}" if master.bonus_welcome > 0 else "выкл"
        text_str = "свой" if master.welcome_message else "стандартный"
        photo_str = "есть" if master.welcome_photo_id else "нет"
        text = (
            "🎉 Приветственный бонус\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {amount_str}\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )
    else:
        text_str = "свой" if master.birthday_message else "стандартный"
        photo_str = "есть" if master.birthday_photo_id else "нет"
        text = (
            "🎂 Бонус на день рождения\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {master.bonus_birthday} {curr}\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=bonus_message_kb(bonus_type)
            )
        except TelegramBadRequest:
            pass


@router.message(BonusMessageEdit.waiting_photo, F.photo)
async def on_bonus_message_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save photo file_id."""
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    data = await state.get_data()
    bonus_type = data.get("bonus_type")
    master = await get_master_by_tg_id(message.from_user.id)

    photo_id = message.photo[-1].file_id

    field = "welcome_photo_id" if bonus_type == "welcome" else "birthday_photo_id"
    await update_master_bonus_setting(master.id, field, photo_id)
    await state.clear()

    # Return to bonus submenu
    master = await get_master_by_tg_id(message.from_user.id)
    curr = get_currency_symbol(master.currency)

    if bonus_type == "welcome":
        amount_str = f"{master.bonus_welcome} {curr}" if master.bonus_welcome > 0 else "выкл"
        text_str = "свой" if master.welcome_message else "стандартный"
        photo_str = "есть" if master.welcome_photo_id else "нет"
        text = (
            "🎉 Приветственный бонус\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {amount_str}\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )
    else:
        text_str = "свой" if master.birthday_message else "стандартный"
        photo_str = "есть" if master.birthday_photo_id else "нет"
        text = (
            "🎂 Бонус на день рождения\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {master.bonus_birthday} {curr}\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=bonus_message_kb(bonus_type)
            )
        except TelegramBadRequest:
            pass


@router.message(BonusMessageEdit.waiting_photo)
async def on_bonus_message_photo_text(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle text in photo state (for 'удалить')."""
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    data = await state.get_data()
    bonus_type = data.get("bonus_type")
    master = await get_master_by_tg_id(message.from_user.id)

    if message.text and message.text.strip().lower() == "удалить":
        field = "welcome_photo_id" if bonus_type == "welcome" else "birthday_photo_id"
        await update_master_bonus_setting(master.id, field, None)

    await state.clear()

    # Return to bonus submenu
    master = await get_master_by_tg_id(message.from_user.id)
    curr = get_currency_symbol(master.currency)

    if bonus_type == "welcome":
        amount_str = f"{master.bonus_welcome} {curr}" if master.bonus_welcome > 0 else "выкл"
        text_str = "свой" if master.welcome_message else "стандартный"
        photo_str = "есть" if master.welcome_photo_id else "нет"
        text = (
            "🎉 Приветственный бонус\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {amount_str}\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )
    else:
        text_str = "свой" if master.birthday_message else "стандартный"
        photo_str = "есть" if master.birthday_photo_id else "нет"
        text = (
            "🎂 Бонус на день рождения\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {master.bonus_birthday} {curr}\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=bonus_message_kb(bonus_type)
            )
        except TelegramBadRequest:
            pass


# =============================================================================
# Services Management
# =============================================================================

@router.callback_query(F.data == "settings:services")
async def cb_settings_services(callback: CallbackQuery) -> None:
    """Show services catalog."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} {curr}"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        "🛠 Справочник услуг\n"
        "━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_services_kb(services, currency=curr))
    await callback.answer()


# =============================================================================
# Services Management FSM
# =============================================================================

@router.callback_query(F.data == "settings:services:new")
async def cb_services_new(callback: CallbackQuery, state: FSMContext) -> None:
    """Start adding new service."""
    text = (
        "🛠 Новая услуга — Шаг 1/3\n"
        "━━━━━━━━━━━━━━━\n"
        "Введите название услуги:"
    )
    await edit_home_message(callback, text, stub_kb("settings:services"))
    await state.set_state(ServiceAdd.name)
    await callback.answer()


@router.message(ServiceAdd.name)
async def service_add_name(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 1: Service name."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    name = message.text.strip()[:200]
    await state.update_data(service_name=name)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    text = (
        "🛠 Новая услуга — Шаг 2/3\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {name}\n"
        "━━━━━━━━━━━━━━━\n"
        "💰 Введите цену (число) или нажмите «Без цены»:"
    )

    no_price_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Без цены", callback_data="service:no_price")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="settings:services"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=no_price_kb
            )
        except TelegramBadRequest:
            pass

    await state.set_state(ServiceAdd.price)


@router.callback_query(ServiceAdd.price, F.data == "service:no_price")
async def service_add_no_price(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 2: No price - go to description."""
    await state.update_data(service_price=None)

    data = await state.get_data()
    name = data.get("service_name")

    text = (
        "🛠 Новая услуга — Шаг 3/3\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {name}\n"
        f"Цена: —\n"
        "━━━━━━━━━━━━━━━\n"
        "📝 Введите описание услуги или нажмите «Пропустить»:"
    )

    skip_desc_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="service:skip_description")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="settings:services"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])

    await edit_home_message(callback, text, skip_desc_kb)
    await state.set_state(ServiceAdd.description)
    await callback.answer()


@router.message(ServiceAdd.price)
async def service_add_price(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 2: Service price - go to description."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    try:
        price = int(message.text.strip())
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("Введите положительное число")
        return

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await state.update_data(service_price=price)

    data = await state.get_data()
    name = data.get("service_name")
    curr = get_currency_symbol(master.currency)

    text = (
        "🛠 Новая услуга — Шаг 3/3\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {name}\n"
        f"Цена: {price} {curr}\n"
        "━━━━━━━━━━━━━━━\n"
        "📝 Введите описание услуги или нажмите «Пропустить»:"
    )

    skip_desc_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="service:skip_description")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="settings:services"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=skip_desc_kb
            )
        except TelegramBadRequest:
            pass

    await state.set_state(ServiceAdd.description)


@router.callback_query(ServiceAdd.description, F.data == "service:skip_description")
async def service_add_skip_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 3: Skip description - save service."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

    data = await state.get_data()
    name = data.get("service_name")
    price = data.get("service_price")

    await create_service(master.id, name, price, None)
    await state.clear()

    # Show updated services list
    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} {curr}"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"✅ Услуга «{name}» добавлена!\n"
        "━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_services_kb(services, currency=curr))
    await callback.answer("Услуга добавлена!")


@router.message(ServiceAdd.description)
async def service_add_description(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 3: Service description - save service."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    description = message.text.strip()[:500]

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    data = await state.get_data()
    name = data.get("service_name")
    price = data.get("service_price")

    await create_service(master.id, name, price, description)
    await state.clear()

    # Show updated services list
    services = await get_services(master.id)
    curr = get_currency_symbol(master.currency)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} {curr}"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"✅ Услуга «{name}» добавлена!\n"
        "━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=settings_services_kb(services, currency=curr)
            )
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.regexp(r"^settings:services:edit:\d+$"))
async def cb_services_edit(callback: CallbackQuery) -> None:
    """Show service edit menu."""
    service_id = int(callback.data.split(":")[3])
    service = await get_service_by_id(service_id)

    if not service:
        await callback.answer("Услуга не найдена")
        return

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

    description_line = f"📝 {service.description}\n" if service.description else ""
    text = (
        f"🛠 {service.name}\n"
        f"💰 {service.price or '—'} {curr}\n"
        f"{description_line}"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, service_edit_kb(service_id))
    await callback.answer()


@router.callback_query(F.data.regexp(r"^settings:services:edit:name:\d+$"))
async def cb_services_edit_name(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing service name."""
    service_id = int(callback.data.split(":")[4])
    service = await get_service_by_id(service_id)

    if not service:
        await callback.answer("Услуга не найдена")
        return

    await state.update_data(edit_service_id=service_id)

    text = (
        f"✏️ Изменить название\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Текущее: {service.name}\n"
        f"━━━━━━━━━━━━━━━\n"
        "Введите новое название:"
    )

    await edit_home_message(callback, text, stub_kb(f"settings:services:edit:{service_id}"))
    await state.set_state(ServiceEdit.name)
    await callback.answer()


@router.message(ServiceEdit.name)
async def service_edit_name(message: Message, state: FSMContext, bot: Bot) -> None:
    """Update service name."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

    name = message.text.strip()[:200]

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    data = await state.get_data()
    service_id = data.get("edit_service_id")

    await update_service(service_id, name=name)
    await state.clear()

    # Show services list
    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} {curr}"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"✅ Название обновлено!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🛠 Справочник услуг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=settings_services_kb(services, currency=curr)
            )
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.regexp(r"^settings:services:edit:price:\d+$"))
async def cb_services_edit_price(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing service price."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

    service_id = int(callback.data.split(":")[4])
    service = await get_service_by_id(service_id)

    if not service:
        await callback.answer("Услуга не найдена")
        return

    await state.update_data(edit_service_id=service_id)

    text = (
        f"💰 Изменить цену\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Текущая: {service.price or '—'} {curr}\n"
        f"━━━━━━━━━━━━━━━\n"
        "Введите новую цену (число):"
    )

    price_edit_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Убрать цену", callback_data=f"service:remove_price:{service_id}")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"settings:services:edit:{service_id}"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])

    await edit_home_message(callback, text, price_edit_kb)
    await state.set_state(ServiceEdit.price)
    await callback.answer()


@router.callback_query(ServiceEdit.price, F.data.startswith("service:remove_price:"))
async def service_remove_price(callback: CallbackQuery, state: FSMContext) -> None:
    """Remove service price."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

    service_id = int(callback.data.split(":")[2])

    await update_service(service_id, price=None)
    await state.clear()

    # Show services list
    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} {curr}"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"✅ Цена убрана!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🛠 Справочник услуг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_services_kb(services, currency=curr))
    await callback.answer("Цена убрана!")


@router.message(ServiceEdit.price)
async def service_edit_price(message: Message, state: FSMContext, bot: Bot) -> None:
    """Update service price."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

    try:
        price = int(message.text.strip())
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("Введите положительное число")
        return

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    data = await state.get_data()
    service_id = data.get("edit_service_id")

    await update_service(service_id, price=price)
    await state.clear()

    # Show services list
    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} {curr}"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"✅ Цена обновлена!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🛠 Справочник услуг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=settings_services_kb(services, currency=curr)
            )
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.regexp(r"^settings:services:edit:description:\d+$"))
async def cb_services_edit_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing service description."""
    service_id = int(callback.data.split(":")[4])
    service = await get_service_by_id(service_id)

    if not service:
        await callback.answer("Услуга не найдена")
        return

    await state.update_data(edit_service_id=service_id)

    current_desc = service.description or "—"
    text = (
        f"📝 Изменить описание\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Текущее: {current_desc}\n"
        f"━━━━━━━━━━━━━━━\n"
        "Введите новое описание:"
    )

    desc_edit_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Убрать описание", callback_data=f"service:remove_description:{service_id}")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"settings:services:edit:{service_id}"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])

    await edit_home_message(callback, text, desc_edit_kb)
    await state.set_state(ServiceEdit.description)
    await callback.answer()


@router.callback_query(ServiceEdit.description, F.data.startswith("service:remove_description:"))
async def service_remove_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Remove service description."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)
    service_id = int(callback.data.split(":")[2])

    await update_service(service_id, description=None)
    await state.clear()

    # Show services list
    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} {curr}"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"✅ Описание убрано!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🛠 Справочник услуг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_services_kb(services, currency=curr))
    await callback.answer("Описание убрано!")


@router.message(ServiceEdit.description)
async def service_edit_description(message: Message, state: FSMContext, bot: Bot) -> None:
    """Update service description."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

    description = message.text.strip()[:500]

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    data = await state.get_data()
    service_id = data.get("edit_service_id")

    await update_service(service_id, description=description)
    await state.clear()

    # Show services list
    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} {curr}"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"✅ Описание обновлено!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🛠 Справочник услуг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=settings_services_kb(services, currency=curr)
            )
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.regexp(r"^settings:services:archive:\d+$"))
async def cb_services_archive(callback: CallbackQuery) -> None:
    """Archive a service."""
    service_id = int(callback.data.split(":")[3])
    service = await get_service_by_id(service_id)

    if not service:
        await callback.answer("Услуга не найдена")
        return

    await archive_service(service_id)

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

    # Show updated services list
    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} {curr}"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"📦 Услуга «{service.name}» в архиве\n"
        "━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_services_kb(services, currency=curr))
    await callback.answer("Услуга в архиве")


@router.callback_query(F.data == "settings:services:archive")
async def cb_services_show_archive(callback: CallbackQuery) -> None:
    """Show archived services."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

    services = await get_archived_services(master.id)

    text = (
        "📦 Архив услуг\n"
        "━━━━━━━━━━━━━━━\n"
        "Нажмите на услугу, чтобы восстановить:"
    )

    await edit_home_message(callback, text, service_archived_kb(services, curr))
    await callback.answer()


@router.callback_query(F.data.regexp(r"^settings:services:restore:\d+$"))
async def cb_services_restore(callback: CallbackQuery) -> None:
    """Restore archived service."""
    service_id = int(callback.data.split(":")[3])
    service = await get_service_by_id(service_id)

    if not service:
        await callback.answer("Услуга не найдена")
        return

    await restore_service(service_id)

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

    # Show updated archive
    services = await get_archived_services(master.id)

    text = (
        f"✅ Услуга «{service.name}» восстановлена!\n"
        "━━━━━━━━━━━━━━━\n"
        "📦 Архив услуг:"
    )

    await edit_home_message(callback, text, service_archived_kb(services, curr))
    await callback.answer("Услуга восстановлена!")


# =============================================================================
# Invite Link and QR Code
# =============================================================================

@router.callback_query(F.data == "settings:invite")
async def cb_settings_invite(callback: CallbackQuery) -> None:
    """Show invite link."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    invite_link = f"t.me/{CLIENT_BOT_USERNAME}?start={master.invite_token}"

    text = (
        "🔗 Ссылка для клиентов\n"
        "━━━━━━━━━━━━━━━\n"
        f"{invite_link}\n\n"
        "Отправьте эту ссылку клиентам или\n"
        "разместите в соцсетях.\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_invite_kb())
    await callback.answer()


@router.callback_query(F.data == "settings:invite:qr")
async def cb_settings_invite_qr(callback: CallbackQuery, bot: Bot) -> None:
    """Generate and send QR code for invite link."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    invite_url = f"https://t.me/{CLIENT_BOT_USERNAME}?start={master.invite_token}"

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(invite_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Вернуться", callback_data="settings:invite:qr:back")]
    ])

    await bot.send_photo(
        chat_id=callback.from_user.id,
        photo=BufferedInputFile(img_bytes.read(), filename="qr_invite.png"),
        caption=f"📱 QR-код для приглашения клиентов\n\nПокажите клиенту для быстрой регистрации",
        reply_markup=back_kb
    )
    await callback.answer()


@router.callback_query(F.data == "settings:invite:qr:back")
async def cb_settings_invite_qr_back(callback: CallbackQuery, bot: Bot) -> None:
    """Return from QR code to invite settings."""
    # Delete QR message
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    # Show invite settings in home message
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    invite_url = f"https://t.me/{CLIENT_BOT_USERNAME}?start={master.invite_token}"
    text = (
        "🔗 Инвайт-ссылка\n"
        "━━━━━━━━━━━━━━━\n"
        f"{invite_url}\n"
        "━━━━━━━━━━━━━━━\n"
        "Отправьте клиентам для регистрации"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                text,
                chat_id=callback.from_user.id,
                message_id=master.home_message_id,
                reply_markup=settings_invite_kb()
            )
        except Exception:
            pass

    await callback.answer()
