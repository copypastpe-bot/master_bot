"""Registration handlers for master onboarding."""

from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from src.config import CLIENT_BOT_USERNAME
from src.database import create_master, get_master_by_tg_id
from src.keyboards import skip_kb, timezone_kb, home_reply_kb
from src.states import MasterRegistration
from src.utils import generate_invite_token, get_timezone_display
from src.handlers.common import show_home

router = Router(name="registration")


# =============================================================================
# Registration FSM
# =============================================================================

@router.message(MasterRegistration.name)
async def reg_name(message: Message, state: FSMContext) -> None:
    """Step 1: Save name."""
    name = message.text.strip()[:100]
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
    """Step 2: Save sphere."""
    sphere = message.text.strip()[:200]
    await state.update_data(sphere=sphere)

    await message.answer(
        "🕐 Выберите ваш часовой пояс:\n"
        "(для отправки поздравлений клиентам)",
        reply_markup=timezone_kb(back_to=None)
    )
    await state.set_state(MasterRegistration.timezone)


@router.callback_query(MasterRegistration.sphere, F.data == "skip")
async def reg_sphere_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 2: Skip sphere."""
    await state.update_data(sphere=None)
    await callback.message.edit_text(
        "🕐 Выберите ваш часовой пояс:\n"
        "(для отправки поздравлений клиентам)"
    )
    await callback.message.answer("Выберите:", reply_markup=timezone_kb(back_to=None))
    await state.set_state(MasterRegistration.timezone)
    await callback.answer()


@router.callback_query(MasterRegistration.timezone, F.data.startswith("set_timezone:"))
async def reg_timezone(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 3: Save timezone."""
    tz_code = callback.data.split(":")[1]
    await state.update_data(timezone=tz_code)

    tz_display = get_timezone_display(tz_code)
    await callback.message.edit_text(f"✅ Часовой пояс: {tz_display}")

    await callback.message.answer(
        "📞 Введите контакты для клиентов:\n"
        "(телефон, мессенджеры, email)",
        reply_markup=skip_kb()
    )
    await state.set_state(MasterRegistration.contacts)
    await callback.answer()


@router.message(MasterRegistration.contacts)
async def reg_contacts(message: Message, state: FSMContext) -> None:
    """Step 4: Save contacts."""
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
    await callback.message.answer("Или пропустите:", reply_markup=skip_kb())
    await state.set_state(MasterRegistration.socials)
    await callback.answer()


@router.message(MasterRegistration.socials)
async def reg_socials(message: Message, state: FSMContext) -> None:
    """Step 4: Save socials."""
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
    await callback.message.answer("Или пропустите:", reply_markup=skip_kb())
    await state.set_state(MasterRegistration.work_hours)
    await callback.answer()


@router.message(MasterRegistration.work_hours)
async def reg_work_hours(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 5: Save work hours and complete."""
    work_hours = message.text.strip()[:200]
    await state.update_data(work_hours=work_hours)
    await complete_registration(message, state, bot)


@router.callback_query(MasterRegistration.work_hours, F.data == "skip")
async def reg_work_hours_skip(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Step 5: Skip work hours."""
    await state.update_data(work_hours=None)
    await complete_registration(callback.message, state, bot, edit=True)
    await callback.answer()


async def complete_registration(message: Message, state: FSMContext, bot: Bot, edit: bool = False) -> None:
    """Complete master registration."""
    data = await state.get_data()
    tg_id = message.chat.id

    invite_token = generate_invite_token()

    master = await create_master(
        tg_id=tg_id,
        name=data["name"],
        invite_token=invite_token,
        sphere=data.get("sphere"),
        contacts=data.get("contacts"),
        socials=data.get("socials"),
        work_hours=data.get("work_hours"),
        timezone=data.get("timezone", "Europe/Moscow"),
    )

    await state.clear()
    await state.update_data(current_screen="home")

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

    # Send reply keyboard
    await bot.send_message(message.chat.id, "🏠", reply_markup=home_reply_kb())
    await show_home(bot, master, message.chat.id)
