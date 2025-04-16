# 构建阶段  3.11优化：使用官方3.11镜像
FROM python:3.11-slim-bookworm as builder

WORKDIR /app
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    POETRY_VERSION=1.7.0

# 安装系统依赖（新增psycopg2编译依赖）
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    libpq-dev \
    python3.11-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装poetry并配置虚拟环境
RUN pip install "poetry==$POETRY_VERSION"
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.in-project true \
    && poetry install --no-root --only main --no-ansi

# --------------------------
# 生产运行阶段
# --------------------------
FROM python:3.11-slim-bookworm as production

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPYCACHEPREFIX=/tmp/pycache \
    PYTHONOPTIMIZE=2

# 复制虚拟环境
COPY --from=builder /app/.venv ./.venv

# 复制应用代码（排除开发文件）
COPY ./app ./app
COPY ./scripts ./scripts
COPY alembic.ini .

# 配置非root用户
RUN useradd --no-create-home --uid 1001 appuser \
    && chown -R appuser:appuser /app
USER appuser

# 健康检查（兼容k8s探针）
HEALTHCHECK --interval=30s --timeout=5s \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

# 启动命令（利用3.11的TLS加速）
CMD ["gunicorn", "app.main:app", \
    "--bind", "0.0.0.0:8000", \
    "--workers", "4", \
    "--worker-class", "uvicorn.workers.UvicornH11Worker"]