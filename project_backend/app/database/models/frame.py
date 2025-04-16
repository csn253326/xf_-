# app/database/models/frame.py
from sqlalchemy import Column, Float, ForeignKey, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from project_backend.app.database.declarative_base import Base
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

class GenderEnum(PyEnum):
    MALE = "male"
    FEMALE = "female"

class FrameResult(Base):
    __tablename__ = "frame_results"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True)  # 使用UUID
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("tasks.id",ondelete="CASCADE"))  # 关联主任务表
    frame_index = Column(Integer, comment="视频帧序号")
    gender = Column(Enum(GenderEnum), comment="性别分类结果")
    confidence = Column(Float, comment="置信度")
    timestamp = Column(Float, comment="帧对应的时间戳（秒）")
    task = relationship("Task", back_populates="frames")  # 新增