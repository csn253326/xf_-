# \app\database\models\task.py
from enum import Enum as PyEnum
from sqlalchemy import Column, JSON, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from project_backend.app.database.declarative_base import Base

class TaskStatus(str, PyEnum):
    """任务状态枚举（兼容PostgreSQL原生枚举）"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(Base):
    __tablename__ = "tasks"

    # UUID主键（PostgreSQL原生支持）
    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        index=True,
        server_default=func.uuid_generate_v4()  # 自动生成UUID
    )

    # 状态字段（显式声明枚举类型名称）
    status = Column(
        Enum(TaskStatus, name="task_status"),  # 定义数据库级枚举类型
        default=TaskStatus.PENDING,
        nullable=False
    )

    # 处理结果（存储JSON格式）
    result = Column(JSON, comment="模型处理结果")

    # 时间戳（自动管理）
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间"
    )

    # 关联的帧结果（级联删除）
    frames = relationship(
        "FrameResult",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
