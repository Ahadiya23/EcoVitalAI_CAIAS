from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class AlertSubscribeRequest(BaseModel):
    user_id: str
    threshold: int = Field(ge=0, le=100)
    push_token: str = ""
    phone: str = ""
    email: str = ""


@router.post("/subscribe")
async def subscribe_alert(body: AlertSubscribeRequest, session: AsyncSession = Depends(get_db)):
    query = text(
        """
        insert into alerts (user_id, threshold, push_token, phone, email, active)
        values (cast(:user_id as uuid), :threshold, :push_token, :phone, :email, true)
        on conflict (user_id)
        do update set
          threshold = excluded.threshold,
          push_token = excluded.push_token,
          phone = excluded.phone,
          email = excluded.email,
          active = true
        """
    )
    await session.execute(
        query,
        {
            "user_id": body.user_id,
            "threshold": body.threshold,
            "push_token": body.push_token,
            "phone": body.phone,
            "email": body.email,
        },
    )
    await session.commit()
    return {"success": True}
