"""Client bot: Mini App entry point and notification actions."""

import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    ReplyKeyboardRemove,
    WebAppInfo,
)

from src.config import CLIENT_BOT_TOKEN, CLIENT_MINIAPP_URL, LOG_LEVEL, MASTER_BOT_TOKEN
from src.database import (
    accrue_welcome_bonus,
    anonymize_client,
    confirm_order_by_client,
    create_client,
    get_all_client_masters_by_tg_id,
    get_client_by_phone,
    get_client_by_tg_id,
    get_master_by_id,
    get_master_by_invite_token,
    get_master_client,
    get_order_by_id_for_feedback,
    get_order_notification_context,
    init_db,
    link_client_to_master,
    link_existing_client_to_master,
    save_order_rating,
    update_client,
    update_client_consent,
)
from src.keyboards import consent_kb, delete_confirm_kb, share_contact_kb, skip_kb
from src.notifications import contact_keyboard, order_action_keyboard, review_keyboard
from src.states import ClientDeletion, ClientRegistration
from src.utils import format_phone, normalize_phone, parse_date

master_bot: Bot | None = None

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

router = Router()

MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def client_miniapp_entry_kb() -> InlineKeyboardMarkup:
    """Open client Mini App."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=CLIENT_MINIAPP_URL))],
    ])


def build_miniapp_entry_text(client, masters: list[dict]) -> str:
    """Build simplified client bot entry text."""
    if not masters:
        return f"Привет, {client.name}!\n\nУ вас пока нет специалистов"

    lines = [f"Привет, {client.name}!", "", "Ваши специалисты:"]
    for item in masters:
        name = item.get("name") or item.get("master_name") or "Специалист"
        sphere = item.get("sphere")
        balance = item.get("bonus_balance") or 0
        suffix = f" · {sphere}" if sphere else ""
        lines.append(f"— {name}{suffix} · {balance} бонусов")
    return "\n".join(lines)


async def send_miniapp_entry(bot: Bot, chat_id: int, client) -> None:
    """Send Mini App entry message with connected specialists."""
    masters = await get_all_client_masters_by_tg_id(client.tg_id)
    await bot.send_message(
        chat_id,
        build_miniapp_entry_text(client, masters),
        reply_markup=client_miniapp_entry_kb(),
    )


async def remove_reply_keyboard(bot: Bot, chat_id: int) -> None:
    """Silently remove old reply keyboard if it was set previously."""
    try:
        msg = await bot.send_message(chat_id, "\u2060", reply_markup=ReplyKeyboardRemove())
        try:
            await bot.delete_message(chat_id, msg.message_id)
        except TelegramBadRequest:
            pass
    except TelegramBadRequest:
        pass


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /start and invite links."""
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    tg_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    invite_token = args[1].strip() if len(args) >= 2 else None
    if invite_token and invite_token.startswith("invite_"):
        invite_token = invite_token[7:]

    client = await get_client_by_tg_id(tg_id)

    if invite_token:
        master = await get_master_by_invite_token(invite_token)
        if not master:
            await bot.send_message(
                message.chat.id,
                "Ссылка недействительна.\n\n"
                "Попросите специалиста отправить вам актуальную ссылку.",
            )
            return

        if not client:
            await state.update_data(master_id=master.id)
            await bot.send_message(
                message.chat.id,
                "Привет!\n\n"
                "Для регистрации нам нужно ваше согласие на обработку персональных данных.\n\n"
                "Мы собираем: имя, телефон, дату рождения (опционально).\n"
                "Данные используются только для записи и бонусной программы.\n\n"
                '<a href="https://crmfit.ru/privacy">Политика конфиденциальности</a>',
                reply_markup=consent_kb(),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            await state.set_state(ClientRegistration.consent)
            return

        existing_link = await get_master_client(master.id, client.id)
        if existing_link:
            await state.clear()
            await bot.send_message(message.chat.id, f"Вы уже подключены к специалисту {master.name}")
            await send_miniapp_entry(bot, message.chat.id, client)
            return

        await link_existing_client_to_master(client.id, master.id)
        await accrue_welcome_bonus(master.id, client.id)
        await state.clear()
        await bot.send_message(message.chat.id, f"Вы подключились к специалисту {master.name}!")
        await send_miniapp_entry(bot, message.chat.id, client)
        return

    if not client:
        await bot.send_message(
            message.chat.id,
            "Привет!\n\n"
            "Для регистрации нужна ссылка от вашего специалиста.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.clear()
    await send_miniapp_entry(bot, message.chat.id, client)


@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /support command."""
    await state.clear()
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    client = await get_client_by_tg_id(message.from_user.id)
    if not client:
        await bot.send_message(message.chat.id, "Вы не зарегистрированы. Перейдите по ссылке от специалиста.")
        return

    await bot.send_message(
        message.chat.id,
        "Поддержка\n\n"
        "Telegram: @pastushenko12\n"
        "E-mail: copypast.pe@gmail.com",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Command("delete_me"))
async def cmd_delete_me(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /delete_me command."""
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    client = await get_client_by_tg_id(message.from_user.id)
    if not client:
        await bot.send_message(message.chat.id, "Вы не зарегистрированы в системе.")
        return

    await state.set_state(ClientDeletion.confirm)
    await state.update_data(client_id=client.id)
    await bot.send_message(
        message.chat.id,
        "Удаление данных\n\n"
        "Будут удалены: имя, телефон, дата рождения и привязка к Telegram.\n"
        "История заказов сохранится анонимно.\n\n"
        "Это действие необратимо.",
        reply_markup=delete_confirm_kb(),
    )


@router.callback_query(F.data == "delete:confirm")
async def delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Confirm data deletion."""
    client = await get_client_by_tg_id(callback.from_user.id)
    if client:
        await anonymize_client(client.id)
    await state.clear()
    await callback.message.edit_text("Ваши данные удалены.\n\nСпасибо, что были с нами!")
    await callback.answer()


@router.callback_query(F.data == "delete:cancel")
async def delete_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel data deletion."""
    await state.clear()
    await callback.message.edit_text("Удаление отменено.")
    await callback.answer()


@router.callback_query(ClientRegistration.consent, F.data == "consent:agree")
async def consent_agree(callback: CallbackQuery, state: FSMContext) -> None:
    """User agreed to privacy policy."""
    await state.update_data(consent_given_at=datetime.now().isoformat())
    await callback.message.edit_text("Спасибо за согласие!\n\nКак вас зовут?")
    await state.set_state(ClientRegistration.name)
    await callback.answer()


@router.callback_query(ClientRegistration.consent, F.data == "consent:decline")
async def consent_decline(callback: CallbackQuery, state: FSMContext) -> None:
    """User declined privacy policy."""
    await state.clear()
    await callback.message.edit_text(
        "Вы отказались от обработки данных.\n\n"
        "Без согласия регистрация невозможна. Если передумаете, перейдите по ссылке от специалиста снова."
    )
    await callback.answer()


@router.message(ClientRegistration.name)
async def reg_name(message: Message, state: FSMContext) -> None:
    """Save client name."""
    name = message.text.strip()[:100]
    await state.update_data(name=name)
    await message.answer(
        f"Приятно познакомиться, {name}!\n\n"
        "Поделитесь номером телефона. Это нужно для связи со специалистом.",
        reply_markup=share_contact_kb(),
    )
    await state.set_state(ClientRegistration.phone)


@router.message(ClientRegistration.phone, F.contact)
async def reg_phone_contact(message: Message, state: FSMContext) -> None:
    """Save client phone from contact."""
    phone = normalize_phone(message.contact.phone_number) or format_phone(message.contact.phone_number)
    await state.update_data(phone=phone)
    await message.answer(
        "Когда у вас день рождения?\n"
        "(в формате ДД.ММ или ДД.ММ.ГГГГ)",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer("Или пропустите этот шаг:", reply_markup=skip_kb())
    await state.set_state(ClientRegistration.birthday)


@router.message(ClientRegistration.phone)
async def reg_phone_text(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save client phone from text."""
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    phone = normalize_phone(message.text.strip())
    if not phone:
        await bot.send_message(
            chat_id=message.chat.id,
            text="Неверный формат номера. Введите с кодом страны: +7..., +995..., +380...",
        )
        return

    await state.update_data(phone=phone)
    await message.answer(
        "Когда у вас день рождения?\n"
        "(в формате ДД.ММ или ДД.ММ.ГГГГ)",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer("Или пропустите этот шаг:", reply_markup=skip_kb())
    await state.set_state(ClientRegistration.birthday)


@router.message(ClientRegistration.birthday)
async def reg_birthday(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save birthday and complete registration."""
    birthday = parse_date(message.text)
    await state.update_data(birthday=birthday.isoformat() if birthday else None)
    await complete_registration(message, state, bot)


@router.callback_query(ClientRegistration.birthday, F.data == "skip")
async def reg_birthday_skip(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Skip birthday and complete registration."""
    await state.update_data(birthday=None)
    await complete_registration(callback.message, state, bot, edit=True)
    await callback.answer()


async def complete_registration(message: Message, state: FSMContext, bot: Bot, edit: bool = False) -> None:
    """Complete client registration and show Mini App entry."""
    data = await state.get_data()
    tg_id = message.chat.id
    master_id = data["master_id"]

    phone = data.get("phone")
    existing_client = await get_client_by_phone(phone) if phone else None
    if existing_client:
        await update_client(existing_client.id, tg_id=tg_id, name=data["name"])
        if data.get("birthday"):
            await update_client(existing_client.id, birthday=data["birthday"])
        client = existing_client
        client.tg_id = tg_id
        client.name = data["name"]
    else:
        client = await create_client(
            tg_id=tg_id,
            name=data["name"],
            phone=phone,
            birthday=data.get("birthday"),
            registered_via=master_id,
        )

    if data.get("consent_given_at"):
        await update_client_consent(client.id, data["consent_given_at"])

    await link_client_to_master(master_id, client.id)
    master = await get_master_by_id(master_id)
    await accrue_welcome_bonus(master_id, client.id)
    await state.clear()

    success_text = "Регистрация завершена!"
    if edit:
        await message.edit_text(success_text)
        await remove_reply_keyboard(bot, message.chat.id)
    else:
        await message.answer(success_text, reply_markup=ReplyKeyboardRemove())

    if master:
        await bot.send_message(message.chat.id, f"Вы подключились к специалисту {master.name}.")
    await send_miniapp_entry(bot, message.chat.id, client)


@router.callback_query(lambda c: c.data and c.data.startswith("feedback:"))
async def handle_feedback_rating(callback: CallbackQuery) -> None:
    """Handle client rating response from post-order feedback."""
    global master_bot

    try:
        _, order_id_raw, rating_raw = (callback.data or "").split(":")
        order_id = int(order_id_raw)
        rating = int(rating_raw)
    except (ValueError, AttributeError):
        await callback.answer()
        return

    if rating < 1 or rating > 5:
        await callback.answer()
        return

    await save_order_rating(order_id, rating)
    try:
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    order = await get_order_by_id_for_feedback(order_id)

    if rating == 5:
        if callback.message:
            await callback.message.answer(
                "Большое спасибо! Оставьте, пожалуйста, отзыв — это поможет специалисту.",
                reply_markup=review_keyboard(order_id, master_id=order.get("master_id")),
            )
    elif rating == 4:
        if callback.message:
            await callback.message.answer("Расскажите, что можно улучшить? Это поможет стать лучше.")

        if order and order.get("master_tg_id") and master_bot:
            client_name = order.get("client_name") or "Клиент"
            try:
                await master_bot.send_message(
                    order["master_tg_id"],
                    f"ℹ️ {client_name} оценил визит на 4.\nЗаказ #{order_id}",
                )
            except Exception as e:
                logger.warning("Failed to notify master for rating 4, order %s: %s", order_id, e)
    else:
        if callback.message:
            await callback.message.answer("Мы свяжемся с вами в ближайшее время.")

        if order and order.get("master_tg_id") and master_bot:
            client_name = order.get("client_name") or "Клиент"
            try:
                await master_bot.send_message(
                    order["master_tg_id"],
                    f"⚠️ {client_name} недоволен!\n"
                    f"Оценка: {rating} из 5\n"
                    f"Заказ #{order_id}\n\n"
                    "Свяжитесь с клиентом.",
                )
            except Exception as e:
                logger.warning("Failed to alert master for rating %s, order %s: %s", rating, order_id, e)

    await callback.answer("Спасибо за оценку!")


@router.callback_query(F.data.startswith("confirm_order:"))
async def handle_order_confirmation(callback: CallbackQuery) -> None:
    """Handle order confirmation from 24h reminder."""
    global master_bot

    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Запись больше не активна", show_alert=True)
        return

    order = await get_order_notification_context(order_id, client_tg_id=callback.from_user.id)
    if not order:
        await callback.answer("Запись больше не активна", show_alert=True)
        return

    if order.get("client_confirmed"):
        await callback.answer("Запись уже подтверждена", show_alert=True)
        return

    if order.get("status") not in ("new", "confirmed"):
        await callback.answer("Запись больше не активна", show_alert=True)
        return

    await confirm_order_by_client(order_id, order["client_id"])

    scheduled_at = datetime.fromisoformat(order["scheduled_at"])
    date_str = f"{scheduled_at.day} {MONTHS_RU[scheduled_at.month]}"
    time_str = scheduled_at.strftime("%H:%M")
    services = order.get("services") or "—"
    master_name = order.get("master_name") or "специалист"
    address = (order.get("address") or "").strip()

    new_text = (
        "Вы подтвердили запись:\n\n"
        f"{services}\n"
        f"{date_str}, {time_str} — {master_name}"
    )
    if address:
        new_text += f"\n{address}"
    new_text += "\n\nЖдём вас!"

    if callback.message:
        await callback.message.edit_text(
            text=new_text,
            reply_markup=order_action_keyboard(order_id, master_id=order.get("master_id")),
        )

    if master_bot and order.get("master_tg_id"):
        master_text = (
            "Клиент подтвердил запись:\n\n"
            f"{order.get('client_name') or 'Клиент'}\n"
            f"{services}\n"
            f"{date_str}, {time_str}"
        )
        await master_bot.send_message(chat_id=order["master_tg_id"], text=master_text)

    await callback.answer("Запись подтверждена")


@router.callback_query(F.data.startswith("contact_order:"))
async def handle_contact_order(callback: CallbackQuery) -> None:
    """Show specialist contacts for an order notification."""
    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Запись больше не активна", show_alert=True)
        return

    order = await get_order_notification_context(order_id, client_tg_id=callback.from_user.id)
    if not order:
        await callback.answer("Запись больше не активна", show_alert=True)
        return

    phone = (order.get("master_phone") or "").strip()
    telegram = (order.get("master_telegram") or "").strip()
    contacts = (order.get("master_contacts") or "").strip()

    lines = [order.get("master_name") or "Специалист", ""]
    lines.append(f"Телефон: {phone or '—'}")
    lines.append(f"Telegram: {telegram or '—'}")
    if contacts and contacts not in {phone, telegram}:
        lines.extend(["", contacts])

    if callback.message:
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=contact_keyboard(
                phone=phone,
                telegram=telegram,
                master_id=order.get("master_id"),
            ),
        )
    await callback.answer()


def setup_dispatcher() -> Dispatcher:
    """Create and configure dispatcher."""
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    return dp


async def main() -> None:
    """Main entry point."""
    global master_bot
    from aiogram.types import BotCommand

    await init_db()
    logger.info("Database initialized")

    bot = Bot(token=CLIENT_BOT_TOKEN)
    master_bot = Bot(token=MASTER_BOT_TOKEN)

    await bot.set_my_commands([
        BotCommand(command="start", description="Начать"),
        BotCommand(command="support", description="Поддержка"),
        BotCommand(command="delete_me", description="Удалить мои данные"),
    ])
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Открыть",
            web_app=WebAppInfo(url=CLIENT_MINIAPP_URL),
        )
    )

    from src.scheduler import setup_scheduler, start_scheduler
    setup_scheduler(bot, master_bot=master_bot)
    start_scheduler()
    logger.info("Scheduler started")

    dp = setup_dispatcher()
    logger.info("Starting client bot...")
    try:
        await dp.start_polling(bot)
    finally:
        from src.scheduler import stop_scheduler
        stop_scheduler()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
