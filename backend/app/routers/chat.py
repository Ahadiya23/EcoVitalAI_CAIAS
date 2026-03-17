from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic
from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])
settings = get_settings()


@router.get("/stream")
async def stream_chat(
    user_id: str = Query(...),
    message: str = Query(...),
    session: AsyncSession = Depends(get_db),
):
    risk_query = text(
        """
        select risk_score, explanation
        from risk_scores
        where user_id = cast(:user_id as uuid)
        order by timestamp desc
        limit 1
        """
    )
    result = await session.execute(risk_query, {"user_id": user_id})
    latest = result.mappings().first() or {"risk_score": 0, "explanation": ""}

    profile_query = text(
        """
        select conditions
        from health_profiles
        where user_id = cast(:user_id as uuid)
        """
    )
    profile_result = await session.execute(profile_query, {"user_id": user_id})
    profile = profile_result.mappings().first() or {"conditions": []}

    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        stream = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            stream=True,
            system=(
                "You are EcoVital Health Advisor. "
                f"User's current risk score is {latest['risk_score']}/100. "
                f"Conditions: {profile['conditions']}. Be concise and actionable."
            ),
            messages=[{"role": "user", "content": message}],
        )
        async for event in stream:
            if event.type == "content_block_delta":
                yield {"event": "token", "data": event.delta.text}
        yield {"event": "done", "data": "[DONE]"}

    return EventSourceResponse(event_generator())
