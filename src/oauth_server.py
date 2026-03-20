"""OAuth callback server for Google Calendar integration."""

import logging
import time
from collections import defaultdict
from aiohttp import web

from src.config import OAUTH_SERVER_PORT, MASTER_BOT_TOKEN
from src.google_calendar import exchange_code, validate_oauth_state
from src.database import get_master_by_id

logger = logging.getLogger(__name__)

# Master bot instance will be set from main.py
master_bot = None

# =============================================================================
# Rate Limiting
# =============================================================================

# Store request timestamps per IP: {ip: [timestamp1, timestamp2, ...]}
_rate_limit_storage: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_REQUESTS = 10  # Max requests
_RATE_LIMIT_WINDOW = 60  # Per 60 seconds
_RATE_LIMIT_CLEANUP_INTERVAL = 300  # Cleanup every 5 minutes
_last_cleanup = time.time()


def _get_client_ip(request: web.Request) -> str:
    """Get client IP, considering proxy headers."""
    # Check X-Forwarded-For (set by nginx)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take first IP (original client)
        return forwarded.split(",")[0].strip()
    # Check X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    # Fallback to direct connection
    peername = request.transport.get_extra_info("peername")
    return peername[0] if peername else "unknown"


def _cleanup_rate_limits() -> None:
    """Remove expired entries from rate limit storage."""
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < _RATE_LIMIT_CLEANUP_INTERVAL:
        return
    _last_cleanup = now
    cutoff = now - _RATE_LIMIT_WINDOW
    expired_ips = []
    for ip, timestamps in _rate_limit_storage.items():
        _rate_limit_storage[ip] = [t for t in timestamps if t > cutoff]
        if not _rate_limit_storage[ip]:
            expired_ips.append(ip)
    for ip in expired_ips:
        del _rate_limit_storage[ip]


def _is_rate_limited(ip: str) -> bool:
    """Check if IP is rate limited. Returns True if should be blocked."""
    _cleanup_rate_limits()
    now = time.time()
    cutoff = now - _RATE_LIMIT_WINDOW

    # Filter old timestamps
    timestamps = [t for t in _rate_limit_storage[ip] if t > cutoff]
    _rate_limit_storage[ip] = timestamps

    if len(timestamps) >= _RATE_LIMIT_REQUESTS:
        return True

    # Record this request
    _rate_limit_storage[ip].append(now)
    return False


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
async def rate_limit_middleware(request: web.Request, handler):
    """Rate limit requests to OAuth endpoint."""
    # Only rate limit OAuth callback, not health check
    if request.path == "/auth/google/callback":
        ip = _get_client_ip(request)
        if _is_rate_limited(ip):
            logger.warning(f"Rate limit exceeded for IP {ip}")
            return web.Response(
                status=429,
                text=(
                    "<html><head><meta charset='utf-8'></head><body>"
                    "<h1>Слишком много запросов</h1>"
                    "<p>Подождите минуту и попробуйте снова.</p>"
                    "</body></html>"
                ),
                content_type="text/html",
                headers={"Retry-After": "60"}
            )
    return await handler(request)


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
    # Rate limiting runs first, then security headers
    app = web.Application(middlewares=[rate_limit_middleware, security_headers_middleware])
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
