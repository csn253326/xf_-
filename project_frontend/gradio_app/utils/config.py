# gradio_app/utils/config.py

from typing import Dict

class AppConfig:
    # ===================== 网络配置 =====================
    BACKEND_HOST: str = "localhost"
    BACKEND_PORT: int = 8000
    API_ENDPOINTS: Dict[str, str] = {
        "gender_detection": "/api/v1/video/stream"
    }

    # ===================== JWT 配置 =====================
    JWT_SECRET_KEY: str = "your-256-bit-secret"  # 必须与后端完全一致
    JWT_ALGORITHM: str = "HS256"                # 保持默认算法
    JWT_ISSUER: str = "face-recognition-auth"   # 签发者需匹配
    JWT_AUDIENCE: str = "video-stream-service"  # 受众需匹配
    JWT_EXPIRE_MINUTES: int = 30                # 新增有效期配置

    # ===================== 客户端配置 =====================
    CLIENT_ID: str = "gradio-client"            # 建议与后端白名单一致
    WS_RECONNECT_TIMEOUT: int = 5               # 连接超时时间（秒）
