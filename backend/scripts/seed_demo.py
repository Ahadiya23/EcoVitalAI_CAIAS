import asyncio
import math
import random
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url)

SCENARIOS = [
    {
        "name": "delhi",
        "email": "demo_delhi@ecovital.app",
        "lat": 28.6139,
        "lng": 77.2090,
        "base_score": 87,
        "conditions": ["Asthma", "Heart disease"],
        "age": 58,
    },
    {
        "name": "bangalore",
        "email": "demo_bangalore@ecovital.app",
        "lat": 12.9716,
        "lng": 77.5946,
        "base_score": 22,
        "conditions": ["Seasonal allergies"],
        "age": 32,
    },
    {
        "name": "mumbai",
        "email": "demo_mumbai@ecovital.app",
        "lat": 19.0760,
        "lng": 72.8777,
        "base_score": 74,
        "conditions": ["Heart disease"],
        "age": 67,
    },
]


async def seed() -> None:
    async with engine.begin() as conn:
        for scenario in SCENARIOS:
            user_id = str(uuid4())
            await conn.execute(
                text("insert into users (id, email) values (cast(:id as uuid), :email) on conflict (email) do nothing"),
                {"id": user_id, "email": scenario["email"]},
            )
            await conn.execute(
                text(
                    """
                    insert into health_profiles (user_id, conditions, age, location_lat, location_lng, medications, updated_at)
                    values (cast(:user_id as uuid), :conditions, :age, :lat, :lng, '{}', now())
                    on conflict (user_id) do update set
                    conditions = excluded.conditions,
                    age = excluded.age,
                    location_lat = excluded.location_lat,
                    location_lng = excluded.location_lng
                    """
                ),
                {
                    "user_id": user_id,
                    "conditions": scenario["conditions"],
                    "age": scenario["age"],
                    "lat": scenario["lat"],
                    "lng": scenario["lng"],
                },
            )
            now = datetime.now(timezone.utc)
            for hour in range(14 * 24):
                ts = now - timedelta(hours=hour)
                wave = math.sin((ts.hour / 24) * 2 * math.pi)
                score = max(0, min(100, scenario["base_score"] + wave * 8 + random.uniform(-4, 4)))
                await conn.execute(
                    text(
                        """
                        insert into risk_scores (id, user_id, timestamp, risk_score, risk_category, component_scores, explanation, anomaly_flag)
                        values (cast(:id as uuid), cast(:user_id as uuid), :timestamp, :risk_score, :risk_category, cast(:component_scores as jsonb), :explanation, false)
                        """
                    ),
                    {
                        "id": str(uuid4()),
                        "user_id": user_id,
                        "timestamp": ts,
                        "risk_score": score,
                        "risk_category": "critical" if score >= 80 else "high" if score >= 60 else "medium" if score >= 30 else "low",
                        "component_scores": {"asthma_risk": score / 100, "heat_risk": score / 120, "allergy_risk": score / 140, "cardiac_risk": score / 110},
                        "explanation": f"Demo scenario {scenario['name']} seeded.",
                    },
                )
            for _ in range(500):
                await conn.execute(
                    text(
                        """
                        insert into community_reports (id, timestamp, location_lat, location_lng, symptoms, severity)
                        values (cast(:id as uuid), now(), :lat, :lng, :symptoms, :severity)
                        """
                    ),
                    {
                        "id": str(uuid4()),
                        "lat": scenario["lat"] + random.uniform(-0.08, 0.08),
                        "lng": scenario["lng"] + random.uniform(-0.08, 0.08),
                        "symptoms": random.choice([["cough"], ["breathlessness"], ["fatigue"], ["headache"]]),
                        "severity": random.choice(["low", "medium", "high"]),
                    },
                )
            for idx in range(6):
                await conn.execute(
                    text(
                        """
                        insert into environmental_readings
                        (time, location_lat, location_lng, aqi, pm25, pm10, o3, no2, temperature, humidity, uv_index, tree_pollen, grass_pollen, weed_pollen, wind_speed)
                        values (:time, :lat, :lng, :aqi, :pm25, :pm10, :o3, :no2, :temperature, :humidity, :uv, :tree, :grass, :weed, :wind)
                        """
                    ),
                    {
                        "time": now - timedelta(hours=idx),
                        "lat": scenario["lat"],
                        "lng": scenario["lng"],
                        "aqi": scenario["base_score"] * 3,
                        "pm25": scenario["base_score"] * 2,
                        "pm10": scenario["base_score"] * 1.4,
                        "o3": scenario["base_score"] * 0.8,
                        "no2": scenario["base_score"] * 0.9,
                        "temperature": 20 + scenario["base_score"] / 4,
                        "humidity": 55 + random.uniform(-10, 10),
                        "uv": max(1, min(11, scenario["base_score"] / 10)),
                        "tree": random.uniform(5, 80),
                        "grass": random.uniform(5, 80),
                        "weed": random.uniform(5, 80),
                        "wind": random.uniform(1, 8),
                    },
                )
    print("Seed complete")


if __name__ == "__main__":
    asyncio.run(seed())
