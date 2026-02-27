"""Client bot - for clients to view bonuses, history, and make requests."""

import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import CLIENT_BOT_TOKEN, LOG_LEVEL
from src.states import ClientRegistration
from src.keyboards import client_home_kb, skip_kb, share_contact_kb
from src.database import (
    init_db,
    get_master_by_invite_token,
    get_client_by_tg_id,
    get_client_by_phone,
    create_client,
    update_client,
    link_client_to_master,
    get_master_client,
    get_master_by_tg_id,
)
from src.utils import format_phone, parse_date

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
router = Router()


async def show_home(message: Message, client, master, master_client) -> None:
    """Display home screen for client."""
    text = (
        f"👋 Привет, {client.name}!\n\n"
        f"Ваш мастер: {master.name}\n"
        f"💰 Бонусов: {master_client.bonus_balance} ₽"
    )

    await message.answer(text, reply_markup=client_home_kb())


# =============================================================================
# Start command and registration
# =============================================================================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Handle /start command - check invite token or show message."""
    tg_id = message.from_user.id

    # Check if client already registered
    client = await get_client_by_tg_id(tg_id)
    if client and client.registered_via:
        await state.clear()
        # Get master info for home screen
        from src.database import get_connection
        conn = await get_connection()
        try:
            cursor = await conn.execute(
                "SELECT * FROM masters WHERE id = ?",
                (client.registered_via,)
            )
            master_row = await cursor.fetchone()
            if master_row:
                from src.models import Master
                master = Master(
                    id=master_row["id"],
                    tg_id=master_row["tg_id"],
                    name=master_row["name"],
                    invite_token=master_row["invite_token"],
                )
                master_client = await get_master_client(master.id, client.id)
                await show_home(message, client, master, master_client)
                return
        finally:
            await conn.close()

    # Extract invite token from start parameter
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "👋 Добро пожаловать!\n\n"
            "Для регистрации нужна ссылка от вашего мастера.\n"
            "Попросите мастера отправить вам персональную ссылку."
        )
        return

    invite_token = args[1].strip()

    # Find master by invite token
    master = await get_master_by_invite_token(invite_token)
    if not master:
        await message.answer(
            "❌ Ссылка недействительна.\n\n"
            "Попросите мастера отправить вам актуальную ссылку."
        )
        return

    # Store master_id in state for registration
    await state.update_data(master_id=master.id)

    await message.answer(
        f"👋 Привет! Вы переходите к мастеру: {master.name}\n\n"
        "Давайте познакомимся.\n\n"
        "📝 Как вас зовут?"
    )
    await state.set_state(ClientRegistration.name)


@router.message(Command("home"))
async def cmd_home(message: Message, state: FSMContext) -> None:
    """Handle /home command - return to home screen."""
    tg_id = message.from_user.id
    client = await get_client_by_tg_id(tg_id)

    if not client or not client.registered_via:
        await message.answer("Вы ещё не зарегистрированы. Перейдите по ссылке от мастера.")
        return

    await state.clear()

    # Get master info
    from src.database import get_connection
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM masters WHERE id = ?",
            (client.registered_via,)
        )
        master_row = await cursor.fetchone()
        if master_row:
            from src.models import Master
            master = Master(
                id=master_row["id"],
                tg_id=master_row["tg_id"],
                name=master_row["name"],
                invite_token=master_row["invite_token"],
            )
            master_client = await get_master_client(master.id, client.id)
            await show_home(message, client, master, master_client)
    finally:
        await conn.close()


# =============================================================================
# Registration FSM handlers
# =============================================================================

@router.message(ClientRegistration.name)
async def reg_name(message: Message, state: FSMContext) -> None:
    """Step 1: Save name and ask for phone."""
    name = message.text.strip()[:100]
    await state.update_data(name=name)

    await message.answer(
        f"Приятно познакомиться, {name}!\n\n"
        "📱 Поделитесь своим номером телефона.\n"
        "Это нужно для связи с мастером.",
        reply_markup=share_contact_kb()
    )
    await state.set_state(ClientRegistration.phone)


@router.message(ClientRegistration.phone, F.contact)
async def reg_phone_contact(message: Message, state: FSMContext) -> None:
    """Step 2: Save phone from contact and ask for birthday."""
    phone = format_phone(message.contact.phone_number)
    await state.update_data(phone=phone)

    await message.answer(
        "🎂 Когда у вас день рождения?\n"
        "(в формате ДД.ММ или ДД.ММ.ГГГГ)\n\n"
        "Мастер сможет поздравить вас и начислить бонусы!",
        reply_markup=ReplyKeyboardRemove()
    )
    # Also send skip keyboard
    await message.answer("Или пропустите этот шаг:", reply_markup=skip_kb())
    await state.set_state(ClientRegistration.birthday)


@router.message(ClientRegistration.phone)
async def reg_phone_text(message: Message, state: FSMContext) -> None:
    """Step 2: Save phone from text and ask for birthday."""
    phone = format_phone(message.text.strip())
    await state.update_data(phone=phone)

    await message.answer(
        "🎂 Когда у вас день рождения?\n"
        "(в формате ДД.ММ или ДД.ММ.ГГГГ)\n\n"
        "Мастер сможет поздравить вас и начислить бонусы!",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer("Или пропустите этот шаг:", reply_markup=skip_kb())
    await state.set_state(ClientRegistration.birthday)


@router.message(ClientRegistration.birthday)
async def reg_birthday(message: Message, state: FSMContext) -> None:
    """Step 3: Save birthday and complete registration."""
    birthday = parse_date(message.text)
    if birthday:
        await state.update_data(birthday=birthday.isoformat())
    else:
        await state.update_data(birthday=None)

    await complete_registration(message, state)


@router.callback_query(ClientRegistration.birthday, F.data == "skip")
async def reg_birthday_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 3: Skip birthday."""
    await state.update_data(birthday=None)
    await complete_registration(callback.message, state, edit=True)
    await callback.answer()


async def complete_registration(message: Message, state: FSMContext, edit: bool = False) -> None:
    """Complete client registration and show home."""
    data = await state.get_data()
    tg_id = message.chat.id
    master_id = data["master_id"]

    # Check if client exists by phone (added manually by master)
    phone = data.get("phone")
    existing_client = None
    if phone:
        existing_client = await get_client_by_phone(phone)

    if existing_client:
        # Link existing client record to Telegram
        await update_client(existing_client.id, tg_id=tg_id, name=data["name"])
        if data.get("birthday"):
            await update_client(existing_client.id, birthday=data["birthday"])
        client = existing_client
        client.tg_id = tg_id
        client.name = data["name"]
    else:
        # Create new client
        client = await create_client(
            tg_id=tg_id,
            name=data["name"],
            phone=phone,
            birthday=data.get("birthday"),
            registered_via=master_id,
        )

    # Link client to master
    master_client = await link_client_to_master(master_id, client.id)

    await state.clear()

    # Get master info for home screen
    master = await get_master_by_invite_token_by_id(master_id)

    success_text = "✅ Регистрация завершена!\n\nДобро пожаловать!"

    if edit:
        await message.edit_text(success_text)
    else:
        await message.answer(success_text)

    await show_home(message, client, master, master_client)


async def get_master_by_invite_token_by_id(master_id: int):
    """Get master by ID."""
    from src.database import get_connection
    from src.models import Master
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM masters WHERE id = ?",
            (master_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Master(
                id=row["id"],
                tg_id=row["tg_id"],
                name=row["name"],
                invite_token=row["invite_token"],
            )
        return None
    finally:
        await conn.close()


# =============================================================================
# Callback query handlers for menu (placeholders)
# =============================================================================

@router.callback_query(F.data == "bonuses")
async def cb_bonuses(callback: CallbackQuery) -> None:
    """Handle Bonuses button."""
    await callback.answer("Раздел 'Мои бонусы' будет доступен в следующей версии")


@router.callback_query(F.data == "history")
async def cb_history(callback: CallbackQuery) -> None:
    """Handle History button."""
    await callback.answer("Раздел 'История' будет доступен в следующей версии")


@router.callback_query(F.data == "promos")
async def cb_promos(callback: CallbackQuery) -> None:
    """Handle Promos button."""
    await callback.answer("Раздел 'Акции' будет доступен в следующей версии")


@router.callback_query(F.data == "order_request")
async def cb_order_request(callback: CallbackQuery) -> None:
    """Handle Order Request button."""
    await callback.answer("Раздел 'Заказать' будет доступен в следующей версии")


@router.callback_query(F.data == "question")
async def cb_question(callback: CallbackQuery) -> None:
    """Handle Question button."""
    await callback.answer("Раздел 'Вопрос' будет доступен в следующей версии")


@router.callback_query(F.data == "media")
async def cb_media(callback: CallbackQuery) -> None:
    """Handle Media button."""
    await callback.answer("Раздел 'Фото/видео' будет доступен в следующей версии")


@router.callback_query(F.data == "notifications")
async def cb_notifications(callback: CallbackQuery) -> None:
    """Handle Notifications button."""
    await callback.answer("Раздел 'Уведомления' будет доступен в следующей версии")


def setup_dispatcher() -> Dispatcher:
    """Create and configure dispatcher."""
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    return dp


async def main() -> None:
    """Main entry point."""
    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Create bot and dispatcher
    bot = Bot(token=CLIENT_BOT_TOKEN)
    dp = setup_dispatcher()

    logger.info("Starting client bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
