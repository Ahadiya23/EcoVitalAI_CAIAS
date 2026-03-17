import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import text

router = APIRouter(tags=["ws"])


@router.websocket("/ws/risk-feed/{user_id}")
async def risk_feed(websocket: WebSocket, user_id: str):
    await websocket.accept()
    session_factory = websocket.app.state.session_factory
    data_service = websocket.app.state.data_service
    predictor = websocket.app.state.risk_predictor
    try:
        async with session_factory() as session:
            profile_result = await session.execute(
                text("select * from health_profiles where user_id = cast(:user_id as uuid)"),
                {"user_id": user_id},
            )
            profile = profile_result.mappings().first()
            if not profile:
                await websocket.send_json({"error": "Profile not found"})
                await websocket.close()
                return
            while True:
                snapshot = await data_service.aggregate_environmental_snapshot(
                    profile["location_lat"], profile["location_lng"]
                )
                from app.models.schemas import UserProfile

                profile_model = UserProfile(
                    user_id=user_id,
                    conditions=profile["conditions"] or [],
                    age=profile["age"],
                    location_lat=profile["location_lat"],
                    location_lng=profile["location_lng"],
                    medications=profile["medications"] or [],
                )
                prediction = predictor.predict(
                    data_service.compute_feature_vector(snapshot, profile_model)
                )
                await websocket.send_json(prediction.model_dump())
                await asyncio.sleep(300)
    except WebSocketDisconnect:
        return
