"""Master bot - for service providers to manage clients, orders, and marketing."""

import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import MASTER_BOT_TOKEN, CLIENT_BOT_USERNAME, LOG_LEVEL
from src.states import MasterRegistration
from src.keyboards import master_home_kb, skip_kb
from src.database import (
    init_db,
    get_master_by_tg_id,
    create_master,
    get_today_orders_for_master,
)
from src.utils import generate_invite_token

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
router = Router()


async def show_home(message: Message, master) -> None:
    """Display home screen for master."""
    today = datetime.now().strftime("%d.%m.%Y")
    orders = await get_today_orders_for_master(master.id)

    # Build orders text
    if orders:
        orders_text = "\n".join(
            f"• {o['scheduled_at'][:5] if o['scheduled_at'] else '—'} — {o['client_name']}, {o['address'] or 'адрес не указан'}"
            for o in orders
        )
    else:
        orders_text = "• Нет записей на сегодня"

    text = (
        f"👋 Привет, {master.name}!\n\n"
        f"📅 Сегодня, {today}:\n"
        f"{orders_text}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔗 Ссылка для клиентов:\n"
        f"t.me/{CLIENT_BOT_USERNAME}?start={master.invite_token}"
    )

    await message.answer(text, reply_markup=master_home_kb())


# =============================================================================
# Start command and registration
# =============================================================================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Handle /start command - check registration or start onboarding."""
    tg_id = message.from_user.id

    # Check if master already registered
    master = await get_master_by_tg_id(tg_id)
    if master:
        await state.clear()
        await show_home(message, master)
        return

    # Start registration
    await message.answer(
        "👋 Добро пожаловать в Master CRM Bot!\n\n"
        "Давайте настроим ваш профиль.\n\n"
        "📝 Введите ваше имя или псевдоним:"
    )
    await state.set_state(MasterRegistration.name)


@router.message(Command("home"))
async def cmd_home(message: Message, state: FSMContext) -> None:
    """Handle /home command - return to home screen."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    if not master:
        await message.answer("Вы ещё не зарегистрированы. Отправьте /start")
        return

    await state.clear()
    await show_home(message, master)


# =============================================================================
# Registration FSM handlers
# =============================================================================

@router.message(MasterRegistration.name)
async def reg_name(message: Message, state: FSMContext) -> None:
    """Step 1: Save name and ask for sphere."""
    name = message.text.strip()[:100]  # Limit to 100 chars
    await state.update_data(name=name)

    await message.answer(
        f"Отлично, {name}!\n\n"
        "🔧 Укажите вашу сферу деятельности:\n"
        "(например: клининг, сантехника, электрика, маникюр)",
        reply_markup=skip_kb()
    )
    await state.set_state(MasterRegistration.sphere)


@router.message(MasterRegistration.sphere)
async def reg_sphere(message: Message, state: FSMContext) -> None:
    """Step 2: Save sphere and ask for contacts."""
    sphere = message.text.strip()[:200]
    await state.update_data(sphere=sphere)

    await message.answer(
        "📞 Введите контакты для клиентов:\n"
        "(телефон, мессенджеры, email)",
        reply_markup=skip_kb()
    )
    await state.set_state(MasterRegistration.contacts)


@router.callback_query(MasterRegistration.sphere, F.data == "skip")
async def reg_sphere_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 2: Skip sphere."""
    await state.update_data(sphere=None)
    await callback.message.edit_text(
        "📞 Введите контакты для клиентов:\n"
        "(телефон, мессенджеры, email)"
    )
    await callback.message.answer("", reply_markup=skip_kb())
    await state.set_state(MasterRegistration.contacts)
    await callback.answer()


@router.message(MasterRegistration.contacts)
async def reg_contacts(message: Message, state: FSMContext) -> None:
    """Step 3: Save contacts and ask for socials."""
    contacts = message.text.strip()[:500]
    await state.update_data(contacts=contacts)

    await message.answer(
        "🔗 Укажите ссылки на соцсети и каналы:\n"
        "(Instagram, Telegram-канал, VK и т.д.)",
        reply_markup=skip_kb()
    )
    await state.set_state(MasterRegistration.socials)


@router.callback_query(MasterRegistration.contacts, F.data == "skip")
async def reg_contacts_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 3: Skip contacts."""
    await state.update_data(contacts=None)
    await callback.message.edit_text(
        "🔗 Укажите ссылки на соцсети и каналы:\n"
        "(Instagram, Telegram-канал, VK и т.д.)"
    )
    await callback.message.answer("", reply_markup=skip_kb())
    await state.set_state(MasterRegistration.socials)
    await callback.answer()


@router.message(MasterRegistration.socials)
async def reg_socials(message: Message, state: FSMContext) -> None:
    """Step 4: Save socials and ask for work hours."""
    socials = message.text.strip()[:500]
    await state.update_data(socials=socials)

    await message.answer(
        "🕐 Укажите режим работы:\n"
        "(например: пн-пт 9:00-19:00, сб 10:00-16:00)",
        reply_markup=skip_kb()
    )
    await state.set_state(MasterRegistration.work_hours)


@router.callback_query(MasterRegistration.socials, F.data == "skip")
async def reg_socials_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 4: Skip socials."""
    await state.update_data(socials=None)
    await callback.message.edit_text(
        "🕐 Укажите режим работы:\n"
        "(например: пн-пт 9:00-19:00, сб 10:00-16:00)"
    )
    await callback.message.answer("", reply_markup=skip_kb())
    await state.set_state(MasterRegistration.work_hours)
    await callback.answer()


@router.message(MasterRegistration.work_hours)
async def reg_work_hours(message: Message, state: FSMContext) -> None:
    """Step 5: Save work hours and complete registration."""
    work_hours = message.text.strip()[:200]
    await state.update_data(work_hours=work_hours)
    await complete_registration(message, state)


@router.callback_query(MasterRegistration.work_hours, F.data == "skip")
async def reg_work_hours_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 5: Skip work hours."""
    await state.update_data(work_hours=None)
    await complete_registration(callback.message, state, edit=True)
    await callback.answer()


async def complete_registration(message: Message, state: FSMContext, edit: bool = False) -> None:
    """Complete master registration and show home."""
    data = await state.get_data()
    tg_id = message.chat.id

    # Generate invite token
    invite_token = generate_invite_token()

    # Create master in database
    master = await create_master(
        tg_id=tg_id,
        name=data["name"],
        invite_token=invite_token,
        sphere=data.get("sphere"),
        contacts=data.get("contacts"),
        socials=data.get("socials"),
        work_hours=data.get("work_hours"),
    )

    await state.clear()

    success_text = (
        "✅ Регистрация завершена!\n\n"
        f"Ваша ссылка для приглашения клиентов:\n"
        f"t.me/{CLIENT_BOT_USERNAME}?start={invite_token}\n\n"
        "Отправьте её клиентам, чтобы они могли зарегистрироваться."
    )

    if edit:
        await message.edit_text(success_text)
    else:
        await message.answer(success_text)

    await show_home(message, master)


# =============================================================================
# Callback query handlers for menu (placeholders)
# =============================================================================

@router.callback_query(F.data == "orders")
async def cb_orders(callback: CallbackQuery) -> None:
    """Handle Orders button."""
    await callback.answer("Раздел 'Заказы' будет доступен в следующей версии")


@router.callback_query(F.data == "clients")
async def cb_clients(callback: CallbackQuery) -> None:
    """Handle Clients button."""
    await callback.answer("Раздел 'Клиенты' будет доступен в следующей версии")


@router.callback_query(F.data == "marketing")
async def cb_marketing(callback: CallbackQuery) -> None:
    """Handle Marketing button."""
    await callback.answer("Раздел 'Маркетинг' будет доступен в следующей версии")


@router.callback_query(F.data == "reports")
async def cb_reports(callback: CallbackQuery) -> None:
    """Handle Reports button."""
    await callback.answer("Раздел 'Отчёты' будет доступен в следующей версии")


@router.callback_query(F.data == "settings")
async def cb_settings(callback: CallbackQuery) -> None:
    """Handle Settings button."""
    await callback.answer("Раздел 'Настройки' будет доступен в следующей версии")


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
    bot = Bot(token=MASTER_BOT_TOKEN)
    dp = setup_dispatcher()

    logger.info("Starting master bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
