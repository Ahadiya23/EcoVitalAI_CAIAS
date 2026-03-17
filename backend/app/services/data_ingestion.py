import asyncio
import json
import logging
from datetime import datetime
from typing import Any

import numpy as np
from redis.asyncio import Redis
from tenacity import retry, stop_after_attempt, wait_exponential

from app.models.schemas import (
    AQIData,
    ClimateData,
    EnvironmentalSnapshot,
    PollenData,
    UVData,
    UserProfile,
)

logger = logging.getLogger(__name__)


class EnvironmentalDataService:
    def __init__(self, client: Any, redis_client: Redis, api_keys: dict[str, str]):
        self.client = client
        self.redis = redis_client
        self.api_keys = api_keys

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def fetch_climate_data(self, lat: float, lng: float) -> ClimateData:
        response = await self.client.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "lat": lat,
                "lon": lng,
                "units": "metric",
                "appid": self.api_keys.get("openweather", ""),
            },
        )
        response.raise_for_status()
        data = response.json()
        return ClimateData(
            temp_celsius=float(data.get("main", {}).get("temp", 0)),
            humidity_pct=float(data.get("main", {}).get("humidity", 0)),
            wind_speed=float(data.get("wind", {}).get("speed", 0)),
            weather_description=str(
                (data.get("weather") or [{}])[0].get("description", "unknown")
            ),
            feels_like=float(data.get("main", {}).get("feels_like", 0)),
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def fetch_aqi_data(self, lat: float, lng: float) -> AQIData:
        url = f"https://api.waqi.info/feed/geo:{lat};{lng}/"
        response = await self.client.get(
            url,
            params={"token": self.api_keys.get("waqi", "")},
        )
        response.raise_for_status()
        payload = response.json().get("data", {})
        iaqi = payload.get("iaqi", {})
        return AQIData(
            aqi_score=float(payload.get("aqi", 0) or 0),
            pm25=float((iaqi.get("pm25") or {}).get("v", 0)),
            pm10=float((iaqi.get("pm10") or {}).get("v", 0)),
            o3=float((iaqi.get("o3") or {}).get("v", 0)),
            no2=float((iaqi.get("no2") or {}).get("v", 0)),
            dominant_pollutant=str(payload.get("dominentpol", "unknown")),
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def fetch_uv_data(self, lat: float, lng: float) -> UVData:
        response = await self.client.get(
            "https://api.openuv.io/api/v1/uv",
            params={"lat": lat, "lng": lng},
            headers={"x-access-token": self.api_keys.get("openuv", "")},
        )
        response.raise_for_status()
        result = response.json().get("result", {})
        uv_index = float(result.get("uv", 0))
        if uv_index >= 8:
            level = "very_high"
        elif uv_index >= 6:
            level = "high"
        elif uv_index >= 3:
            level = "moderate"
        else:
            level = "low"
        return UVData(
            uv_index=uv_index,
            uv_max=float(result.get("uv_max", uv_index)),
            uv_max_time=str(result.get("uv_max_time", "")),
            uv_risk_level=level,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def fetch_pollen_data(self, lat: float, lng: float) -> PollenData:
        response = await self.client.get(
            "https://api.ambeedata.com/latest/pollen/by-lat-lng",
            params={"lat": lat, "lng": lng},
            headers={"x-api-key": self.api_keys.get("ambee", "")},
        )
        response.raise_for_status()
        data = (response.json().get("data") or [{}])[0]
        count = data.get("Count", {})
        tree = float(count.get("tree_pollen", 0))
        grass = float(count.get("grass_pollen", 0))
        weed = float(count.get("weed_pollen", 0))
        max_value = max(tree, grass, weed)
        if max_value >= 75:
            risk = "high"
        elif max_value >= 40:
            risk = "moderate"
        else:
            risk = "low"
        return PollenData(
            tree_pollen=tree,
            grass_pollen=grass,
            weed_pollen=weed,
            risk_level=risk,
        )

    async def _load_cached_snapshot(self, cache_key: str) -> EnvironmentalSnapshot | None:
        cached = await self.redis.get(cache_key)
        if not cached:
            return None
        return EnvironmentalSnapshot.model_validate_json(cached)

    async def aggregate_environmental_snapshot(
        self, lat: float, lng: float
    ) -> EnvironmentalSnapshot:
        cache_key = f"env:{lat:.4f}:{lng:.4f}"
        cached = await self._load_cached_snapshot(cache_key)
        if cached:
            return cached

        coroutines = [
            self.fetch_climate_data(lat, lng),
            self.fetch_aqi_data(lat, lng),
            self.fetch_uv_data(lat, lng),
            self.fetch_pollen_data(lat, lng),
        ]
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        fallback = cached or EnvironmentalSnapshot(lat=lat, lng=lng)
        climate = fallback.climate
        aqi = fallback.aqi
        uv = fallback.uv
        pollen = fallback.pollen

        for item in results:
            if isinstance(item, Exception):
                logger.warning("API call failed, using fallback", exc_info=item)
                continue
            if isinstance(item, ClimateData):
                climate = item
            elif isinstance(item, AQIData):
                aqi = item
            elif isinstance(item, UVData):
                uv = item
            elif isinstance(item, PollenData):
                pollen = item

        snapshot = EnvironmentalSnapshot(
            timestamp=datetime.utcnow(),
            lat=lat,
            lng=lng,
            climate=climate,
            aqi=aqi,
            uv=uv,
            pollen=pollen,
        )
        await self.redis.set(cache_key, snapshot.model_dump_json(), ex=600)
        return snapshot

    def compute_feature_vector(
        self, snapshot: EnvironmentalSnapshot, profile: UserProfile
    ) -> np.ndarray:
        conditions_lower = {condition.lower() for condition in profile.conditions}
        has_asthma = 1 if any("asthma" in c or "copd" in c for c in conditions_lower) else 0
        has_cardiac = 1 if any("heart" in c or "cardiac" in c for c in conditions_lower) else 0
        has_allergies = 1 if any("allerg" in c for c in conditions_lower) else 0

        now = datetime.utcnow()
        vector = np.array(
            [
                snapshot.aqi.aqi_score,
                snapshot.aqi.pm25,
                snapshot.aqi.pm10,
                snapshot.aqi.o3,
                snapshot.aqi.no2,
                snapshot.climate.temp_celsius,
                snapshot.climate.humidity_pct,
                snapshot.uv.uv_index,
                snapshot.pollen.tree_pollen,
                snapshot.pollen.grass_pollen,
                snapshot.pollen.weed_pollen,
                snapshot.climate.wind_speed,
                float(profile.age),
                float(has_asthma),
                float(has_cardiac),
                float(has_allergies),
                float(now.hour),
                float(now.weekday()),
            ],
            dtype=np.float32,
        )
        return vector
