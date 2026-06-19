from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.platform.core.websockets import manager
from app.platform.observability.logging import logger
from app.api.dependencies.auth import get_current_user_ws

router = APIRouter()

@router.websocket("/stream")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    Establish a WebSocket connection for real-time updates.
    Expects `?token=JWT_TOKEN` in the URL.
    """
    user = await get_current_user_ws(token)
    if not user:
        await websocket.close(code=1008) # Policy Violation
        return

    await manager.connect(user.id, websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(user.id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(user.id, websocket)
