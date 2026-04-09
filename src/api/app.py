"""FastAPI application for Mini App backend."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.routers import client, orders, bonuses, promos, services
from src.api.routers import auth_router
from src.api.routers import client_masters
from src.api.routers import requests as client_requests
from src.api.routers.master import dashboard as master_dashboard
from src.api.routers.master import calendar as master_calendar
from src.api.routers.master import orders as master_orders
from src.api.routers.master import clients as master_clients
from src.api.routers.master import settings as master_settings
from src.api.routers.master import promos as master_promos
from src.api.routers.master import broadcast as master_broadcast
from src.api.routers.master import reports as master_reports
from src.api.routers.master import auth as master_auth
from src.api.routers.master import requests as master_requests
from src.api.routers.master import subscription as master_subscription
from src.config import MINIAPP_URL
from src.api.dependencies import SubscriptionRequiredError
from urllib.parse import urlparse

app = FastAPI(
    title="Master Bot API",
    description="API for Telegram Mini App",
    version="1.0.0",
)

# CORS origin = scheme + host (strip path/query from MINIAPP_URL)
_parsed = urlparse(MINIAPP_URL)
_miniapp_origin = f"{_parsed.scheme}://{_parsed.netloc}"

# CORS for Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        _miniapp_origin,
        "http://localhost:5173",
        "https://ru.app.crmfit.ru",
    ],  # Mini App + local dev + RU proxy
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BONUS_MEDIA_DIR = Path("/app/data/bonus_media")
BONUS_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/bonus-media", StaticFiles(directory=str(BONUS_MEDIA_DIR)), name="bonus-media")

# Include routers
app.include_router(client.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(bonuses.router, prefix="/api")
app.include_router(promos.router, prefix="/api")
app.include_router(services.router, prefix="/api")
app.include_router(auth_router.router, prefix="/api")
app.include_router(client_masters.router, prefix="/api")
app.include_router(client_requests.router, prefix="/api")
app.include_router(master_dashboard.router, prefix="/api")
app.include_router(master_calendar.router, prefix="/api")
app.include_router(master_orders.router, prefix="/api")
app.include_router(master_clients.router, prefix="/api")
app.include_router(master_settings.router, prefix="/api")
app.include_router(master_promos.router, prefix="/api")
app.include_router(master_broadcast.router, prefix="/api")
app.include_router(master_reports.router, prefix="/api")
app.include_router(master_auth.router, prefix="/api")
app.include_router(master_requests.router, prefix="/api")
app.include_router(master_subscription.router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.exception_handler(SubscriptionRequiredError)
async def handle_subscription_required(_request, exc: SubscriptionRequiredError):
    """Return compact subscription-required payload without FastAPI detail wrapper."""
    return JSONResponse(status_code=403, content=exc.payload)
