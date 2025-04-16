# 复用构建阶段
FROM docker/app.Dockerfile as builder

# --------------------------
# 生产运行阶段
# --------------------------
FROM python:3.11-slim-bookworm as production

WORKDIR /app
ENV CELERY_BROKER_URL=redis://redis:6379/0 \
    CELERY_RESULT_BACKEND=redis://redis:6379/1 \
    CELERY_WORKER_PREFETCH_MULTIPLIER=4 \
    OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/app ./app
COPY --from=builder /app/scripts ./scripts

USER appuser

# 启动命令（启用3.11的性能模式）
CMD ["celery", "-A", "app.tasks", "worker", \
     "--loglevel=info", \
     "--pool=prefork", \
     "--concurrency=8", \
     "--without-gossip", \
     "--optimize=3"]