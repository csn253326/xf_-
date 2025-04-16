# app/ml_models/video_processor.py
import cv2
import torch
import asyncio
import concurrent.futures
import numpy as np
from typing import Dict, Callable
from fastapi import WebSocketDisconnect

class VideoProcessor:
    """重构版视频处理器（支持管道注册与硬件加速）"""
    _pipelines: Dict[str, Callable] = {}  # 注册的处理管道
    _gpu_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    # === 类方法 ===
    @classmethod
    def register_pipeline(cls, name: str, processor_func: Callable):
        """注册视频处理管道（供model_manager调用）"""
        if not callable(processor_func):
            raise ValueError("处理器必须是可调用函数")
        cls._pipelines[name] = processor_func

    @classmethod
    def get_pipeline(cls, name: str) -> Callable:
        """获取注册的处理管道"""
        return cls._pipelines.get(name)

    # === 核心处理方法 ===
    @classmethod
    async def process_frame(cls, client_id: str, frame_data: bytes):
        """统一处理入口（网关调用）"""
        try:
            # 使用注册的管道处理
            if "gender" not in cls._pipelines:
                raise RuntimeError("未注册性别检测管道")

            # 异步调度处理
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                cls._gpu_executor,
                cls._process_gender_pipeline,
                frame_data
            )
        except WebSocketDisconnect:
            raise
        except Exception as e:
            return {"error": str(e)}

    # === 私有方法 ===
    @staticmethod
    def _process_gender_pipeline(frame_data: bytes):
        """性别检测管道处理逻辑"""
        # 解码帧数据
        frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)

        # 获取注册的处理器（来自model_manager）
        processor = VideoProcessor.get_pipeline("gender")
        if not processor:
            raise ValueError("性别检测处理器未注册")

        # 执行处理（注意：需在同步上下文中运行）
        return processor(frame)

    @staticmethod
    def _decode_frame(data: bytes):
        """解码帧数据（兼容方法）"""
        return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

    # === 硬件加速方法 ===
    @staticmethod
    def _gpu_preprocess(data: bytes) -> torch.Tensor:
        """GPU预处理（兼容旧代码）"""
        frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        return torch.from_numpy(frame).cuda().half() / 255.0  # 添加归一化

    @staticmethod
    def _gpu_postprocess(outputs) -> list:
        """GPU后处理（兼容旧代码）"""
        return outputs.cpu().numpy().tolist()
