# \app\routers\stream.py
from fastapi import WebSocket, status, APIRouter
from project_backend.app.utils.security import validate_ws_token
from project_backend.app.ml_models.video_processor import VideoProcessor

router = APIRouter(
    prefix="/stream",  # 独立路由前缀
    tags=["Realtime Streaming"],  # 新的OpenAPI分组
    responses={403: {"description": "Forbidden"}}
)
processor = VideoProcessor()

@router.websocket("/video-feed")
async def realtime_video_stream(websocket: WebSocket):
    # 认证握手
    await websocket.accept()
    try:
        token = await websocket.receive_text()
        user = await validate_ws_token(token)
    except Exception as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 实时处理循环
    try:
        while True:
            frame_data = await websocket.receive_bytes()
            result = await processor.async_process(frame_data)
            await websocket.send_json(result)
    except Exception as e:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)