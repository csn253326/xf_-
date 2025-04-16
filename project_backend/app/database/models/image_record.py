# \app\database\models\image_record.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from project_backend.app.database.declarative_base import Base

class ImageProcessRecord(Base):
    __tablename__ = "image_process_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", nullable=True))  # 关联用户（可选）
    input_path = Column(String(500), nullable=False)
    output_path = Column(String(500), nullable=False)
    status = Column(String(50), default="pending")  # 如: pending, success, failed
    created_at = Column(DateTime, default=datetime.utcnow)