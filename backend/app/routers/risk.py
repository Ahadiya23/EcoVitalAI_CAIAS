import json
from datetime import datetime

from anthropic import AsyncAnthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_data_service, get_db, get_risk_predictor
from app.models.schemas import RiskPrediction, UserProfile

router = APIRouter(prefix="/api/risk", tags=["risk"])
settings = get_settings()


async def _load_user_profile(session: AsyncSession, user_id: str) -> UserProfile:
    query = text(
        """
        select user_id::text, conditions, age, location_lat, location_lng, medications
        from health_profiles
        where user_id = cast(:user_id as uuid)
        """
    )
    result = await session.execute(query, {"user_id": user_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return UserProfile(
        user_id=row["user_id"],
        conditions=row["conditions"] or [],
        age=row["age"],
        location_lat=row["location_lat"],
        location_lng=row["location_lng"],
        medications=row["medications"] or [],
    )


@router.get("/current", response_model=RiskPrediction)
async def get_current_risk(
    lat: float = Query(...),
    lng: float = Query(...),
    user_id: str = Query(...),
    session: AsyncSession = Depends(get_db),
    data_service=Depends(get_data_service),
    predictor=Depends(get_risk_predictor),
):
    snapshot = await data_service.aggregate_environmental_snapshot(lat, lng)
    profile = await _load_user_profile(session, user_id)
    feature_vector = data_service.compute_feature_vector(snapshot, profile)
    prediction = predictor.predict(feature_vector)

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = (
        f"Risk score: {prediction.overall_score:.1f}/100 ({prediction.severity}). "
        f"Environment: {snapshot.model_dump_json()}. "
        f"User conditions: {profile.conditions}. "
        "Explain the dominant risk factor and one action to take."
    )
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        system="You are EcoVital AI. Respond in 2 friendly sentences.",
        messages=[{"role": "user", "content": prompt}],
    )
    prediction.explanation = response.content[0].text if response.content else ""

    insert = text(
        """
        insert into risk_scores (user_id, timestamp, risk_score, risk_category, component_scores, explanation, anomaly_flag)
        values (cast(:user_id as uuid), :timestamp, :risk_score, :risk_category, cast(:component_scores as jsonb), :explanation, :anomaly_flag)
        """
    )
    await session.execute(
        insert,
        {
            "user_id": user_id,
            "timestamp": datetime.utcnow(),
            "risk_score": prediction.overall_score,
            "risk_category": prediction.severity,
            "component_scores": json.dumps(prediction.component_scores),
            "explanation": prediction.explanation,
            "anomaly_flag": prediction.anomaly_flag,
        },
    )
    await session.commit()
    return prediction


@router.get("/forecast")
async def get_forecast(
    lat: float = Query(...),
    lng: float = Query(...),
    user_id: str = Query(...),
    session: AsyncSession = Depends(get_db),
    data_service=Depends(get_data_service),
    predictor=Depends(get_risk_predictor),
):
    profile = await _load_user_profile(session, user_id)
    query = text(
        """
        select *
        from environmental_readings
        where location_lat between :lat_low and :lat_high
          and location_lng between :lng_low and :lng_high
        order by time desc
        limit 6
        """
    )
    result = await session.execute(
        query,
        {"lat_low": lat - 0.05, "lat_high": lat + 0.05, "lng_low": lng - 0.05, "lng_high": lng + 0.05},
    )
    rows = list(result.mappings())
    if len(rows) < 6:
        snapshot = await data_service.aggregate_environmental_snapshot(lat, lng)
        vector = data_service.compute_feature_vector(snapshot, profile)
        sequence = [vector for _ in range(6)]
    else:
        sequence = []
        for row in reversed(rows):
            snapshot = await data_service.aggregate_environmental_snapshot(
                row["location_lat"], row["location_lng"]
            )
            sequence.append(data_service.compute_feature_vector(snapshot, profile))

    forecast = predictor.forecast_24h(__import__("numpy").array(sequence))
    peak_risk = max(forecast) if forecast else 0
    worst_hour = forecast.index(peak_risk) if forecast else 0
    best_risk = min(forecast) if forecast else 0
    best_hour = forecast.index(best_risk) if forecast else 0
    return {
        "hourly_scores": forecast,
        "worst_hour": worst_hour,
        "best_hour": best_hour,
        "peak_risk": peak_risk,
    }


@router.get("/history")
async def get_history(
    user_id: str = Query(...),
    days: int = Query(7, ge=1, le=30),
    session: AsyncSession = Depends(get_db),
):
    query = text(
        """
        select timestamp, risk_score, risk_category as severity, explanation
        from risk_scores
        where user_id = cast(:user_id as uuid)
          and timestamp >= now() - (:days || ' day')::interval
        order by timestamp desc
        """
    )
    result = await session.execute(query, {"user_id": user_id, "days": days})
    return [dict(row) for row in result.mappings().all()]
