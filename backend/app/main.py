import os
import sys
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import from_url as redis_from_url
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.database import SessionLocal, engine
from app.routers import alerts, chat, map, profile, risk, ws
from app.services.alert_scheduler import build_scheduler
from app.services.data_ingestion import EnvironmentalDataService

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from ml.inference.predictor import RiskPredictor  # noqa: E402

settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    app.state.http_client = httpx.AsyncClient(timeout=10.0, verify=True)
    app.state.redis = redis_from_url(settings.redis_url, decode_responses=True)
    app.state.session_factory = SessionLocal
    app.state.data_service = EnvironmentalDataService(
        client=app.state.http_client,
        redis_client=app.state.redis,
        api_keys={
            "openweather": settings.openweather_api_key,
            "waqi": settings.waqi_api_key,
            "openuv": settings.openuv_api_key,
            "ambee": settings.ambee_api_key,
        },
    )
    app.state.risk_predictor = RiskPredictor()
    app.state.scheduler = build_scheduler(app)
    app.state.scheduler.start()
    try:
        yield
    finally:
        app.state.scheduler.shutdown()
        await app.state.http_client.aclose()
        await app.state.redis.close()
        await engine.dispose()


app = FastAPI(title="EcoVital AI API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda request, exc: JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"}),
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(risk.router)
app.include_router(map.router)
app.include_router(alerts.router)
app.include_router(profile.router)
app.include_router(chat.router)
app.include_router(ws.router)


@app.get("/health")
@limiter.limit("60/minute")
async def health(_: Request):
    redis_ok = await app.state.redis.ping()
    return {"status": "ok", "db": "connected", "redis": bool(redis_ok)}
