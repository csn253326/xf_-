from celery import shared_task
from project_backend.app.utils.image_utils import process_image
from project_backend.app.database.crud.image import create_image_record
from project_backend.app.database.base import AsyncSessionLocal
from asgiref.sync import async_to_sync
import tempfile
import os
import logging

@shared_task(bind=True, max_retries=3)
def edge_detection_task(self, image_data: bytes, original_filename: str):
    """异步边缘检测任务"""
    input_path, output_path = None, None
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            tmp_file.write(image_data)
            input_path = tmp_file.name

        # 处理图像
        output_path = process_image(input_path)

        # 数据库记录（异步上下文）
        async def save_record():
            async with AsyncSessionLocal() as session:
                record = await create_image_record(
                    session,
                    input_path=input_path,
                    output_path=output_path,
                    filename=original_filename
                )
                return record.id

        record_id = async_to_sync(save_record)()

        return {
            "status": "success",
            "result_path": output_path,
            "record_id": record_id
        }

    except Exception as exc:
        logging.error(f"Edge detection failed: {str(exc)}")
        self.retry(countdown=60 * self.request.retries, exc=exc)
    finally:
        # 清理临时文件
        for path in [input_path, output_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception as e:
                    logging.warning(f"清理临时文件失败: {e}")
