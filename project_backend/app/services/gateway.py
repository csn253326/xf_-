# \app\services\gateway.py
import asyncio
import time
import jwt
from fastapi import WebSocket, status
from threading import Lock
from typing import Dict, Tuple
from project_backend.app.config.settings import settings
from project_backend.app.utils.metrics import monitor  # 使用单例监控实例
from project_backend.app.services.quality_controller import DynamicQualityController
from project_backend.app.services.limiters import TokenBucketLimiter, BandwidthLimiter

from project_backend.app.ml_models.video_processor import VideoProcessor

class StreamGateway:
    """实时视频流控网关（监控集成优化版）"""

    def __init__(self):
        # 连接核心状态
        self.active_connections: Dict[str, Tuple[WebSocket, float]] = {}
        self.connection_lock = Lock()

        # 流量控制模块
        self.frame_limiter = TokenBucketLimiter(
            capacity=settings.MAX_FPS,
            refill_rate=settings.MAX_FPS
        )
        self.bandwidth_limiter = BandwidthLimiter(
            max_bps=settings.MAX_BANDWIDTH_MBPS * 1_000_000
        )

        # 质量调控模块
        self.quality_controller = DynamicQualityController()

        # 后台任务初始化
        self._init_background_tasks()

    def _init_background_tasks(self):
        """启动后台维护任务"""
        loop = asyncio.get_event_loop()
        loop.create_task(self._heartbeat_check())
        loop.create_task(self._report_system_metrics())

    async def manage_connection(self, websocket: WebSocket, client_id: str):
        """管理连接全生命周期"""
        if not await self._perform_handshake(websocket, client_id):
            return

        # 注册连接
        with self.connection_lock:
            self.active_connections[client_id] = (websocket, time.time())
            monitor.increment_connection()  # 线程安全计数

        try:
            while True:
                # 准入控制
                admission_result = self._check_admission(client_id)
                if not admission_result["allowed"]:
                    monitor.record_limiter_decision(
                        limiter_type=admission_result["type"],
                        allowed=False
                    )
                    continue

                # 接收帧数据
                frame_data, receive_time = await self._receive_frame(websocket)
                monitor.record_bandwidth(
                    client_id=client_id,
                    bytes=len(frame_data),
                    direction="in"
                )

                # 处理流水线
                start_time = time.time()
                processed = await self._processing_pipeline(client_id, frame_data)
                monitor.record_processing_latency(
                    phase="full_pipeline",
                    latency_seconds=time.time() - start_time
                )

                # 发送响应
                await self._send_response(websocket, processed)
                monitor.record_bandwidth(
                    client_id=client_id,
                    bytes=len(processed),
                    direction="out"
                )

        except Exception as e:
            monitor.record_processing_error()
            await self._safe_close(websocket, code=status.WS_1011_INTERNAL_ERROR)
        finally:
            with self.connection_lock:
                if client_id in self.active_connections:
                    del self.active_connections[client_id]
                    monitor.decrement_connection()

    async def _perform_handshake(self, websocket: WebSocket, client_id: str) -> bool:
        """安全握手协议（带监控）"""
        try:
            await websocket.accept()
            token = await websocket.receive_text()
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

            if payload.get('client_id') != client_id:
                raise ValueError("Client ID mismatch")

            if 'video_stream' not in payload.get('scopes', []):
                raise PermissionError("Insufficient privileges")

            await websocket.send_json({"status": "auth_success"})
            return True
        except jwt.ExpiredSignatureError:
            monitor.record_auth_failure(failure_type="expired")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False
        except Exception as e:
            monitor.record_auth_failure(failure_type="invalid")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False

    def _check_admission(self, client_id: str) -> dict:
        """综合准入检查（返回决策详情）"""
        # 帧率限制检查
        if not self.frame_limiter.consume(client_id, tokens=1):
            return {"allowed": False, "type": "frame_rate"}

        # 带宽配额检查
        if not self.bandwidth_limiter.check_quota(client_id):
            self.quality_controller.downgrade(client_id)
            monitor.record_quality_change(
                client_id=client_id,
                action="downgrade",
                reason="bandwidth_limit"
            )
            return {"allowed": False, "type": "bandwidth"}

        return {"allowed": True, "type": "passed"}

    async def _processing_pipeline(self, client_id: str, frame_data: bytes):
        """处理流水线（带详细监控）"""
        # 解码阶段
        decode_start = time.time()
        validated_frame = self._validate_frame(frame_data)
        monitor.record_processing_latency(
            phase="decode",
            latency_seconds=time.time() - decode_start
        )

        # 质量调整阶段
        adjust_start = time.time()
        adjusted_frame = self.quality_controller.adjust(client_id, validated_frame)
        monitor.record_processing_latency(
            phase="quality_adjust",
            latency_seconds=time.time() - adjust_start
        )

        # 推理处理阶段
        process_start = time.time()
        processed = await self._submit_to_processor(client_id, adjusted_frame)
        monitor.record_processing_latency(
            phase="inference",
            latency_seconds=time.time() - process_start
        )

        return await VideoProcessor.process_frame(client_id, frame_data)

    async def _submit_to_processor(self, client_id: str, frame_data: bytes) -> dict:
        """提交到处理集群（需集成实际逻辑）"""
        # 示例实现
        return {"result": "processed_data"}

    async def _heartbeat_check(self):
        """心跳检测（带连接状态监控）"""
        while True:
            await asyncio.sleep(settings.HEARTBEAT_INTERVAL)
            stale = []
            now = time.time()

            with self.connection_lock:
                for client_id, (ws, last_active) in self.active_connections.items():
                    if now - last_active > settings.CONNECTION_TIMEOUT:
                        stale.append(client_id)

                for client_id in stale:
                    await self._safe_close(self.active_connections[client_id][0])
                    del self.active_connections[client_id]
                    monitor.decrement_connection()
                    monitor.record_connection_duration(
                        duration=now - last_active,
                        client_type="stale"
                    )

    async def _report_system_metrics(self):
        """系统级指标上报"""
        while True:
            await asyncio.sleep(30)
            # 上报当前并发数
            with self.connection_lock:
                monitor.record_concurrency(
                    current=len(self.active_connections)
                )

    async def _safe_close(self, websocket: WebSocket, code: int = status.WS_1000_NORMAL_CLOSURE):
        """安全关闭连接（带连接时长统计）"""
        try:
            start_time = self.active_connections.get(id(websocket), (None, 0))[1]
            if start_time:
                monitor.record_connection_duration(
                    duration=time.time() - start_time,
                    client_type="normal"
                )
            await websocket.close(code=code)
        except Exception:
            pass


# 辅助类接口定义
class DynamicQualityController:
    def adjust(self, client_id: str, frame_data: bytes) -> bytes:
        """质量调整接口"""
        return frame_data


class BandwidthLimiter:
    def check_quota(self, client_id: str) -> bool:
        """带宽配额检查接口"""
        return True