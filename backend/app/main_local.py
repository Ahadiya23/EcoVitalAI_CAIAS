import asyncio
import json
import logging
import math
import os
import random
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

import numpy as np
from anthropic import AsyncAnthropic
from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from sse_starlette.sse import EventSourceResponse
from slowapi import Limiter
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app = FastAPI(title="EcoVital AI Local API", version="1.1.0")
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
    risk_reasons: list[str] = Field(default_factory=list)
    prevention_tips: list[str] = Field(default_factory=list)
    user_context: dict = Field(default_factory=dict)


profiles: dict[str, Profile] = {}
alerts: dict[str, Alert] = {}
risk_history: defaultdict[str, list[dict]] = defaultdict(list)
community_reports: list[dict] = []
anthropic_client: AsyncAnthropic | None = None
anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
gemini_enabled = False
gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
gemini_api_key = ""
logger = logging.getLogger("ecovital.local")


def _severity(score: float) -> Literal["low", "medium", "high", "critical"]:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def _location_aqi_details(lat: float, lng: float) -> dict:
    """Generate deterministic pseudo-live AQI details by location."""
    hour = datetime.now(UTC).hour
    seed = abs(lat * 37.0 + lng * 13.0) % 100
    aqi = int(np.clip(40 + seed + 15 * math.sin(hour / 24 * 2 * math.pi), 15, 320))
    pm25 = round(max(5.0, aqi * 0.55), 1)
    pm10 = round(max(8.0, aqi * 0.7), 1)
    o3 = round(max(5.0, aqi * 0.25), 1)
    no2 = round(max(4.0, aqi * 0.2), 1)
    if aqi >= 201:
        category = "very_unhealthy"
        dominant = "pm25"
    elif aqi >= 151:
        category = "unhealthy"
        dominant = "pm25"
    elif aqi >= 101:
        category = "unhealthy_for_sensitive"
        dominant = "pm10"
    elif aqi >= 51:
        category = "moderate"
        dominant = "o3"
    else:
        category = "good"
        dominant = "no2"
    recommendation = {
        "good": "Air quality is good for normal outdoor activity.",
        "moderate": "Sensitive users should reduce prolonged outdoor exertion.",
        "unhealthy_for_sensitive": "Sensitive groups should limit outdoor time and use masks.",
        "unhealthy": "Keep outdoor exposure brief and avoid heavy exertion.",
        "very_unhealthy": "Avoid outdoor activity unless necessary and use strong protection.",
    }[category]
    return {
        "aqi": aqi,
        "category": category,
        "dominant_pollutant": dominant,
        "pm25": pm25,
        "pm10": pm10,
        "o3": o3,
        "no2": no2,
        "recommendation": recommendation,
    }


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
    location_aqi = _location_aqi_details(lat, lng)
    reasons: list[str] = []
    if location_aqi["aqi"] >= 151:
        reasons.append(
            f"Very high AQI ({location_aqi['aqi']}) with dominant {location_aqi['dominant_pollutant']} is elevating respiratory stress."
        )
    elif location_aqi["aqi"] >= 101:
        reasons.append(
            f"Moderately unhealthy AQI ({location_aqi['aqi']}) is increasing breathing and circulation load."
        )
    if components["asthma_risk"] >= 0.6:
        reasons.append("Asthma-sensitive risk component is elevated due to pollution interaction.")
    if components["cardiac_risk"] >= 0.6:
        reasons.append("Cardiac risk component is elevated because environmental stress can raise heart strain.")
    if profile.age >= 60:
        reasons.append("Age-related vulnerability contributes to higher risk sensitivity.")
    if not reasons:
        reasons.append("Current environmental and profile signals indicate manageable but non-zero risk.")

    tips = [
        location_aqi["recommendation"],
        "Prefer indoor activity during peak pollution periods and keep hydration steady.",
        "Use a well-fitted mask outdoors when AQI is moderate or worse.",
    ]
    if any("asthma" in c.lower() or "copd" in c.lower() for c in profile.conditions):
        tips.append("Carry rescue inhaler and avoid high-intensity outdoor exertion when symptomatic.")
    if any("heart" in c.lower() or "cardiac" in c.lower() for c in profile.conditions):
        tips.append("Avoid strenuous activity in poor air quality and monitor unusual chest discomfort.")
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
        risk_reasons=reasons[:4],
        prevention_tips=tips[:5],
        user_context={
            "age": profile.age,
            "conditions": profile.conditions,
            "location": {"lat": lat, "lng": lng},
            "aqi": location_aqi,
        },
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


async def _ai_risk_explanation(
    message: str,
    profile: Profile,
    prediction: RiskPrediction,
    location_aqi: dict,
) -> str | None:
    if anthropic_client is None:
        return None
    system = (
        "You are EcoVital AI, a preventive health advisor. "
        "Provide concise, practical, and question-specific guidance in 2-4 sentences. "
        "Mention the dominant risk reason and one immediate action."
    )
    prompt = (
        f"User question: {message}\n"
        f"Risk score: {prediction.overall_score:.1f}/100 ({prediction.severity}).\n"
        f"AQI context: {location_aqi}.\n"
        f"User profile: age={profile.age}, conditions={profile.conditions}, medications={profile.medications}.\n"
        f"Risk reasons: {prediction.risk_reasons}.\n"
        f"Prevention tips: {prediction.prevention_tips}."
    )
    try:
        response = await anthropic_client.messages.create(
            model=anthropic_model,
            max_tokens=220,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        if response.content:
            return response.content[0].text.strip()
    except Exception as exc:
        logger.warning("Anthropic explanation fallback engaged: %s", exc)
        return None
    return None


_GEMINI_FALLBACK_MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite"]


def _gemini_call(model: str, system: str, prompt: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={gemini_api_key}"
    )
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 260},
    }
    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8) as response:
        body = json.loads(response.read().decode("utf-8"))
    candidates = body.get("candidates") or []
    if not candidates:
        return ""
    parts = (candidates[0].get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()


def _gemini_generate_sync(system: str, prompt: str) -> str:
    if not gemini_enabled or not gemini_api_key:
        return ""
    models_to_try = [gemini_model] + _GEMINI_FALLBACK_MODELS
    last_err = None
    for model in models_to_try:
        try:
            text = _gemini_call(model, system, prompt)
            if text:
                return text
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore")
            if exc.code == 429:
                logger.warning("Gemini %s rate-limited, trying next model…", model)
                last_err = RuntimeError(f"Gemini HTTP 429 on {model}")
                import time
                time.sleep(1)
                continue
            last_err = RuntimeError(f"Gemini HTTP {exc.code} on {model}: {error_body}")
            continue
        except urllib.error.URLError as exc:
            last_err = RuntimeError(f"Gemini network error: {exc.reason}")
            break
    if last_err:
        raise last_err
    return ""


async def _gemini_generate(system: str, prompt: str) -> str | None:
    if not gemini_enabled:
        return None
    try:
        text = await asyncio.to_thread(_gemini_generate_sync, system, prompt)
        return text or None
    except Exception as exc:
        logger.warning("Gemini generation fallback: %s", exc)
        return None


async def _ai_risk_explanation_with_fallback(
    message: str,
    profile: Profile,
    prediction: RiskPrediction,
    location_aqi: dict,
) -> str | None:
    anthropic_text = await _ai_risk_explanation(message, profile, prediction, location_aqi)
    if anthropic_text:
        logger.info("Risk explanation provider: anthropic")
        return anthropic_text

    system = (
        "You are EcoVital AI, a preventive health advisor. "
        "Provide concise, practical, and question-specific guidance in 2-4 sentences. "
        "Mention the dominant risk reason and one immediate action."
    )
    prompt = (
        f"User question: {message}\n"
        f"Risk score: {prediction.overall_score:.1f}/100 ({prediction.severity}).\n"
        f"AQI context: {location_aqi}.\n"
        f"User profile: age={profile.age}, conditions={profile.conditions}, medications={profile.medications}.\n"
        f"Risk reasons: {prediction.risk_reasons}.\n"
        f"Prevention tips: {prediction.prevention_tips}."
    )
    gemini_text = await _gemini_generate(system, prompt)
    if gemini_text:
        logger.info("Risk explanation provider: gemini")
        return gemini_text
    return None


async def _ai_chat_stream(
    message: str,
    profile: Profile,
    prediction: RiskPrediction,
    location_aqi: dict,
):
    if anthropic_client is None:
        return
    system = (
        "You are EcoVital Health Advisor. "
        "Answer based on the user's question and their risk context. "
        "Be concise, personalized, and actionable."
    )
    prompt = (
        f"Question: {message}\n"
        f"Current risk: {prediction.overall_score:.1f}/100 ({prediction.severity}).\n"
        f"AQI details: {location_aqi}.\n"
        f"Profile: age={profile.age}, conditions={profile.conditions}, medications={profile.medications}.\n"
        f"Reasons: {prediction.risk_reasons}.\n"
        f"Prevention tips: {prediction.prevention_tips}."
    )
    stream = await anthropic_client.messages.create(
        model=anthropic_model,
        max_tokens=260,
        stream=True,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    async for event in stream:
        if event.type == "content_block_delta" and getattr(event.delta, "text", ""):
            yield event.delta.text


async def _ai_chat_text_with_fallback(
    message: str,
    profile: Profile,
    prediction: RiskPrediction,
    location_aqi: dict,
) -> tuple[str | None, str]:
    if anthropic_client is not None:
        try:
            chunks: list[str] = []
            async for token in _ai_chat_stream(message, profile, prediction, location_aqi):
                chunks.append(token)
            text = "".join(chunks).strip()
            if text:
                return text, "anthropic"
        except Exception as exc:
            logger.warning("Anthropic chat fallback engaged: %s", exc)

    system = (
        "You are EcoVital Health Advisor. "
        "Answer based on the user's question and their risk context. "
        "Be concise, personalized, and actionable."
    )
    prompt = (
        f"Question: {message}\n"
        f"Current risk: {prediction.overall_score:.1f}/100 ({prediction.severity}).\n"
        f"AQI details: {location_aqi}.\n"
        f"Profile: age={profile.age}, conditions={profile.conditions}, medications={profile.medications}.\n"
        f"Reasons: {prediction.risk_reasons}.\n"
        f"Prevention tips: {prediction.prevention_tips}."
    )
    gemini_text = await _gemini_generate(system, prompt)
    if gemini_text:
        return gemini_text, "gemini"
    return None, "none"


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
    location_aqi = _location_aqi_details(lat, lng)
    try:
        ai_explanation = await asyncio.wait_for(
            _ai_risk_explanation_with_fallback(
                message="Explain the user's current score and what to do now.",
                profile=profile,
                prediction=pred,
                location_aqi=location_aqi,
            ),
            timeout=8,
        )
        if ai_explanation:
            pred.explanation = ai_explanation
    except asyncio.TimeoutError:
        logger.warning("AI explanation timed out – returning local explanation")
    except Exception as exc:
        logger.warning("AI explanation failed – returning local explanation: %s", exc)
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
    location_aqi = _location_aqi_details(body.lat, body.lng)
    community_reports.append(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "lat": body.lat,
            "lng": body.lng,
            "symptoms": body.symptoms,
            "severity": body.severity,
            "location_aqi": location_aqi,
        }
    )
    return {
        "success": True,
        "message": "Thank you for reporting",
        "location_aqi": location_aqi,
    }


@app.get("/api/location/aqi")
async def location_aqi(lat: float = Query(...), lng: float = Query(...)):
    return _location_aqi_details(lat, lng)


@app.get("/api/chat/stream")
async def chat_stream(user_id: str = Query(...), message: str = Query(...)):
    async def event_generator():
        profile = profiles.get(user_id, Profile())
        prediction = _calc_risk(profile.location_lat, profile.location_lng, profile)
        location_aqi = _location_aqi_details(profile.location_lat, profile.location_lng)
        ai_text, provider = await _ai_chat_text_with_fallback(
            message, profile, prediction, location_aqi
        )
        if ai_text:
            logger.info("Chat provider: %s", provider)
            for token in ai_text.split(" "):
                yield {"event": "token", "data": token + " "}
                await asyncio.sleep(0.02)
        else:
            text = _chat_reply(message, profile, prediction)
            logger.info("Chat provider: local_fallback")
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


@app.on_event("startup")
async def startup() -> None:
    global anthropic_client, anthropic_model, gemini_enabled, gemini_model, gemini_api_key
    logging.basicConfig(level=logging.INFO)

    backend_dir = Path(__file__).resolve().parents[1]
    root_dir = backend_dir.parent
    load_dotenv(root_dir / ".env", override=False)
    load_dotenv(backend_dir / ".env", override=False)
    # Local dev fallback if user populated only .env.example.
    load_dotenv(root_dir / ".env.example", override=False)
    load_dotenv(backend_dir / ".env.example", override=False)

    anthropic_model = os.getenv("ANTHROPIC_MODEL", anthropic_model)
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if api_key.startswith("sk-ant-"):
        anthropic_client = AsyncAnthropic(api_key=api_key)
        logger.info("Anthropic enabled with model: %s", anthropic_model)
    else:
        anthropic_client = None
        logger.warning(
            "Anthropic disabled: missing/invalid ANTHROPIC_API_KEY. Chat will use local fallback."
        )

    gemini_model = os.getenv("GEMINI_MODEL", gemini_model)
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_api_key:
        gemini_enabled = True
        logger.info("Gemini enabled with model: %s", gemini_model)
    else:
        gemini_enabled = False
        logger.warning("Gemini disabled: missing GEMINI_API_KEY.")
