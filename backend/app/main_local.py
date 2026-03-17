import asyncio
import math
import random
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Literal

import numpy as np
from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from slowapi import Limiter
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app = FastAPI(title="EcoVital AI Local API")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Profile(BaseModel):
    conditions: list[str] = Field(default_factory=list)
    age: int = 30
    location_lat: float = 12.9716
    location_lng: float = 77.5946
    medications: list[str] = Field(default_factory=list)


class Alert(BaseModel):
    threshold: int = 60
    push_token: str = ""
    phone: str = ""
    email: str = ""
    active: bool = True


class RiskPrediction(BaseModel):
    overall_score: float
    component_scores: dict[str, float]
    severity: Literal["low", "medium", "high", "critical"]
    confidence: float
    anomaly_flag: bool
    explanation: str


profiles: dict[str, Profile] = {}
alerts: dict[str, Alert] = {}
risk_history: defaultdict[str, list[dict]] = defaultdict(list)
community_reports: list[dict] = []


def _severity(score: float) -> Literal["low", "medium", "high", "critical"]:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def _calc_risk(lat: float, lng: float, profile: Profile) -> RiskPrediction:
    hour = datetime.now(UTC).hour
    base = 35 + 20 * math.sin(hour / 24 * math.pi * 2) + random.uniform(-5, 5)
    climate_factor = min(25, abs(lat) * 0.3 + abs(lng) * 0.05)
    condition_factor = 0
    c = [x.lower() for x in profile.conditions]
    if any("asthma" in x or "copd" in x for x in c):
        condition_factor += 12
    if any("heart" in x or "cardiac" in x for x in c):
        condition_factor += 10
    if any("allerg" in x for x in c):
        condition_factor += 8
    age_factor = 8 if profile.age >= 60 else 0
    score = float(np.clip(base + climate_factor + condition_factor + age_factor, 0, 100))

    components = {
        "asthma_risk": float(np.clip(score / 100 + (0.15 if "asthma" in " ".join(c) else 0), 0, 1)),
        "heat_risk": float(np.clip(score / 110, 0, 1)),
        "allergy_risk": float(np.clip(score / 115 + (0.2 if any("allerg" in x for x in c) else 0), 0, 1)),
        "cardiac_risk": float(np.clip(score / 105 + (0.15 if any("heart" in x or "cardiac" in x for x in c) else 0), 0, 1)),
    }
    sev = _severity(score)
    explanation = (
        f"Your current risk is {score:.0f}/100 ({sev}). "
        "Main drivers are current environmental load and your health profile, so reduce outdoor exertion during peak hours."
    )
    return RiskPrediction(
        overall_score=score,
        component_scores=components,
        severity=sev,
        confidence=0.79,
        anomaly_flag=score > 92,
        explanation=explanation,
    )


def _chat_reply(message: str, profile: Profile, prediction: RiskPrediction) -> str:
    query = message.lower().strip()
    conditions = [c.lower() for c in profile.conditions]

    if prediction.severity in {"high", "critical"}:
        risk_prefix = (
            f"Your current risk is {prediction.overall_score:.0f}/100 ({prediction.severity}), "
            "so be extra cautious right now."
        )
    elif prediction.severity == "medium":
        risk_prefix = (
            f"Your current risk is {prediction.overall_score:.0f}/100 ({prediction.severity}), "
            "so moderate precautions are recommended."
        )
    else:
        risk_prefix = (
            f"Your current risk is {prediction.overall_score:.0f}/100 ({prediction.severity}), "
            "so normal activity is generally fine with basic care."
        )

    if any(word in query for word in ["exercise", "workout", "run", "jog", "gym", "outside"]):
        if prediction.severity in {"high", "critical"}:
            advice = "Prefer indoor exercise today; if you must go outside, keep it short and avoid peak traffic hours."
        elif prediction.severity == "medium":
            advice = "Light-to-moderate outdoor activity is okay, but avoid high-intensity sessions during midday."
        else:
            advice = "Outdoor exercise is reasonable now; hydrate and stop if you feel breathless."
    elif any(word in query for word in ["smoke", "smoking", "cigarette", "vape"]):
        if any("asthma" in c or "copd" in c for c in conditions):
            advice = "Smoking or vaping can sharply worsen airway irritation for your profile, so avoid it completely today."
        elif any("heart" in c or "cardiac" in c for c in conditions):
            advice = "Smoking raises immediate cardiac strain risk, especially with environmental stress, so this is not a safe time to smoke."
        else:
            advice = "It is not safe to smoke: even one cigarette increases short-term lung and heart stress."
    elif any(word in query for word in ["pm2.5", "pm25", "aqi", "pollution", "air quality"]):
        if any("asthma" in c or "copd" in c for c in conditions):
            advice = "PM2.5 can trigger airway inflammation and bronchospasm, so use a mask outdoors and keep your rescue inhaler available."
        else:
            advice = "Poor AQI and PM2.5 increase breathing and cardiovascular stress, so reduce time near traffic and ventilate indoor air."
    elif any(word in query for word in ["evening", "night", "later", "today", "tonight"]):
        advice = "Plan lower-exposure activities for later hours, keep hydration steady, and avoid heavy exertion if symptoms appear."
    elif any(word in query for word in ["what should i do", "advice", "recommend", "help"]):
        advice = "Check your risk dashboard before going out, minimize exposure during peak-risk windows, and follow your prescribed medication routine."
    else:
        advice = (
            "I can give more specific guidance if you ask about exercise, smoking, air quality, or what to do this evening."
        )

    return f"{risk_prefix} {advice}"


@app.exception_handler(RateLimitExceeded)
async def ratelimit_handler(_: Request, __: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


@app.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    return {"status": "ok", "db": "local-memory", "redis": "local-memory"}


@app.get("/api/risk/current", response_model=RiskPrediction)
async def risk_current(lat: float = Query(...), lng: float = Query(...), user_id: str = Query(...)):
    profile = profiles.get(user_id, Profile(location_lat=lat, location_lng=lng))
    pred = _calc_risk(lat, lng, profile)
    risk_history[user_id].append(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "risk_score": pred.overall_score,
            "severity": pred.severity,
            "explanation": pred.explanation,
        }
    )
    return pred


@app.get("/api/risk/forecast")
async def risk_forecast(lat: float = Query(...), lng: float = Query(...), user_id: str = Query(...)):
    profile = profiles.get(user_id, Profile(location_lat=lat, location_lng=lng))
    baseline = _calc_risk(lat, lng, profile).overall_score
    scores = []
    for h in range(24):
        value = baseline + 15 * math.sin((h / 24) * math.pi * 2) + random.uniform(-4, 4)
        scores.append(float(np.clip(value, 0, 100)))
    peak = max(scores)
    return {
        "hourly_scores": scores,
        "worst_hour": int(scores.index(peak)),
        "best_hour": int(scores.index(min(scores))),
        "peak_risk": float(peak),
    }


@app.get("/api/risk/history")
async def risk_history_api(user_id: str = Query(...), days: int = Query(7, ge=1, le=30)):
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = [x for x in risk_history[user_id] if datetime.fromisoformat(x["timestamp"]) >= cutoff]
    return list(reversed(rows[-200:]))


@app.get("/api/profile/{user_id}")
async def get_profile(user_id: str):
    return profiles.get(user_id, Profile()).model_dump()


@app.put("/api/profile/{user_id}")
async def put_profile(user_id: str, body: Profile):
    profiles[user_id] = body
    return {"success": True}


class AlertIn(BaseModel):
    user_id: str
    threshold: int = Field(ge=0, le=100)
    push_token: str = ""
    phone: str = ""
    email: str = ""


@app.post("/api/alerts/subscribe")
async def alerts_subscribe(body: AlertIn):
    alerts[body.user_id] = Alert(
        threshold=body.threshold,
        push_token=body.push_token,
        phone=body.phone,
        email=body.email,
        active=True,
    )
    return {"success": True}


@app.get("/api/map/heatmap")
async def map_heatmap(bbox: str):
    lat1, lng1, lat2, lng2 = [float(x) for x in bbox.split(",")]
    rows = []
    for _ in range(300):
        lat = random.uniform(min(lat1, lat2), max(lat1, lat2))
        lng = random.uniform(min(lng1, lng2), max(lng1, lng2))
        intensity = random.random() ** 2
        rows.append({"lat": lat, "lng": lng, "intensity": intensity})
    return {"type": "FeatureCollection", "features": [], "heat": rows}


class CommunityReport(BaseModel):
    lat: float
    lng: float
    symptoms: list[str]
    severity: str


@app.post("/api/map/report")
async def map_report(body: CommunityReport):
    community_reports.append(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "lat": body.lat,
            "lng": body.lng,
            "symptoms": body.symptoms,
            "severity": body.severity,
        }
    )
    return {"success": True, "message": "Thank you for reporting"}


@app.get("/api/chat/stream")
async def chat_stream(user_id: str = Query(...), message: str = Query(...)):
    async def event_generator():
        profile = profiles.get(user_id, Profile())
        prediction = _calc_risk(profile.location_lat, profile.location_lng, profile)
        text = _chat_reply(message, profile, prediction)
        for token in text.split(" "):
            yield {"event": "token", "data": token + " "}
            await asyncio.sleep(0.04)
        yield {"event": "done", "data": "[DONE]"}

    return EventSourceResponse(event_generator())


@app.websocket("/ws/risk-feed/{user_id}")
async def ws_feed(websocket: WebSocket, user_id: str):
    await websocket.accept()
    try:
        while True:
            profile = profiles.get(user_id, Profile())
            pred = _calc_risk(profile.location_lat, profile.location_lng, profile)
            await websocket.send_json(pred.model_dump())
            await asyncio.sleep(8)
    except WebSocketDisconnect:
        return
