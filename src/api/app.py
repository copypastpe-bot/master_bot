"""FastAPI application for Mini App backend."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import client, orders, bonuses, promos, services
from src.config import MINIAPP_URL

app = FastAPI(
    title="Master Bot API",
    description="API for Telegram Mini App",
    version="1.0.0",
)

# CORS for Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=[MINIAPP_URL, "http://localhost:5173"],  # Mini App + local dev
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/debug/headers")
async def debug_headers(request: Request):
    """Debug endpoint — returns received headers (remove after debugging)."""
    init_data = request.headers.get("x-init-data", "")
    return {
        "x_init_data_present": bool(init_data),
        "x_init_data_length": len(init_data),
        "x_init_data_preview": init_data[:80] + "..." if len(init_data) > 80 else init_data,
        "all_headers": dict(request.headers),
    }
