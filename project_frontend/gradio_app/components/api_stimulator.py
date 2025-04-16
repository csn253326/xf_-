import asyncio
from fastapi import FastAPI, WebSocket
import cv2
from fastapi.websockets import WebSocket, WebSocketDisconnect
app = FastAPI()
import random
from datetime import datetime
import numpy as np


def generate_mock_data(
        frame_shape: tuple = (480, 640, 3),
        model_type: str = "gender"
) -> list:
    """生成与YOLO输出结构兼容的模拟检测数据

    Args:
        frame_shape: 输入视频帧维度 (h, w, c)
        model_type: 模型类型 ['gender', 'age']

    Returns:
        包含虚拟检测结果的字典列表
    """
    h, w, _ = frame_shape
    timestamp = datetime.now().isoformat()

    # 生成1-3个随机检测框
    return [{
        "bbox": [
            random.randint(0, w // 2),  # x_min
            random.randint(0, h // 2),  # y_min
            random.randint(w // 2, w),  # x_max
            random.randint(h // 2, h)  # y_max
        ],
        "confidence": round(random.uniform(0.65, 0.95), 2),
        "label": "male" if model_type == "gender" else str(random.randint(18, 70)),
        "track_id": random.randint(1000, 9999),  # 虚拟跟踪ID
        "timestamp": timestamp,
        "frame_hash": hash(np.random.bytes(16))  # 模拟帧特征指纹
    } for _ in range(random.randint(1, 3))]

# 模拟YOLO输出（后续替换为真实模型）
def mock_yolo_detection(frame, model_type):
    # 生成随机检测框
    h, w = frame.shape[:2]
    return [{
        "bbox": [int(w * 0.2), int(h * 0.2), int(w * 0.4), int(h * 0.4)],
        "confidence": np.random.uniform(0.7, 0.9),
        "label": "male" if model_type == "gender" else str(np.random.randint(20, 60))
    }]


@app.websocket("/api/v1/detect/{model_type}")
async def video_stream(websocket: WebSocket, model_type: str):
    await websocket.accept()
    while True:
        data = await websocket.receive_bytes()

        # 转换字节为OpenCV格式
        nparr = np.frombuffer(data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 模拟处理延迟
        await asyncio.sleep(0.05)

        # 返回模拟结果
        results = mock_yolo_detection(frame, model_type)
        await websocket.send_json(results)

app = FastAPI()


# 模拟YOLO输出（后续替换为真实模型）
def mock_yolo_detection(frame, model_type):
    # 生成随机检测框
    h, w = frame.shape[:2]
    return [{
        "bbox": [int(w * 0.2), int(h * 0.2), int(w * 0.4), int(h * 0.4)],
        "confidence": np.random.uniform(0.7, 0.9),
        "label": "male" if model_type == "gender" else str(np.random.randint(20, 60))
    }]


@app.websocket("/api/v1/detect/{model_type}")
async def video_stream(websocket: WebSocket, model_type: str):
    await websocket.accept()
    while True:
        data = await websocket.receive_bytes()

        # 转换字节为OpenCV格式
        nparr = np.frombuffer(data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 模拟处理延迟
        await asyncio.sleep(0.05)

        # 返回模拟结果
        results = mock_yolo_detection(frame, model_type)
        await websocket.send_json(results)

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            frame_bytes = await websocket.receive_bytes()

            # 压缩优化（质量参数调整）
            compressed_frame = cv2.imdecode(
                np.frombuffer(frame_bytes, np.uint8),
                cv2.IMREAD_COLOR
            )
            _, jpeg = cv2.imencode('.jpg', compressed_frame,
                                   [int(cv2.IMWRITE_JPEG_QUALITY), 70])

            # 模拟处理延迟
            await asyncio.sleep(0.05)
            await websocket.send_json({
                "results": generate_mock_data(),
                "compressed_frame": jpeg.tobytes()
            })
    except WebSocketDisconnect as e:
        print(f"WS连接关闭: code={e.code}")
    except Exception as e:
        print(f"未处理异常: {e.__class__.__name__}: {str(e)}")
    finally:
        await websocket.close()