# \app\database\crud\image.py
from sqlalchemy.orm import Session
from project_backend.app.database.models.image_record import ImageProcessRecord

def create_image_record(db: Session, input_path: str, output_path: str, user_id: int = None):
    """创建图像处理记录"""
    db_record = ImageProcessRecord(
        input_path=input_path,
        output_path=output_path,
        user_id=user_id
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

def get_records_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """查询用户的所有处理记录"""
    return db.query(ImageProcessRecord).filter(
        ImageProcessRecord.user_id == user_id
    ).offset(skip).limit(limit).all()