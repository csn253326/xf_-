# \main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from project_backend.app.routes.vision import router as vision_router
from project_backend.app.routes.stream import router as stream_router
#from project_backend.app.database.base import init_db, close_db
from project_backend.app.ml_models.model_manager import startup_event, shutdown_event
from project_backend.app.ml_models.model_manager import model_manager
from project_backend.app.config.settings import settings
from project_backend.app.config.prometheus import init_monitoring
from project_backend.app.routes.video import router as video_router
import uvicorn
import logging


# ------------------------- 生命周期管理 -------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """统一管理关键资源生命周期"""
    try:
        # 服务启动初始化
        logging.info("Initializing resources...")
        #await init_db()  # 数据库连接池验证
        await startup_event()  # 初始化流处理器
        model_manager.load_model()  # 模型预加载
        yield
    finally:
        # 服务关闭清理
        logging.info("Releasing resources...")
        #await close_db()  # 关闭数据库连接池
        await shutdown_event()  # 关闭流处理器
        model_manager.release_model()  # 释放模型资源

# ------------------------- FastAPI应用实例 -------------------------
app = FastAPI(
    title="人脸识别与性别检测",
    description="提供图像分类和边缘检测API服务",
    version=settings.API_VERSION,
    contact={
        "name": settings.CONTACT_NAME,
        "email": settings.CONTACT_EMAIL
    },
    openapi_tags=[{
        "name": "Vision",
        "description": "图像处理接口",
    }],
    lifespan=lifespan
)

# ------------------------- 中间件配置 -------------------------
# CORS跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 安全响应头中间件
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers.update({
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY"
    })
    return response

# ------------------------- 监控与健康检查 -------------------------
# Prometheus指标监控
instrumentator = Instrumentator(
    excluded_handlers=["/health", "/docs", "/openapi.json"]
)
init_monitoring(app)

# 健康检查端点
@app.get("/health", include_in_schema=False)
async def health_check():
    """服务健康状态探针"""
    return {
        "status": "ok",
        "database": "connected" if model_manager.is_loaded() else "disconnected",
        "model_status": model_manager.get_model_status()
    }

# ------------------------- 服务信息端点 -------------------------
@app.get("/api/v1/service-info", tags=["Service Info"])
async def get_service_info():
    """返回服务基础信息（供前端动态构建请求地址）"""
    return {
        "service": app.title,
        "version": settings.API_VERSION,
        "environment": "development" if settings.DEBUG_MODE else "production",
        "base_url": f"http://{settings.HOST}:{settings.PORT}",
        "api_docs": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "available_endpoints": [
            {
                "name": "视频流处理",
                "path": "/api/v1/video/stream",
                "methods": ["WEBSOCKET"]
            },
            {
                "name": "图像分类接口",
                "path": "/api/v1/vision/classify",
                "methods": ["POST"]
            },
            {
                "name": "健康检查",
                "path": "/health",
                "methods": ["GET"]
            }
        ]
    }

# ------------------------- 路由注册 -------------------------
app.include_router(video_router)

app.include_router(
    vision_router,
    prefix="/api/v1/vision",  # 更明确的视觉服务路径
    tags=["Computer Vision"]
)

app.include_router(
    stream_router,
    prefix="/api/v1",  # 保持统一API版本前缀
    tags=["Streaming"]
)

# ------------------------- 启动配置 -------------------------
if __name__ == "__main__":
    uvicorn.run(
        app="project_backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG_MODE,
        log_level="info" if settings.DEBUG_MODE else "warning",
        timeout_graceful_shutdown=30,  # 优雅关闭超时时间
    )
