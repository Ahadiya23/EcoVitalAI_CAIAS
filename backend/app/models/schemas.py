from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ClimateData(BaseModel):
    temp_celsius: float = 0
    humidity_pct: float = 0
    wind_speed: float = 0
    weather_description: str = "unknown"
    feels_like: float = 0


class AQIData(BaseModel):
    aqi_score: float = 0
    pm25: float = 0
    pm10: float = 0
    o3: float = 0
    no2: float = 0
    dominant_pollutant: str = "unknown"


class UVData(BaseModel):
    uv_index: float = 0
    uv_max: float = 0
    uv_max_time: str = ""
    uv_risk_level: str = "low"


class PollenData(BaseModel):
    tree_pollen: float = 0
    grass_pollen: float = 0
    weed_pollen: float = 0
    risk_level: str = "low"


class EnvironmentalSnapshot(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    lat: float
    lng: float
    climate: ClimateData = Field(default_factory=ClimateData)
    aqi: AQIData = Field(default_factory=AQIData)
    uv: UVData = Field(default_factory=UVData)
    pollen: PollenData = Field(default_factory=PollenData)


class UserProfile(BaseModel):
    user_id: str
    conditions: list[str] = Field(default_factory=list)
    age: int
    location_lat: float
    location_lng: float
    medications: list[str] = Field(default_factory=list)


class FeatureVector(BaseModel):
    values: list[float] = Field(min_length=18, max_length=18)


class RiskPrediction(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    component_scores: dict[str, float]
    severity: Literal["low", "medium", "high", "critical"]
    confidence: float = Field(ge=0, le=1)
    anomaly_flag: bool = False
    explanation: str = ""
