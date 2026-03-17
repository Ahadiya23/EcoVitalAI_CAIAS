from datetime import datetime, timedelta

import numpy as np
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from scipy.stats import gaussian_kde
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db

router = APIRouter(prefix="/api/map", tags=["map"])


class CommunityReportRequest(BaseModel):
    lat: float
    lng: float
    symptoms: list[str]
    severity: str


@router.get("/heatmap")
async def get_heatmap(bbox: str, session: AsyncSession = Depends(get_db)):
    lat1, lng1, lat2, lng2 = [float(part) for part in bbox.split(",")]
    query = text(
        """
        select location_lat, location_lng
        from community_reports
        where location_lat between :lat_min and :lat_max
          and location_lng between :lng_min and :lng_max
          and timestamp >= :cutoff
        """
    )
    cutoff = datetime.utcnow() - timedelta(hours=48)
    result = await session.execute(
        query,
        {
            "lat_min": min(lat1, lat2),
            "lat_max": max(lat1, lat2),
            "lng_min": min(lng1, lng2),
            "lng_max": max(lng1, lng2),
            "cutoff": cutoff,
        },
    )
    points = np.array([(row[0], row[1]) for row in result.all()], dtype=float)
    if len(points) < 2:
        return {"type": "FeatureCollection", "features": [], "heat": []}

    kde = gaussian_kde(points.T)
    lat_grid = np.linspace(min(lat1, lat2), max(lat1, lat2), 30)
    lng_grid = np.linspace(min(lng1, lng2), max(lng1, lng2), 30)
    heat = []
    for lat in lat_grid:
        for lng in lng_grid:
            intensity = float(kde([[lat], [lng]])[0])
            heat.append({"lat": float(lat), "lng": float(lng), "intensity": intensity})
    max_intensity = max(item["intensity"] for item in heat) or 1.0
    for item in heat:
        item["intensity"] = item["intensity"] / max_intensity
    return {"type": "FeatureCollection", "features": [], "heat": heat}


@router.post("/report")
async def create_report(body: CommunityReportRequest, session: AsyncSession = Depends(get_db)):
    query = text(
        """
        insert into community_reports (timestamp, location_lat, location_lng, symptoms, severity)
        values (now(), :lat, :lng, :symptoms, :severity)
        """
    )
    await session.execute(
        query,
        {
            "lat": body.lat,
            "lng": body.lng,
            "symptoms": body.symptoms,
            "severity": body.severity,
        },
    )
    await session.commit()
    return {"success": True, "message": "Thank you for reporting"}
