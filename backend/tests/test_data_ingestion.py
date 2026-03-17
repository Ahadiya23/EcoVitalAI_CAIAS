from unittest.mock import AsyncMock

import pytest

from app.models.schemas import UserProfile
from app.services.data_ingestion import EnvironmentalDataService


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    return redis


@pytest.fixture
def mock_client():
    client = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_aggregate_success(mock_client, mock_redis):
    responses = [
        {"main": {"temp": 30, "humidity": 55, "feels_like": 32}, "wind": {"speed": 4}, "weather": [{"description": "clear"}]},
        {"data": {"aqi": 80, "iaqi": {"pm25": {"v": 25}, "pm10": {"v": 40}, "o3": {"v": 20}, "no2": {"v": 14}}, "dominentpol": "pm25"}},
        {"result": {"uv": 6.2, "uv_max": 8.1, "uv_max_time": "2026-03-17T10:00:00Z"}},
        {"data": [{"Count": {"tree_pollen": 10, "grass_pollen": 22, "weed_pollen": 8}}]},
    ]
    mock_client.get.side_effect = [AsyncMock(json=lambda d=r: d, raise_for_status=lambda: None) for r in responses]
    service = EnvironmentalDataService(mock_client, mock_redis, {})
    snapshot = await service.aggregate_environmental_snapshot(12.9, 77.5)
    assert snapshot.aqi.aqi_score == 80
    assert snapshot.uv.uv_index == 6.2
    mock_redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_one_api_failure_fallback(mock_client, mock_redis):
    ok_response = AsyncMock(json=lambda: {"main": {"temp": 30, "humidity": 55, "feels_like": 32}, "wind": {"speed": 4}, "weather": [{"description": "clear"}]}, raise_for_status=lambda: None)
    fail_response = AsyncMock()
    fail_response.raise_for_status.side_effect = RuntimeError("boom")
    fail_response.json.return_value = {}
    mock_client.get.side_effect = [ok_response, fail_response, ok_response, ok_response]
    service = EnvironmentalDataService(mock_client, mock_redis, {})
    snapshot = await service.aggregate_environmental_snapshot(12.9, 77.5)
    assert snapshot.climate.temp_celsius == 30
    assert snapshot.aqi.aqi_score == 0


@pytest.mark.asyncio
async def test_cache_hit(mock_client, mock_redis):
    cached = (
        '{"timestamp":"2026-03-17T00:00:00","lat":1,"lng":2,'
        '"climate":{"temp_celsius":10,"humidity_pct":10,"wind_speed":1,"weather_description":"clear","feels_like":9},'
        '"aqi":{"aqi_score":20,"pm25":4,"pm10":5,"o3":3,"no2":2,"dominant_pollutant":"pm25"},'
        '"uv":{"uv_index":1,"uv_max":2,"uv_max_time":"x","uv_risk_level":"low"},'
        '"pollen":{"tree_pollen":1,"grass_pollen":2,"weed_pollen":3,"risk_level":"low"}}'
    )
    mock_redis.get.return_value = cached
    service = EnvironmentalDataService(mock_client, mock_redis, {})
    snapshot = await service.aggregate_environmental_snapshot(1, 2)
    assert snapshot.aqi.aqi_score == 20
    mock_client.get.assert_not_called()


def test_feature_vector_shape(mock_client, mock_redis):
    service = EnvironmentalDataService(mock_client, mock_redis, {})
    from app.models.schemas import EnvironmentalSnapshot

    snapshot = EnvironmentalSnapshot(lat=10, lng=20)
    profile = UserProfile(
        user_id="u1",
        conditions=["Asthma", "Seasonal Allergies"],
        age=32,
        location_lat=10,
        location_lng=20,
        medications=[],
    )
    vector = service.compute_feature_vector(snapshot, profile)
    assert vector.shape == (18,)
