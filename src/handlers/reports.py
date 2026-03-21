"""Reports handlers: statistics and analytics."""

from datetime import date, datetime, timedelta

from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from src.database import (
    get_master_by_tg_id,
    get_reports,
    save_master_home_message_id,
)
from src.keyboards import reports_kb, report_period_cancel_kb
from src.states import ReportPeriodFSM
from src.utils import get_currency_symbol, parse_date
from src.handlers.common import edit_home_message, MONTHS_RU_NOM

router = Router(name="reports")


# =============================================================================
# Reports Section
# =============================================================================

@router.callback_query(F.data == "reports")
async def cb_reports(callback: CallbackQuery, state: FSMContext) -> None:
    """Show reports for current month."""
    await show_reports(callback, state, "month")


@router.callback_query(F.data == "reports:today")
async def cb_reports_today(callback: CallbackQuery, state: FSMContext) -> None:
    """Show reports for today."""
    await show_reports(callback, state, "today")


@router.callback_query(F.data == "reports:week")
async def cb_reports_week(callback: CallbackQuery, state: FSMContext) -> None:
    """Show reports for week."""
    await show_reports(callback, state, "week")


@router.callback_query(F.data == "reports:month")
async def cb_reports_month(callback: CallbackQuery, state: FSMContext) -> None:
    """Show reports for month."""
    await show_reports(callback, state, "month")


@router.callback_query(F.data == "reports:period")
async def cb_reports_period(callback: CallbackQuery, state: FSMContext) -> None:
    """Start custom period selection FSM."""
    await state.set_state(ReportPeriodFSM.date_from)
    text = (
        "📅 Произвольный период\n\n"
        "Введите дату начала периода\n"
        "(например: 01.03.2026):"
    )
    await edit_home_message(callback, text, report_period_cancel_kb())
    await callback.answer()


@router.message(ReportPeriodFSM.date_from)
async def fsm_report_date_from(message: Message, state: FSMContext) -> None:
    """Handle date_from input for custom period."""
    date_from = parse_date(message.text.strip())
    if not date_from:
        await message.answer(
            "❌ Неверный формат даты.\n"
            "Введите дату в формате ДД.ММ.ГГГГ\n"
            "(например: 01.03.2026):",
            reply_markup=report_period_cancel_kb()
        )
        return

    await state.update_data(report_date_from=date_from.isoformat())
    await state.set_state(ReportPeriodFSM.date_to)

    await message.answer(
        "Введите дату окончания периода\n"
        "(например: 31.03.2026):",
        reply_markup=report_period_cancel_kb()
    )


@router.message(ReportPeriodFSM.date_to)
async def fsm_report_date_to(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle date_to input for custom period."""
    date_to = parse_date(message.text.strip())
    if not date_to:
        await message.answer(
            "❌ Неверный формат даты.\n"
            "Введите дату в формате ДД.ММ.ГГГГ\n"
            "(например: 31.03.2026):",
            reply_markup=report_period_cancel_kb()
        )
        return

    data = await state.get_data()
    date_from = date.fromisoformat(data["report_date_from"])

    # Validate: date_to >= date_from
    if date_to < date_from:
        await message.answer(
            "❌ Дата окончания не может быть раньше даты начала.\n"
            "Введите корректную дату окончания:",
            reply_markup=report_period_cancel_kb()
        )
        return

    # Validate: period not more than 1 year
    if (date_to - date_from).days > 365:
        await message.answer(
            "❌ Период не может превышать 1 год.\n"
            "Введите дату окончания не более чем через год от начала:",
            reply_markup=report_period_cancel_kb()
        )
        return

    await state.clear()

    # Get master and show report
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)
    home_message_id = data.get("home_message_id")

    # Build report text inline since we can't use show_reports (no callback)
    report_data = await get_reports(master.id, date_from, date_to)

    # Format period text
    if date_from.year == date_to.year:
        period_text = f"{date_from.strftime('%d.%m')} — {date_to.strftime('%d.%m.%Y')}"
    else:
        period_text = f"{date_from.strftime('%d.%m.%Y')} — {date_to.strftime('%d.%m.%Y')}"

    # Build top services text (by popularity)
    top_services_text = ""
    if report_data["top_services"] and report_data["order_count"] > 0:
        lines = []
        for s in report_data["top_services"]:
            cnt = s["count"]
            if cnt == 1:
                times_word = "раз"
            elif 2 <= cnt <= 4:
                times_word = "раза"
            else:
                times_word = "раз"
            lines.append(f"- {s['name']} — {cnt} {times_word}")
        top_services_text = "\n".join(lines)

    # Build top orders text (by amount)
    top_orders_text = ""
    if report_data.get("top_orders") and report_data["order_count"] > 0:
        lines = []
        for o in report_data["top_orders"]:
            order_date = datetime.fromisoformat(o["date"]).strftime("%d.%m")
            lines.append(f"- {o['amount']:,} {curr} — {o['client_name']} ({order_date})".replace(",", " "))
        top_orders_text = "\n".join(lines)

    # Build report text
    if report_data["order_count"] == 0:
        text = (
            f"📊 Отчёты — {period_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"За этот период заказов нет.\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 Выручка: 0 {curr}\n"
            f"🛒 Заказов выполнено: 0\n"
            f"👥 Новых клиентов: {report_data['new_clients']}\n"
            f"🔄 Повторных клиентов: 0\n"
            f"🧾 Средний чек: 0 {curr}\n"
            f"📋 Всего клиентов в базе: {report_data['total_clients']}\n"
            f"━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            f"📊 Отчёты — {period_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 Выручка: {report_data['revenue']:,} {curr}\n"
            f"🛒 Заказов выполнено: {report_data['order_count']}\n"
            f"👥 Новых клиентов: {report_data['new_clients']}\n"
            f"🔄 Повторных клиентов: {report_data['repeat_clients']}\n"
            f"🧾 Средний чек: {report_data['avg_check']:,} {curr}\n"
            f"📋 Всего клиентов в базе: {report_data['total_clients']}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🏆 Топ услуг по популярности:\n"
            f"{top_services_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 Топ заказов по сумме:\n"
            f"{top_orders_text}\n"
            f"━━━━━━━━━━━━━━━"
        ).replace(",", " ")

    # Try to edit home message, fallback to send new
    if home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=home_message_id,
                text=text,
                reply_markup=reports_kb("custom")
            )
        except TelegramBadRequest:
            sent = await message.answer(text, reply_markup=reports_kb("custom"))
            await save_master_home_message_id(master.id, sent.message_id)
    else:
        sent = await message.answer(text, reply_markup=reports_kb("custom"))
        await save_master_home_message_id(master.id, sent.message_id)


async def show_reports(
    callback: CallbackQuery,
    state: FSMContext,
    period: str,
    custom_from: date = None,
    custom_to: date = None
) -> None:
    """Show reports for a period."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

    today = date.today()

    if period == "today":
        date_from = today
        date_to = today
        period_text = "Сегодня"
    elif period == "week":
        date_from = today - timedelta(days=6)  # today - 6 days = 7 days total
        date_to = today
        period_text = "Неделя"
    elif period == "custom" and custom_from and custom_to:
        date_from = custom_from
        date_to = custom_to
        # Format: 01.03 — 31.03.2026
        if date_from.year == date_to.year:
            period_text = f"{date_from.strftime('%d.%m')} — {date_to.strftime('%d.%m.%Y')}"
        else:
            period_text = f"{date_from.strftime('%d.%m.%Y')} — {date_to.strftime('%d.%m.%Y')}"
    else:  # month
        date_from = today.replace(day=1)
        date_to = today
        period_text = f"{MONTHS_RU_NOM[today.month]} {today.year}"

    await state.update_data(current_screen="reports")

    data = await get_reports(master.id, date_from, date_to)

    # Build top services text (by popularity - count only)
    top_services_text = ""
    if data["top_services"] and data["order_count"] > 0:
        lines = []
        for s in data["top_services"]:
            cnt = s["count"]
            if cnt == 1:
                times_word = "раз"
            elif 2 <= cnt <= 4:
                times_word = "раза"
            else:
                times_word = "раз"
            lines.append(f"- {s['name']} — {cnt} {times_word}")
        top_services_text = "\n".join(lines)

    # Build top orders text (by amount)
    top_orders_text = ""
    if data.get("top_orders") and data["order_count"] > 0:
        lines = []
        for o in data["top_orders"]:
            order_date = datetime.fromisoformat(o["date"]).strftime("%d.%m")
            lines.append(f"- {o['amount']:,} {curr} — {o['client_name']} ({order_date})".replace(",", " "))
        top_orders_text = "\n".join(lines)

    # Build the report text
    if data["order_count"] == 0:
        text = (
            f"📊 Отчёты — {period_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"За этот период заказов нет.\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 Выручка: 0 {curr}\n"
            f"🛒 Заказов выполнено: 0\n"
            f"👥 Новых клиентов: {data['new_clients']}\n"
            f"🔄 Повторных клиентов: 0\n"
            f"🧾 Средний чек: 0 {curr}\n"
            f"📋 Всего клиентов в базе: {data['total_clients']}\n"
            f"━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            f"📊 Отчёты — {period_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 Выручка: {data['revenue']:,} {curr}\n"
            f"🛒 Заказов выполнено: {data['order_count']}\n"
            f"👥 Новых клиентов: {data['new_clients']}\n"
            f"🔄 Повторных клиентов: {data['repeat_clients']}\n"
            f"🧾 Средний чек: {data['avg_check']:,} {curr}\n"
            f"📋 Всего клиентов в базе: {data['total_clients']}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🏆 Топ услуг по популярности:\n"
            f"{top_services_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 Топ заказов по сумме:\n"
            f"{top_orders_text}\n"
            f"━━━━━━━━━━━━━━━"
        ).replace(",", " ")

    await edit_home_message(callback, text, reports_kb(period))
    await callback.answer()
