"""Common handlers: home screen, middleware, navigation."""

from aiogram import Bot, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, FSInputFile
from aiogram.fsm.context import FSMContext

from src.database import get_master_by_tg_id
from src.config import MINIAPP_URL

router = Router(name="common")

# --- DISABLED: moved to Mini App ---
# MONTHS_RU = [
#     "", "января", "февраля", "марта", "апреля", "мая", "июня",
#     "июля", "августа", "сентября", "октября", "ноября", "декабря"
# ]
#
# MONTHS_RU_NOM = [
#     "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
#     "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
# ]
# --- END DISABLED ---

# Stub constants kept for backward-compat with other handlers until they are migrated
MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]

MONTHS_RU_NOM = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]

# --- DISABLED: moved to Mini App ---
# class HomeButtonMiddleware(BaseMiddleware):
#     """Middleware to intercept Home button before any FSM handlers."""
#
#     async def __call__(
#         self,
#         handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
#         event: TelegramObject,
#         data: Dict[str, Any]
#     ) -> Any:
#         # Only process text messages with "Home" button
#         if isinstance(event, Message) and event.text and event.text == "🏠 Домой":
#             bot: Bot = data["bot"]
#             state: FSMContext = data["state"]
#             tg_id = event.from_user.id
#
#             master = await get_master_by_tg_id(tg_id)
#             if master:
#                 await state.clear()
#                 try:
#                     await event.delete()
#                 except TelegramBadRequest:
#                     pass
#                 await show_home(bot, master, event.chat.id, force_new=True)
#             else:
#                 # Not registered - show message
#                 await event.answer("Вы не зарегистрированы. Отправьте /start")
#             return  # Always stop propagation for "Home" button
#
#         return await handler(event, data)
# --- END DISABLED ---


# =============================================================================
# Home Screen
# =============================================================================

# --- DISABLED: moved to Mini App ---
# async def build_home_text(master) -> str:
#     """Build home screen text."""
#     today = date.today()
#     day = today.day
#     month = MONTHS_RU[today.month]
#
#     orders = await get_orders_today(master.id)
#
#     if orders:
#         def get_time(scheduled_at: str) -> str:
#             """Extract HH:MM from ISO datetime string."""
#             return scheduled_at[11:16] if len(scheduled_at) >= 16 else "—"
#
#         orders_text = "\n".join(
#             f"• {get_time(o.get('scheduled_at', ''))} — "
#             f"{o.get('client_name', 'Клиент')} | {o.get('address', 'адрес не указан')[:30]}"
#             for o in orders
#         )
#     else:
#         orders_text = "• Заказов на сегодня нет"
#
#     return (
#         f"👋 Привет, {master.name}!\n"
#         f"━━━━━━━━━━━━━━━\n"
#         f"📅 Сегодня, {day} {month}:\n\n"
#         f"{orders_text}\n"
#         f"━━━━━━━━━━━━━━━"
#     )
# --- END DISABLED ---


# --- DISABLED: moved to Mini App ---
# async def show_home(bot: Bot, master, chat_id: int, force_new: bool = False) -> int:
#     """Show or update home screen. Returns message_id.
#
#     Args:
#         force_new: If True, always send new message (delete old if exists)
#     """
#     text = await build_home_text(master)
#     keyboard = home_master_kb()
#
#     # Delete old message if force_new
#     if force_new and master.home_message_id:
#         try:
#             await bot.delete_message(chat_id=chat_id, message_id=master.home_message_id)
#         except TelegramBadRequest:
#             pass
#         # Send new message
#         msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
#         await save_master_home_message_id(master.id, msg.message_id)
#         return msg.message_id
#
#     # Try to edit existing message
#     if master.home_message_id:
#         try:
#             await bot.edit_message_text(
#                 chat_id=chat_id,
#                 message_id=master.home_message_id,
#                 text=text,
#                 reply_markup=keyboard
#             )
#             return master.home_message_id
#         except TelegramBadRequest as e:
#             # "message is not modified" - no need to send new message
#             if "message is not modified" in str(e):
#                 return master.home_message_id
#             # Otherwise message was deleted or not found - send new
#
#     # Send new message
#     msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
#     await save_master_home_message_id(master.id, msg.message_id)
#     return msg.message_id
# --- END DISABLED ---


# --- DISABLED: moved to Mini App ---
# async def edit_home_message(callback: CallbackQuery, text: str, keyboard) -> None:
#     """Edit the home message with new content."""
#     try:
#         await callback.message.edit_text(text=text, reply_markup=keyboard)
#     except TelegramBadRequest:
#         pass
# --- END DISABLED ---

# Stub functions kept for backward-compat with other handlers until they are migrated.
# These will be removed when all dependent handlers are updated.
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest


async def build_home_text(master) -> str:
    """Stub — original implementation disabled. Returns empty string."""
    return ""


async def show_home(bot: Bot, master, chat_id: int, force_new: bool = False) -> int:
    """Stub — original implementation disabled. Returns 0."""
    return 0


async def edit_home_message(callback: CallbackQuery, text: str, keyboard) -> None:
    """Stub — original implementation disabled. Does nothing."""
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard)
    except TelegramBadRequest:
        pass


# =============================================================================
# Start and Home Commands
# =============================================================================

BANNER_PATH = "assets/welcome_banner.png"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /start — show banner with Mini App button."""
    await state.clear()

    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    if master:
        caption = (
            f"Привет, {master.name}! 👋\n\n"
            "Открой приложение, чтобы продолжить работу."
        )
    else:
        caption = (
            "Привет! Помогу вести запись клиентов, напоминать им "
            "о визите и вести учёт финансов.\n\n"
            "Всё в Telegram — никаких лишних приложений."
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Открыть приложение →",
            web_app=WebAppInfo(url=MINIAPP_URL)
        )]
    ])

    await bot.send_photo(
        chat_id=message.chat.id,
        photo=FSInputFile(BANNER_PATH),
        caption=caption,
        reply_markup=keyboard,
    )


@router.message(Command("home"))
async def cmd_home(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /home — same as /start."""
    await state.clear()

    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    if master:
        caption = (
            f"Привет, {master.name}! 👋\n\n"
            "Открой приложение, чтобы продолжить работу."
        )
    else:
        caption = (
            "Привет! Помогу вести запись клиентов, напоминать им "
            "о визите и вести учёт финансов.\n\n"
            "Всё в Telegram — никаких лишних приложений."
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Открыть приложение →",
            web_app=WebAppInfo(url=MINIAPP_URL)
        )]
    ])

    await bot.send_photo(
        chat_id=message.chat.id,
        photo=FSInputFile(BANNER_PATH),
        caption=caption,
        reply_markup=keyboard,
    )


# =============================================================================
# Navigation: Home
# =============================================================================

# --- DISABLED: moved to Mini App ---
# @router.callback_query(F.data == "home")
# async def cb_home(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
#     """Return to home screen."""
#     tg_id = callback.from_user.id
#     master = await get_master_by_tg_id(tg_id)
#
#     if not master:
#         await callback.answer("Ошибка")
#         return
#
#     await state.update_data(current_screen="home")
#     text = await build_home_text(master)
#     await edit_home_message(callback, text, home_master_kb())
#     await callback.answer()
# --- END DISABLED ---


from aiogram import F


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    """Do nothing callback for non-interactive buttons."""
    await callback.answer()
