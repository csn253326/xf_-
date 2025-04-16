# \app\settings.py
"""
项目配置中心（适配 Pydantic v2 规范）
"""
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from project_backend.app.ml_models.convert_pt_to_onnx import BASE_DIR

class Settings(BaseSettings):
    # ===================== 基础配置 =====================
    API_VERSION: str = Field(
        default="1.3.0",
        description="API版本号，遵循语义化版本规范"
    )

    DEBUG_MODE: bool = Field(
        default=False,
        description="调试模式开关（生产环境必须关闭）"
    )

    HOST: str = Field(
        default="0.0.0.0",
        description="服务监听地址（0.0.0.0表示监听所有接口）"
    )

    PORT: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="服务监听端口（1024-65535）"
    )

    UVICORN_WORKERS: int = Field(
        default=1,
        gt=0,
        description="工作进程数（建议设为 CPU 核数*2+1）"
    )

    # ===================== 安全配置 =====================
    JWT_SECRET_KEY: str = Field(
        default="your-256-bit-secret"
    )

    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT签名算法（推荐HS256/RS256）"
    )

    JWT_EXPIRE_MINUTES: int = Field(
        default=30,
        gt=0,
        description="JWT令牌有效期（分钟）"
    )

    JWT_ISSUER:str = "face-recognition-auth"

    JWT_AUDIENCE:str = "video-stream-service"


    ALLOWED_CLIENTS: List[str] = Field(
        default=["gradio-client"],
        description="允许的客户端列表"
    )

    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000",
                 "http://localhost:7860"],
        description="允许的跨域请求来源列表"
    )

    # ===================== 数据库配置 =====================
    DATABASE_URL: str = Field(
        default="mysql+asyncmy://root:ZGYD10086@localhost:3306/sys?charset=utf8mb4",
        description="MySQL连接URL"
    )
    DB_USE_SSL: bool = Field(
        default=False,
        description="是否启用SSL数据库连接"
    )
    # ===================== 文件处理配置 =====================
    MAX_FPS: int = 30
    MAX_CONNECTIONS: int = 100
    MAX_CONCURRENT_STREAMS: int = 100  # 最大并发流数量
    MAX_FRAME_SIZE: int = Field(
        default=1024 * 1024,  # 1MB
        gt=0,
        description="允许上传的最大帧尺寸（字节）"
    )
    MAX_BANDWIDTH_MBPS: float = Field(
        default=10.0,
        gt=0,
        description="最大带宽（Mbps）"
    )
    MAX_FILE_SIZE: int = Field(
        default=8 * 1024 * 1024,  # 8MB
        gt=0,
        description="允许上传的最大文件尺寸（字节）"
    )

    ALLOWED_IMAGE_TYPES: List[str] = Field(
        default=["image/jpeg", "image/png", "image/webp"],
        description="允许上传的图片MIME类型"
    )

    # ===================== 模型配置 =====================
    MODEL_PATH: str = Field(
        default=str(Path(__file__).parent.parent / "ml_models/model_weights/gender.pt"),
        description="模型文件绝对路径"
    )

    MODEL_INPUT_SIZE: tuple = Field(
        default=(224, 224),
        description="模型输入尺寸（高度, 宽度）"
    )

    USE_MOCK_MODEL: bool = Field(
        default=False,
        description="是否使用模拟模型（开发调试用）"
    )

    CLASS_LABELS: List[str] = Field(
        default=["male", "female"],
        min_items=2,
        description="分类标签列表"
    )

    MODEL_SHA256: str = Field(
        default="14b0a93a5edd0bdcd89523239d7bdeacdf355e98878f81d6360eb68e4701fe73",
        min_length=64,
        max_length=64,
        description="模型文件SHA256校验值"
    )

    MODEL_CHECK_ENABLED: bool = Field(
        default=True,
        description="是否启用模型签名验证"
    )

    # ===================== Celery配置 =====================
    BROKER_URL: str = Field(
        default="redis://localhost:6379/0",
        description="消息代理连接地址"
    )

    RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/1",
        description="任务结果存储地址"
    )

    CELERY_WORKERS: int = Field(
        default=4,
        gt=0,
        description="工作进程数"
    )

    CELERY_TASK_TIMEOUT: int = Field(
        default=600,
        gt=0,
        description="任务超时时间（秒）"
    )

    # ===================== MinIO存储配置 =====================
    MINIO_ENDPOINT: str = Field(
        default="localhost:9000",
        description="MinIO服务器地址"
    )

    MINIO_ACCESS_KEY: str = Field(
        default="minioadmin",
        description="访问密钥"
    )

    MINIO_SECRET_KEY: str = Field(
        default="minioadmin",
        description="私有密钥"
    )

    MINIO_BUCKET: str = Field(
        default="user-uploads",
        description="默认存储桶名称"
    )

    # ===================== 联系人信息 =====================
    CONTACT_NAME: str = Field(
        default="kong Team",
        description="技术支持联系人"
    )

    CONTACT_EMAIL: Optional[str] = Field(
        default="2536854326@qq.com",
        description="联系邮箱（可选）"
    )

    # ===================== Pydantic配置 =====================
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    FORCE_CPU: bool = False  # 新增强制CPU模式配置

    LOG_LEVEL: str = "INFO"

settings = Settings()