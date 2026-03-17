from collections.abc import AsyncGenerator

import httpx
from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_risk_predictor(request: Request):
    return request.app.state.risk_predictor


def get_data_service(request: Request):
    return request.app.state.data_service
