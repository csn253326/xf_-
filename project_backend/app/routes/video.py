# app/routes/video.py
from fastapi import APIRouter, WebSocket, HTTPException
from jwt.exceptions import PyJWTError  # 修正导入方式
import jwt
from datetime import datetime, timezone
import base64
import json
import logging
import numpy as np
from ..ml_models.model_manager import stream_processor  # 正确导入流处理器
from ..config.settings import settings

router = APIRouter(prefix="/api/v1/video", tags=["Video Stream"])

# 配置校验
if not all([settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM]):
    logging.critical("JWT配置不完整")
    raise HTTPException(status_code=500, detail="JWT配置不完整")

async def verify_token(token: str):
    """增强版令牌验证"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER
        )
        return payload
    except PyJWTError as e:
        logging.warning(f"令牌验证失败: {str(e)}")
        raise HTTPException(status_code=403, detail=f"凭证验证失败: {str(e)}")
    except Exception as e:
        logging.error(f"令牌解析异常: {str(e)}")
        raise HTTPException(status_code=403, detail="无效令牌")

@router.websocket("/stream")
async def video_stream_endpoint(websocket: WebSocket):
    """增强版视频流处理端点"""
    await websocket.accept()
    client_id = "unknown"

    try:
        # ================= 认证阶段 =================
        auth_msg = await websocket.receive_text()
        try:
            msg_data = json.loads(auth_msg)
            if msg_data.get("type") != "auth":
                await websocket.send_json({"status": "error", "message": "需要先认证"})
                await websocket.close(code=1008)
                return

            # 验证JWT令牌
            payload = await verify_token(msg_data.get("token", ""))
            client_id = payload.get("client_id", "unknown")
            if "video_stream" not in payload.get("scopes", []):
                logging.warning(f"客户端 {client_id} 权限不足")
                await websocket.send_json({"status": "error", "message": "权限不足"})
                await websocket.close(code=1008)
                return

            await websocket.send_json({"status": "success", "client_id": client_id})
            logging.info(f"客户端 {client_id} 认证成功")

        except json.JSONDecodeError:
            await websocket.send_json({"status": "error", "message": "无效的JSON格式"})
            await websocket.close(code=1007)
            return

        # ================= 流处理阶段 =================
        while True:
            message = await websocket.receive()

            # 处理二进制数据
            if isinstance(message, bytes):
                frame_data = message
            else:
                try:
                    msg = json.loads(message)
                    if msg.get("type") == "frame":
                        frame_data = base64.b64decode(msg["data"])
                    else:
                        continue
                except Exception as e:
                    logging.warning(f"无效消息格式: {str(e)}")
                    continue

            try:
                # 使用流处理器处理原始字节
                results = await stream_processor.process_frame(frame_data)

                # 构建标准化响应
                response = {
                    "predictions": [
                        {
                            "label": pred["label"],
                            "confidence": pred["confidence"],
                            "bbox": [
                                float(pred["bbox"][0]),  # 使用原始坐标
                                float(pred["bbox"][1]),
                                float(pred["bbox"][2]),
                                float(pred["bbox"][3])
                            ]
                        } for pred in results
                    ],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await websocket.send_json(response)

            except Exception as e:
                logging.error(f"处理失败: {str(e)}", exc_info=True)
                await websocket.send_json({
                    "status": "error",
                    "message": f"处理失败: {str(e)}"
                })

    except Exception as e:
        logging.error(f"连接异常 ({client_id}): {str(e)}", exc_info=True)
    finally:
        await websocket.close()
        logging.info(f"连接关闭 ({client_id})")
