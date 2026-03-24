"""FastAPI application for Mini App backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import client, orders, bonuses, promos, services
from src.api.routers import auth_router
from src.api.routers.master import dashboard as master_dashboard
from src.config import MINIAPP_URL
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
    allow_origins=[_miniapp_origin, "http://localhost:5173"],  # Mini App + local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(client.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(bonuses.router, prefix="/api")
app.include_router(promos.router, prefix="/api")
app.include_router(services.router, prefix="/api")
app.include_router(auth_router.router, prefix="/api")
app.include_router(master_dashboard.router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


