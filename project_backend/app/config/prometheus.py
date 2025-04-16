# \app\config\prometheus.py
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import Request
import time

# ------------------------- 监控指标定义 -------------------------
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP Requests",
    ["method", "endpoint", "status_code"]
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)

MODEL_LOAD_STATUS = Gauge(
    "model_load_status",
    "Current model load status (1=loaded, 0=error)",
    ["model_name"]
)

# ------------------------- 指标初始化 -------------------------
def init_monitoring(app):
    """集成Prometheus监控到FastAPI应用"""
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        excluded_handlers=["/health", "/metrics"]
    )

    # 中间件用于测量请求持续时间
    @app.middleware("http")
    async def add_request_duration(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        return response

    # 注册自定义指标
    instrumentator.add(
        "http_requests_total",
        REQUEST_COUNT,
        lambda req, res: {
            "method": req.method,
            "endpoint": req.url.path,
            "status_code": res.status_code
        }
    )

    # 挂载到应用
    instrumentator.instrument(app).expose(app)
