"""FastAPI entry point for TrendPulse local control API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import settings, trends

app = FastAPI(
    title="TrendPulse API",
    description="Monitor semanal de tendencias musicales globales (7 días + crecimiento rápido + previews)",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trends.router)
app.include_router(settings.router)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Simple local backend healthcheck."""
    return {"status": "ok", "app": "TrendPulse"}
