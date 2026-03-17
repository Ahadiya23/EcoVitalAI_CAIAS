import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text

logger = logging.getLogger(__name__)


def build_scheduler(app) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    @scheduler.scheduled_job("interval", minutes=10)
    async def process_alerts() -> None:
        session_factory = app.state.session_factory
        data_service = app.state.data_service
        predictor = app.state.risk_predictor
        async with session_factory() as session:
            alerts_result = await session.execute(text("select * from alerts where active = true"))
            alerts = alerts_result.mappings().all()
            for alert in alerts:
                profile_result = await session.execute(
                    text("select * from health_profiles where user_id = cast(:user_id as uuid)"),
                    {"user_id": str(alert["user_id"])},
                )
                profile = profile_result.mappings().first()
                if not profile:
                    continue
                from app.models.schemas import UserProfile

                profile_model = UserProfile(
                    user_id=str(alert["user_id"]),
                    conditions=profile["conditions"] or [],
                    age=profile["age"],
                    location_lat=profile["location_lat"],
                    location_lng=profile["location_lng"],
                    medications=profile["medications"] or [],
                )
                snapshot = await data_service.aggregate_environmental_snapshot(
                    profile_model.location_lat, profile_model.location_lng
                )
                prediction = predictor.predict(
                    data_service.compute_feature_vector(snapshot, profile_model)
                )
                if prediction.overall_score >= alert["threshold"]:
                    logger.info(
                        "Alert threshold reached",
                        extra={
                            "user_id": str(alert["user_id"]),
                            "score": prediction.overall_score,
                            "threshold": alert["threshold"],
                        },
                    )
    return scheduler
