import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger("expense_tracker.websocket")

active_connections: list[WebSocket] = []


@router.websocket("/ws")
async def websocket_handler(ws: WebSocket):
    await ws.accept()
    active_connections.append(ws)
    try:
        while True:
            data = await ws.receive_text()
            for conn in active_connections:
                await conn.send_text(data)
    except WebSocketDisconnect:
        logger.info("websocket.disconnected", extra={"operation": "websocket"})
