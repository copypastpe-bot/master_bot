"""OAuth callback server for Google Calendar integration."""

import logging
from aiohttp import web

from src.config import OAUTH_SERVER_PORT, MASTER_BOT_TOKEN
from src.google_calendar import exchange_code, validate_oauth_state
from src.database import get_master_by_id

logger = logging.getLogger(__name__)

# Master bot instance will be set from main.py
master_bot = None


def set_master_bot(bot):
    """Set master bot instance for sending notifications."""
    global master_bot
    master_bot = bot


async def handle_oauth_callback(request: web.Request) -> web.Response:
    """Handle OAuth callback from Google."""
    code = request.rel_url.query.get("code")
    state = request.rel_url.query.get("state")  # CSRF token
    error = request.rel_url.query.get("error")

    logger.info(f"OAuth callback: has_state={bool(state)}, error={error}, has_code={bool(code)}")

    if not state:
        return web.Response(
            text="<h1>Ошибка</h1><p>Отсутствует state параметр.</p>",
            content_type="text/html"
        )

    # Validate CSRF token and get master_id
    master_id = validate_oauth_state(state)
    if master_id is None:
        logger.warning(f"Invalid or expired OAuth state token")
        return web.Response(
            text=(
                "<html><head><meta charset='utf-8'></head><body>"
                "<h1>Ошибка</h1>"
                "<p>Ссылка недействительна или истекла.</p>"
                "<p>Попробуйте снова в боте.</p>"
                "</body></html>"
            ),
            content_type="text/html"
        )

    master = await get_master_by_id(master_id)
    if not master:
        return web.Response(
            text="<h1>Ошибка</h1><p>Мастер не найден.</p>",
            content_type="text/html"
        )

    if error:
        # User denied access
        logger.warning(f"OAuth denied for master {master_id}: {error}")

        # Notify master
        if master_bot:
            try:
                await master_bot.send_message(
                    master.tg_id,
                    "❌ Google Calendar не подключён.\n\n"
                    "Вы отменили авторизацию или произошла ошибка.\n"
                    "Попробуйте снова в Настройках."
                )
            except Exception as e:
                logger.error(f"Failed to notify master {master_id}: {e}")

        return web.Response(
            text=(
                "<html><head><meta charset='utf-8'></head><body>"
                "<h1>Авторизация отменена</h1>"
                "<p>Вы можете закрыть это окно и попробовать снова в боте.</p>"
                "</body></html>"
            ),
            content_type="text/html"
        )

    if code:
        # Exchange code for tokens
        email = await exchange_code(master_id, code)

        if email:
            logger.info(f"OAuth success for master {master_id}: {email}")

            # Notify master
            if master_bot:
                try:
                    await master_bot.send_message(
                        master.tg_id,
                        f"✅ Google Calendar подключён!\n\n"
                        f"Аккаунт: {email}\n"
                        f"Теперь все заказы будут автоматически\n"
                        f"появляться в вашем календаре."
                    )
                except Exception as e:
                    logger.error(f"Failed to notify master {master_id}: {e}")

            return web.Response(
                text=(
                    "<html><head><meta charset='utf-8'></head><body>"
                    f"<h1>✅ Google Calendar подключён!</h1>"
                    f"<p>Аккаунт: {email}</p>"
                    f"<p>Вы можете закрыть это окно.</p>"
                    "</body></html>"
                ),
                content_type="text/html"
            )
        else:
            logger.error(f"OAuth token exchange failed for master {master_id}")

            # Notify master
            if master_bot:
                try:
                    await master_bot.send_message(
                        master.tg_id,
                        "❌ Google Calendar не подключён.\n\n"
                        "Произошла ошибка при обмене токенов.\n"
                        "Попробуйте снова в Настройках."
                    )
                except Exception as e:
                    logger.error(f"Failed to notify master {master_id}: {e}")

            return web.Response(
                text=(
                    "<html><head><meta charset='utf-8'></head><body>"
                    "<h1>Ошибка</h1>"
                    "<p>Не удалось получить токен. Попробуйте снова.</p>"
                    "</body></html>"
                ),
                content_type="text/html"
            )

    return web.Response(
        text="<h1>Ошибка</h1><p>Неизвестная ошибка.</p>",
        content_type="text/html"
    )


async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.Response(text="OK")


@web.middleware
async def security_headers_middleware(request: web.Request, handler):
    """Add security headers to all responses."""
    response = await handler(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
    return response


def create_app() -> web.Application:
    """Create aiohttp application with security middleware."""
    app = web.Application(middlewares=[security_headers_middleware])
    app.router.add_get("/auth/google/callback", handle_oauth_callback)
    app.router.add_get("/health", health_check)
    return app


async def run_oauth_server():
    """Run OAuth server."""
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", OAUTH_SERVER_PORT)
    await site.start()

    logger.info(f"OAuth server started on port {OAUTH_SERVER_PORT}")

    # Keep running
    while True:
        import asyncio
        await asyncio.sleep(3600)
