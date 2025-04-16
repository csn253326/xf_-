# app/models/metadata.py
from sqlalchemy import Column, String, JSON, Float, DateTime, UniqueConstraint, CheckConstraint
from sqlalchemy.sql import func
from project_backend.app.database.declarative_base import Base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
class ModelMetadata(Base):
    __tablename__ = "model_metadata"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_model_version"),  # 名称+版本唯一
        CheckConstraint("accuracy >= 0 AND accuracy <= 1", name="ck_accuracy_range"),
    )

    # 独立UUID主键
    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    name = Column(String(50), nullable=False, comment="模型名称（如 'gender_classifier'）")
    version = Column(String(20), nullable=False, comment="语义化版本（如 'v1.0.0'）")
    parameters = Column(JSON, comment="训练超参数（如学习率、批大小）")
    accuracy = Column(Float, comment="验证集精度")
    model_path = Column(String(256), comment="MinIO存储路径（如 'models/gender/v1.0.0.onnx'）")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    metrics = Column(JSON, comment="其他评估指标（如 {'f1': 0.92, 'auc': 0.98}）")