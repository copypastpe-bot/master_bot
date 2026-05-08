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

_ICON_SVG = {
    "⏰": '<svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 11h5v-2h-4V6h-2v7Z"/></svg>',
    "🧴": '<svg viewBox="0 0 24 24"><path d="M9 2h6v3l-2 2v2h1a4 4 0 0 1 4 4v7a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-7a4 4 0 0 1 4-4h1V7L9 5V2Zm1 12v5h4v-5h-4Z"/></svg>',
    "🔔": '<svg viewBox="0 0 24 24"><path d="M12 22a2.8 2.8 0 0 0 2.65-2H9.35A2.8 2.8 0 0 0 12 22Zm7-6-2-2v-4a5 5 0 0 0-4-4.9V3h-2v2.1A5 5 0 0 0 7 10v4l-2 2v2h14v-2Z"/></svg>',
    "🌿": '<svg viewBox="0 0 24 24"><path d="M17 8C8 10 5.9 16.17 3.82 21.34l1.89.66.95-2.3c.48.17.98.3 1.34.3C19 20 22 3 22 3c-1 2-8 2.25-13 3.25S2 11.5 2 13.5s1.75 3.75 1.75 3.75C7 8 17 8 17 8Z"/></svg>',
    "📸": '<svg viewBox="0 0 24 24"><path d="M12 15.2A3.2 3.2 0 1 0 12 8.8a3.2 3.2 0 0 0 0 6.4ZM9 2 7.17 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-3.17L15 2H9Zm3 15a5 5 0 1 1 0-10 5 5 0 0 1 0 10Z"/></svg>',
    "⭐": '<svg viewBox="0 0 24 24"><path d="m12 2.5 2.9 5.87 6.48.94-4.69 4.57 1.11 6.45L12 17.28l-5.8 3.05 1.11-6.45-4.69-4.57 6.48-.94L12 2.5Z"/></svg>',
    "✂️": '<svg viewBox="0 0 24 24"><path d="M9.6 7.4A3.5 3.5 0 1 0 8 10.34L11.66 14 8 17.66A3.5 3.5 0 1 0 9.6 20.6L20.2 10l-1.4-1.4-5.72 5.72-3.48-3.48ZM5.5 9A1.5 1.5 0 1 1 5.5 6a1.5 1.5 0 0 1 0 3Zm0 10A1.5 1.5 0 1 1 5.5 16a1.5 1.5 0 0 1 0 3Z"/></svg>',
    "💈": '<svg viewBox="0 0 24 24"><path d="M9 2h6v3l-2 2v2h1a4 4 0 0 1 4 4v7a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-7a4 4 0 0 1 4-4h1V7L9 5V2Zm1 12v5h4v-5h-4Z"/></svg>',
    "🧼": '<svg viewBox="0 0 24 24"><path d="M12 2 4 5v6c0 5.1 3.4 9.9 8 11 4.6-1.1 8-5.9 8-11V5l-8-3Zm-1 14-4-4 1.4-1.4 2.6 2.6 5.6-5.6L18 9l-7 7Z"/></svg>',
    "💡": '<svg viewBox="0 0 24 24"><path d="M12 2a7 7 0 0 0-4 12.74V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.26A7 7 0 0 0 12 2ZM9 20v1a3 3 0 0 0 6 0v-1H9Z"/></svg>',
    "📍": '<svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5Z"/></svg>',
    "💅": '<svg viewBox="0 0 24 24"><path d="M18.7 3.3a2.4 2.4 0 0 0-3.4 0l-7.8 7.8 3.4 3.4 7.8-7.8a2.4 2.4 0 0 0 0-3.4ZM7 12.8c-2.8.7-4 2.7-4 5.7 0 1 .7 1.5 1.6 1.2 1.6-.5 3.2-.3 4.4-1.5 1.2-1.2 1.2-3.1 0-4.3L7 12.8Z"/></svg>',
    "✨": '<svg viewBox="0 0 24 24"><path d="M13 2 9.9 8.9 3 12l6.9 3.1L13 22l3.1-6.9L23 12l-6.9-3.1L13 2ZM5 3l-1 2-2 1 2 1 1 2 1-2 2-1-2-1-1-2Z"/></svg>',
    "💗": '<svg viewBox="0 0 24 24"><path d="m12 21.35-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35Z"/></svg>',
    "🕯️": '<svg viewBox="0 0 24 24"><path d="M12 2C9.24 6 8 8.5 8 10.5A4 4 0 0 0 16 10.5C16 8.5 14.76 6 12 2ZM7 14v8h10v-8H7Z"/></svg>',
    "🤲": '<svg viewBox="0 0 24 24"><path d="M20 13c0 5-3.5 9-8 9s-8-4-8-9a8 8 0 0 1 3-6.24V4a4 4 0 0 1 4-4h2a4 4 0 0 1 4 4v2.76A8 8 0 0 1 20 13Z"/></svg>',
    "💪": '<svg viewBox="0 0 24 24"><path d="m12 2.5 2.9 5.87 6.48.94-4.69 4.57 1.11 6.45L12 17.28l-5.8 3.05 1.11-6.45-4.69-4.57 6.48-.94L12 2.5Z"/></svg>',
    "📚": '<svg viewBox="0 0 24 24"><path d="M6 2a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H6Zm1 4h10v2H7V6Zm0 4h7v2H7v-2Z"/></svg>',
    "🎯": '<svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm0 16a6 6 0 1 1 6-6 6 6 0 0 1-6 6Zm0-8a2 2 0 1 0 2 2 2 2 0 0 0-2-2Z"/></svg>',
    "✏️": '<svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25ZM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83Z"/></svg>',
    "📖": '<svg viewBox="0 0 24 24"><path d="M6 2a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H6Zm1 4h10v2H7V6Zm0 4h7v2H7v-2Z"/></svg>',
    "✓": '<svg viewBox="0 0 24 24"><path d="M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17Z"/></svg>',
}

_DEFAULT_ICON_SVG = '<svg viewBox="0 0 24 24"><path d="M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17Z"/></svg>'
_PUBLIC_STRINGS = {
    "ru": {
        "og_locale": "ru_RU",
        "popular_service": "Популярная услуга",
        "from_price": "от",
        "promo_cta": "Забрать бонусы и подписаться",
        "promo_subtext": "Бонусы и уведомления в Telegram",
        "landing_title_not_found": "Страница не найдена",
        "landing_missing": "Мастер не найден или ссылка устарела.",
        "landing_cta_bonus": "Подписаться и получить {bonus} бонусов",
        "landing_cta_default": "Подписаться",
        "portfolio": "Портфолио",
        "reviews": "Отзывы",
        "services": "Услуги и цены",
        "contacts": "Контакты",
        "phone": "Телефон",
        "socials": "Соцсети",
    },
    "en": {
        "og_locale": "en_US",
        "popular_service": "Popular service",
        "from_price": "from",
        "promo_cta": "Claim bonuses and subscribe",
        "promo_subtext": "Bonuses and Telegram updates",
        "landing_title_not_found": "Page not found",
        "landing_missing": "The master was not found or the link is outdated.",
        "landing_cta_bonus": "Subscribe and get {bonus} bonuses",
        "landing_cta_default": "Subscribe",
        "portfolio": "Portfolio",
        "reviews": "Reviews",
        "services": "Services & prices",
        "contacts": "Contacts",
        "phone": "Phone",
        "socials": "Socials",
    },
}


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
    return bool(style.get("is_dark", False))


def _normalize_public_language(raw: str | None) -> str:
    value = str(raw or "").strip().lower()
    return "en" if value.startswith("en") else "ru"


def _style_with_defaults(style: dict | None) -> dict:
    data = dict(style or {})
    defaults = {
        "screen_bg": "#f7faf5",
        "screen_fg": "#1a2a1e",
        "screen_muted": "#566b5e",
        "screen_accent": "#2d8049",
        "badge_bg": "rgba(255,255,255,.8)",
        "badge_fg": "#1f6e3a",
        "badge_border": "rgba(255,255,255,.68)",
        "card_bg": "#eef5eb",
        "card_border": "#d5e5cf",
        "pill_bg": "#deedda",
        "pill_border": "#7aba6e",
        "offer_bg": "#faf0ec",
        "offer_border": "#e8c9bc",
        "offer_fg": "#8c4a2a",
        "cta_bg": "#2d8049",
        "cta_fg": "#ffffff",
        "cta_shadow": "rgba(31,135,79,.22)",
        "is_dark": False,
    }
    return {**defaults, **data}


@router.get("/m/{page_key}", response_class=HTMLResponse)
async def landing_page(request: Request, page_key: str):
    """Render public promo page by slug, or legacy master landing by invite token."""
    promo = await get_promo_public_data(page_key, increment_view=True)
    if promo is not None:
        language = _normalize_public_language(promo.get("language"))
        strings = _PUBLIC_STRINGS[language]
        style = _style_with_defaults(promo.get("style", {}).get("config"))
        advantages_with_svg = []
        for adv in promo.get("advantages", []):
            svg = _ICON_SVG.get(adv.get("icon", ""), _DEFAULT_ICON_SVG)
            advantages_with_svg.append({**adv, "svg": svg})
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
                "language": language,
                "og_locale": strings["og_locale"],
                "tagline": promo["tagline"],
                "badge_text": promo.get("badge_text"),
                "service_name": promo["service_name"],
                "service_price": promo["service_price"],
                "popular_service_label": strings["popular_service"],
                "from_price_label": strings["from_price"],
                "promo_enabled": promo.get("promo_enabled", False),
                "promo_text": promo.get("promo_text"),
                "advantages": advantages_with_svg,
                "cta_button_text": strings["promo_cta"],
                "sub_button_text": promo.get("sub_button_text") or strings["promo_subtext"],
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

    language = _normalize_public_language(data.get("language"))
    strings = _PUBLIC_STRINGS[language]
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
        cta_text = strings["landing_cta_bonus"].format(bonus=bonus_welcome)
    else:
        cta_text = strings["landing_cta_default"]

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
            "language": language,
            "og_locale": strings["og_locale"],
            "portfolio_label": strings["portfolio"],
            "reviews_label": strings["reviews"],
            "services_label": strings["services"],
            "contacts_label": strings["contacts"],
            "phone_label": strings["phone"],
            "socials_label": strings["socials"],
        },
    )
