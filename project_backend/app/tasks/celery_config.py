# app\tasks\celery_config.py
from celery import Celery
from project_backend.app.config.settings import settings

# ------------------------- 基础配置 -------------------------
app = Celery(
    "vision_tasks",
    broker=settings.BROKER_URL,
    backend=settings.RESULT_BACKEND,
    include=["app.tasks.process_tasks"],
    broker_connection_retry=True
)

# ------------------------- 高级配置 -------------------------
app.conf.update(
    # 序列化配置
    task_serializer="pickle",
    result_serializer="pickle",
    accept_content=["pickle", "json"],

    # 队列路由
    task_routes={
        "app.tasks.process_tasks.edge_detection_task": {
            "queue": "vision_high_priority"
        },
        "app.tasks.process_tasks.*": {"queue": "vision_default"}
    },

    # 可靠性配置
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,

    # 性能优化
    worker_prefetch_multiplier=1,  # 公平调度
    worker_max_tasks_per_child=100,  # 防止内存泄漏
    task_compression="zlib",

    # 监控集成
    worker_send_task_events=True,
    event_queue_expires=60,

    # 定时任务配置（示例）
    beat_schedule={
        "clean_temp_files": {
            "task": "app.tasks.maintenance.clean_temp_files",
            "schedule": 3600.0,  # 每小时执行
            "options": {"queue": "system_maintenance"}
        }
    }
)

# ------------------------- 环境覆盖 -------------------------
if settings.DEBUG_MODE:
    # 开发环境优化配置
    app.conf.update(
        worker_concurrency=2,
        task_always_eager=False,
        broker_pool_limit=None
    )
else:
    # 生产环境强化配置
    app.conf.update(
        worker_concurrency=settings.CELERY_WORKERS * 2,
        broker_connection_max_retries=3,
        result_chord_retry_interval=10
    )