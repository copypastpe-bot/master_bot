"""Public landing page for master mini-site (/m/{invite_token})."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.config import CLIENT_BOT_USERNAME, MASTER_BOT_USERNAME
from src.database import get_landing_data

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(include_in_schema=False)

_CURRENCY_SYMBOLS = {"RUB": "₽", "EUR": "€", "USD": "$", "GBP": "£", "UAH": "₴", "KZT": "₸"}

_404_HTML = """<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Страница не найдена</title>
<style>body{font-family:system-ui,sans-serif;display:flex;align-items:center;
justify-content:center;min-height:100vh;margin:0;background:#f9fafb;color:#374151}
.box{text-align:center;padding:40px 24px}.box h1{font-size:48px;margin-bottom:8px;color:#d1d5db}
.box p{font-size:18px;margin-bottom:24px}.box a{color:#6c47ff;text-decoration:none}</style>
</head><body><div class="box"><h1>404</h1>
<p>Мастер не найден или ссылка устарела.</p></div></body></html>"""


def _fmt_date(s) -> str:
    if not s:
        return ""
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return str(s)[:10]


def _photo_url(file_id: str) -> str:
    if file_id.startswith("/"):
        return file_id
    return f"/api/public/photo/{file_id}"


def _initials(name: str) -> str:
    words = (name or "").split()
    return "".join(w[0].upper() for w in words[:2]) if words else "?"


@router.get("/m/{invite_token}", response_class=HTMLResponse)
async def landing_page(request: Request, invite_token: str):
    """Render public master landing page by invite token."""
    data = await get_landing_data(invite_token)
    if data is None:
        return HTMLResponse(content=_404_HTML, status_code=404)

    name = data.get("name") or ""
    sphere = data.get("sphere") or ""
    about = data.get("about") or ""
    contacts = data.get("contacts") or ""
    socials = data.get("socials") or ""
    work_hours = data.get("work_hours") or ""
    currency = data.get("currency") or "RUB"
    bonus_enabled = data.get("bonus_enabled", False)
    bonus_welcome = data.get("bonus_welcome") or 0
    avatar_file_id = data.get("avatar_file_id") or ""

    avatar_url = _photo_url(avatar_file_id) if avatar_file_id else None
    avatar_initials = _initials(name)
    currency_symbol = _CURRENCY_SYMBOLS.get(currency, currency)

    cta_link = f"https://t.me/{CLIENT_BOT_USERNAME}?start={invite_token}"
    master_bot_link = f"https://t.me/{MASTER_BOT_USERNAME}?start=from_landing"

    if bonus_enabled and bonus_welcome > 0:
        cta_text = f"Подписаться и получить {bonus_welcome} бонусов"
    else:
        cta_text = "Подписаться"

    portfolio = [
        {"id": item["id"], "url": _photo_url(item["file_id"])}
        for item in data.get("portfolio", [])
    ]

    services = data.get("services", [])

    reviews = []
    for r in data.get("reviews", []):
        reviews.append({
            "client_name": r.get("client_name") or "Клиент",
            "rating": int(r.get("rating") or 0),
            "text": r.get("text") or "",
            "created_at": _fmt_date(r.get("created_at")),
        })

    og_image = _photo_url(avatar_file_id) if avatar_file_id else None
    og_title = f"{name} — {sphere}" if sphere else name
    og_description = about or sphere or ""

    return templates.TemplateResponse("landing.html", {
        "request": request,
        "name": name,
        "sphere": sphere,
        "about": about,
        "contacts": contacts,
        "socials": socials,
        "work_hours": work_hours,
        "avatar_url": avatar_url,
        "avatar_initials": avatar_initials,
        "cta_link": cta_link,
        "cta_text": cta_text,
        "master_bot_link": master_bot_link,
        "portfolio": portfolio,
        "services": services,
        "reviews": reviews,
        "currency_symbol": currency_symbol,
        "og_title": og_title,
        "og_description": og_description,
        "og_image": og_image,
    })
