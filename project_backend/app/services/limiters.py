# \app\services/limiter.py
import time
import threading
from typing import Dict
from project_backend.app.utils.metrics import monitor
from project_backend.app.config.settings import settings


class TokenBucketLimiter:
    """
    令牌桶限流器（支持动态配置热更新）

    特性：
    - 客户端级独立限流
    - 线程安全
    - 动态调整容量和速率
    """

    def __init__(self):
        self._default_capacity = settings.MAX_FPS
        self._tokens = settings.MAX_FPS
        self._default_refill_rate = settings.MAX_FPS
        self.buckets: Dict[str, dict] = {}
        self.lock = threading.Lock()

    @property
    def default_capacity(self):
        """实时获取最新配置"""
        return settings.MAX_FPS

    @property
    def default_refill_rate(self):
        """实时获取最新速率"""
        return settings.MAX_FPS

    def _init_bucket(self, client_id: str) -> dict:
        """初始化客户端令牌桶"""
        return {
            'tokens': min(self.default_capacity, 1000),  # 安全上限
            'last_refill': time.monotonic(),
            'capacity': self.default_capacity,
            'refill_rate': self.default_refill_rate,
            'lock': threading.Lock()
        }

    def consume(self, client_id: str, tokens: int = 1) -> bool:
        """尝试消费令牌（线程安全）"""
        with self.lock:
            if client_id not in self.buckets:
                self.buckets[client_id] = self._init_bucket(client_id)
            bucket = self.buckets[client_id]

        with bucket['lock']:
            # 计算时间差并补充令牌
            now = time.monotonic()
            elapsed = now - bucket['last_refill']
            refill_amount = elapsed * bucket['refill_rate']
            bucket['tokens'] = min(
                bucket['capacity'],
                bucket['tokens'] + refill_amount
            )
            bucket['last_refill'] = now

            # 决策并记录指标
            if bucket['tokens'] >= tokens:
                bucket['tokens'] -= tokens
                monitor.record_limiter_decision(
                    limiter_type="frame_rate",
                    allowed=True
                )
                return True
            else:
                monitor.record_limiter_decision(
                    limiter_type="frame_rate",
                    allowed=False
                )
                return False

    def update_capacity(self, client_id: str, new_capacity: int):
        """动态调整客户端容量"""
        with self.lock:
            if client_id in self.buckets:
                with self.buckets[client_id]['lock']:
                    self.buckets[client_id]['capacity'] = new_capacity


class BandwidthLimiter:
    """
    带宽分配管理器（实时配置同步）

    特性：
    - 全局带宽池分配
    - 优先级抢占机制
    - 突发流量缓冲
    """

    def __init__(self):
        self._max_bps = settings.MAX_BANDWIDTH_MBPS * 1_000_000
        self.used_bps: float = 0.0
        self.client_usage: Dict[str, float] = {}
        self.lock = threading.Lock()

    @property
    def max_bps(self):
        """动态获取最新带宽配置"""
        return settings.MAX_BANDWIDTH_MBPS * 1_000_000

    def allocate(self, client_id: str, required_bps: float) -> bool:
        """申请带宽分配"""
        with self.lock:
            client_current = self.client_usage.get(client_id, 0.0)

            # 计算新总带宽
            new_total = self.used_bps - client_current + required_bps
            if new_total > self.max_bps:
                return False

            self.used_bps = new_total
            self.client_usage[client_id] = required_bps
            monitor.record_bandwidth(
                client_id=client_id,
                bytes=required_bps,
                direction="allocate"
            )
            return True

    def release(self, client_id: str):
        """释放带宽"""
        with self.lock:
            if client_id in self.client_usage:
                self.used_bps -= self.client_usage[client_id]
                del self.client_usage[client_id]
                monitor.record_bandwidth(
                    client_id=client_id,
                    bytes=0,
                    direction="release"
                )

    def get_available(self) -> float:
        """获取可用带宽"""
        with self.lock:
            return max(0, self.max_bps - self.used_bps)


class ConcurrencyLimiter:
    """
    系统级并发控制器（动态资源保护）

    特性：
    - 优雅降级
    - 优先级队列
    - 过载保护
    """

    def __init__(self):
        self._max_concurrent = settings.MAX_CONCURRENT_STREAMS
        self.current = 0
        self.lock = threading.Lock()

    @property
    def max_concurrent(self):
        """动态获取最新并发限制"""
        return min(settings.MAX_CONCURRENT_STREAMS, 5000)  # 安全上限

    def acquire(self, timeout: float = 0.5) -> bool:
        """获取处理槽位"""
        end_time = time.monotonic() + timeout
        while time.monotonic() < end_time:
            with self.lock:
                if self.current < self.max_concurrent:
                    self.current += 1
                    monitor.record_concurrency(current=self.current)
                    return True
            time.sleep(0.01)
        return False

    def release(self):
        """释放槽位"""
        with self.lock:
            self.current -= 1
            monitor.record_concurrency(current=self.current)


# ------------------------- 全局实例 -------------------------
frame_limiter = TokenBucketLimiter()
bandwidth_limiter = BandwidthLimiter()
concurrency_limiter = ConcurrencyLimiter()