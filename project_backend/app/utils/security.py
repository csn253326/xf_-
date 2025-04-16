# \app\utils\security.py
import jwt  # 来自 PyJWT
from jwt import PyJWTError as JWTError  # 重命名异常类
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, WebSocketException, status, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from project_backend.app.config.settings import settings

# ------------------------- HTTP API 认证 -------------------------
api_key_header = APIKeyHeader(name="X-API-Key")

async def validate_api_key(api_key: str = Depends(api_key_header)):
    """API Key 认证（HTTP 接口使用）"""
    if api_key != settings.API_KEY:
        # 安全优化：不返回具体错误信息
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

# ------------------------- WebSocket 认证 -------------------------
class WebsocketAuthError(WebSocketException):
    def __init__(self, code: int, reason: str):
        super().__init__(code=code, reason=f"AUTH: {reason}")

class TokenPayload(BaseModel):
    client_id: str
    scopes: list[str]
    exp: datetime
    iss: str | None = None  # 签发者
    aud: str | None = None  # 受众

def create_ws_token(client_id: str, scopes: list) -> str:
    required_scope = "video_stream"
    if required_scope not in scopes:
        scopes.append(required_scope)

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_EXPIRE_MINUTES
    )
    payload = {
        "client_id": client_id,
        "scopes": scopes,
        "exp": expire,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

async def validate_ws_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require_exp": True},
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER
        )
        token_data = TokenPayload(**payload)

        if datetime.now(timezone.utc) > token_data.exp:
            raise WebsocketAuthError(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Token expired"
            )

        if "video_stream" not in token_data.scopes:
            raise WebsocketAuthError(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Insufficient permissions"
            )

        if token_data.client_id not in settings.allowed_clients:
            raise WebsocketAuthError(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Unauthorized client"
            )

        return token_data

    except JWTError as e:
        raise WebsocketAuthError(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication failed"
        )
