"""Master reports endpoint."""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_current_master
from src.database import get_daily_revenue, get_reports
from src.models import Master

router = APIRouter(tags=["master"])

MONTH_NAMES = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]


def _resolve_period(
    period: Optional[str],
    date_from: Optional[date],
    date_to: Optional[date],
) -> tuple[date, date, str]:
    """Return (date_from, date_to, label). Raises HTTPException on bad input.

    If both date_from and date_to are provided, period param is ignored.
    Both must be supplied together; providing only one raises HTTP 400.
    """
    today = date.today()

    if (date_from is None) != (date_to is None):
        raise HTTPException(400, "Provide both date_from and date_to, or neither")

    if date_from and date_to:
        if date_to < date_from:
            raise HTTPException(400, "date_to must be >= date_from")
        if (date_to - date_from).days > 365:
            raise HTTPException(400, "Period cannot exceed 365 days")
        label = f"{date_from.strftime('%d.%m.%Y')} – {date_to.strftime('%d.%m.%Y')}"
        return date_from, date_to, label

    if period == "today":
        return today, today, "Сегодня"
    if period == "week":
        d_from = today - timedelta(days=today.weekday())  # Monday
        return d_from, today, "Эта неделя"
    # default: month
    d_from = today.replace(day=1)
    label = f"{MONTH_NAMES[today.month]} {today.year}"
    return d_from, today, label


@router.get("/master/reports")
async def get_master_reports(
    period: Optional[str] = Query(None, pattern="^(today|week|month)$"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    master: Master = Depends(get_current_master),
):
    """Get KPI + chart data for a period."""
    d_from, d_to, label = _resolve_period(period, date_from, date_to)

    kpi_raw = await get_reports(master.id, d_from, d_to)
    chart = await get_daily_revenue(master.id, d_from, d_to)

    return {
        "period": {
            "from": d_from.isoformat(),
            "to": d_to.isoformat(),
            "label": label,
        },
        "kpi": {
            "revenue": kpi_raw["revenue"],
            "order_count": kpi_raw["order_count"],
            "new_clients": kpi_raw["new_clients"],
            "repeat_clients": kpi_raw["repeat_clients"],
            "avg_check": kpi_raw["avg_check"],
            "total_clients": kpi_raw["total_clients"],
        },
        "top_services": kpi_raw.get("top_services", [])[:5],
        "chart_data": chart,
    }
