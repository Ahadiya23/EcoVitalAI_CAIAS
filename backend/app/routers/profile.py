from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileUpsert(BaseModel):
    conditions: list[str]
    age: int
    location_lat: float
    location_lng: float
    medications: list[str] = []


@router.get("/{user_id}")
async def get_profile(user_id: str, session: AsyncSession = Depends(get_db)):
    query = text("select * from health_profiles where user_id = cast(:user_id as uuid)")
    result = await session.execute(query, {"user_id": user_id})
    row = result.mappings().first()
    return dict(row) if row else {}


@router.put("/{user_id}")
async def upsert_profile(user_id: str, body: ProfileUpsert, session: AsyncSession = Depends(get_db)):
    query = text(
        """
        insert into health_profiles (user_id, conditions, age, location_lat, location_lng, medications, updated_at)
        values (cast(:user_id as uuid), :conditions, :age, :location_lat, :location_lng, :medications, now())
        on conflict (user_id)
        do update set
          conditions = excluded.conditions,
          age = excluded.age,
          location_lat = excluded.location_lat,
          location_lng = excluded.location_lng,
          medications = excluded.medications,
          updated_at = now()
        """
    )
    await session.execute(
        query,
        {
            "user_id": user_id,
            "conditions": body.conditions,
            "age": body.age,
            "location_lat": body.location_lat,
            "location_lng": body.location_lng,
            "medications": body.medications,
        },
    )
    await session.commit()
    return {"success": True}
