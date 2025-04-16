# app/utils/metrics.py
from prometheus_client import (
    Gauge,
    Counter,
    Histogram,
    start_http_server,
    CollectorRegistry
)
from typing import Literal
from threading import Lock


class PrometheusMonitor:
    """
    增强版监控指标收集器

    特性：
    1. 线程安全：所有指标操作原子化
    2. 单例模式：全局唯一实例
    3. 动态端口：支持运行时端口切换
    """
    _instance = None
    _lock = Lock()
    _server_started = False

    def __new__(cls, port: int = 8001):
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_metrics(port)
        return cls._instance

    def _init_metrics(self, port: int):
        """初始化指标和HTTP服务"""
        self.registry = CollectorRegistry()
        self._define_metrics()

        if not self.__class__._server_started:
            start_http_server(port, registry=self.registry)
            self.__class__._server_started = True

    def _define_metrics(self):
        """定义所有监控指标"""
        # ----------------- 连接指标 -----------------
        self.active_connections = Gauge(
            'video_active_connections',
            '当前活跃视频流连接数',
            ['protocol'],
            registry=self.registry
        )

        # ----------------- 性能指标 -----------------
        self.processing_latency = Histogram(
            'video_processing_latency_seconds',
            '视频处理阶段延迟分布',
            ['phase'],
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 10, '+Inf'),
            registry=self.registry
        )

        # ----------------- 流量控制指标 -----------------
        self.limiter_decisions = Counter(
            'video_limiter_decisions_total',
            '限流器决策统计',
            ['limiter_type', 'action'],
            registry=self.registry
        )

        # ----------------- 带宽指标 -----------------
        self.bandwidth_usage = Gauge(
            'video_bandwidth_usage_bytes',
            '实时带宽使用量',
            ['client_id', 'direction'],
            registry=self.registry
        )

        # ----------------- 质量指标 -----------------
        self.quality_changes = Counter(
            'video_quality_adjustments_total',
            '视频质量调整事件',
            ['client_id', 'action', 'reason'],
            registry=self.registry
        )

    # ----------------- 线程安全操作 -----------------
    def increment_connection(self, protocol: str = "websocket"):
        """原子化增加连接数"""
        with self._lock:
            self.active_connections.labels(protocol=protocol).inc()

    def decrement_connection(self, protocol: str = "websocket"):
        """原子化减少连接数"""
        with self._lock:
            self.active_connections.labels(protocol=protocol).dec()

    def record_limiter_decision(self, limiter_type: str, allowed: bool):
        """记录限流器决策结果"""
        action = "allowed" if allowed else "denied"
        self.limiter_decisions.labels(
            limiter_type=limiter_type,
            action=action
        ).inc()

    def record_bandwidth(self, client_id: str, bytes: int, direction: Literal['in', 'out']):
        """记录带宽使用（输入/输出）"""
        self.bandwidth_usage.labels(
            client_id=client_id,
            direction=direction
        ).set(bytes)

    def record_processing_latency(self, phase: str, latency_seconds: float):
        """记录处理延迟"""
        self.processing_latency.labels(
            phase=phase
        ).observe(latency_seconds)

    def record_quality_change(self, client_id: str, action: str, reason: str):
        """记录质量调整事件"""
        self.quality_changes.labels(
            client_id=client_id,
            action=action,
            reason=reason
        ).inc()


# 全局单例（默认端口8001）
monitor = PrometheusMonitor()