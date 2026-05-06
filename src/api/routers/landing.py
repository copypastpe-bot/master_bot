"""Public landing page for master mini-site (/m/{invite_token})."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.config import CLIENT_BOT_USERNAME, MASTER_BOT_USERNAME
from src.database import get_landing_data, get_promo_public_data

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


def _absolute_url(request: Request, url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return str(request.base_url).rstrip("/") + url


def _is_dark_style(style: dict) -> bool:
    bg = (style.get("bg_color") or "#ffffff").lstrip("#")
    if len(bg) != 6:
        return False
    try:
        red = int(bg[0:2], 16) / 255
        green = int(bg[2:4], 16) / 255
        blue = int(bg[4:6], 16) / 255
    except ValueError:
        return False
    return (0.2126 * red + 0.7152 * green + 0.0722 * blue) < 0.3


def _style_with_defaults(style: dict | None) -> dict:
    data = dict(style or {})
    defaults = {
        "primary_color": "#2E7D32",
        "secondary_color": "#E8F5E9",
        "accent_color": "#1B5E20",
        "text_color": "#212121",
        "text_color_light": "#FFFFFF",
        "bg_color": "#FFFFFF",
        "badge_bg": "#2E7D32",
        "badge_text": "#FFFFFF",
        "button_bg": "#2E7D32",
        "button_text": "#FFFFFF",
        "card_bg": "#F1F8E9",
        "gradient": "linear-gradient(135deg, #2E7D32 0%, #4CAF50 100%)",
    }
    return {**defaults, **data}


@router.get("/m/{page_key}", response_class=HTMLResponse)
async def landing_page(request: Request, page_key: str):
    """Render public promo page by slug, or legacy master landing by invite token."""
    promo = await get_promo_public_data(page_key, increment_view=True)
    if promo is not None:
        style = _style_with_defaults(promo.get("style", {}).get("config"))
        photo_url = promo.get("photo_url") or ""
        absolute_photo_url = _absolute_url(request, photo_url)
        page_url = str(request.url)
        bot_link = f"https://t.me/{CLIENT_BOT_USERNAME}?start=promo_{promo['master_id']}"
        return templates.TemplateResponse(
            request=request,
            name="promo_page.html",
            context={
                "slug": promo["slug"],
                "page_url": page_url,
                "display_name": promo["display_name"],
                "specialization": promo["specialization"],
                "tagline": promo["tagline"],
                "badge_text": promo.get("badge_text"),
                "service_name": promo["service_name"],
                "service_price": promo["service_price"],
                "promo_enabled": promo.get("promo_enabled", False),
                "promo_text": promo.get("promo_text"),
                "advantages": promo.get("advantages", []),
                "sub_button_text": promo.get("sub_button_text") or "Бонусы и уведомления в Telegram",
                "photo_url": photo_url,
                "absolute_photo_url": absolute_photo_url,
                "style": style,
                "is_dark_style": _is_dark_style(style),
                "bot_link": bot_link,
            },
        )

    data = await get_landing_data(page_key)
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
    landing_theme = data.get("landing_theme") or "sunset"
    avatar_initials = _initials(name)
    currency_symbol = _CURRENCY_SYMBOLS.get(currency, currency)

    cta_link = f"https://t.me/{CLIENT_BOT_USERNAME}?start={page_key}"
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

    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={
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
            "landing_theme": landing_theme,
        },
    )
