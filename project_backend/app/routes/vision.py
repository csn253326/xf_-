# \app\routes\vision.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from project_backend.app.utils.image_utils import process_image
#from project_backend.app.database import crud
#from project_backend.app.database.base import get_db
from project_backend.app.ml_models.model_manager import model_manager
from project_backend.app.config.settings import settings
import tempfile
import contextlib
import os
import logging

router = APIRouter(tags=["计算机视觉"], prefix="/api/v1")


# ------------------------- 响应模型 -------------------------
class ClassificationResult(BaseModel):
    """图像分类响应模型"""
    class_name: str = Field(..., example="female", description="预测类别")
    confidence: float = Field(..., example=0.92, ge=0, le=1, description="置信度")
    model_version: str = Field(..., example="v2.1.0", description="模型版本")


class EdgeDetectionResult(BaseModel):
    """边缘检测响应模型"""
    result_url: str = Field(..., example="/results/edge_123.jpg", description="处理结果URL")
    #record_id: int = Field(..., example=42, description="数据库记录ID")


# ------------------------- 图像分类接口 -------------------------
@router.post(
    "/classify/image",
    summary="图像性别分类",
    description="""### 核心功能
- 接收JPEG/PNG格式图像
- 使用ONNX模型进行推理
- 返回性别分类结果及置信度

### 安全要求
- 需在请求头携带有效API Key
""",
    response_model=ClassificationResult,
    responses={
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
            "description": "文件过大",
            "content": {"application/json": {"example": {"detail": "文件超过8MB限制"}}}
        },
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {
            "description": "文件类型错误",
            "content": {"application/json": {"example": {"detail": "仅支持 ['image/jpeg', 'image/png'] 格式"}}}
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "服务器内部错误",
            "content": {"application/json": {"example": {"detail": "模型推理错误"}}}
        }
    }
)
async def classify_image(
        file: UploadFile = File(...,
                                description=f"允许格式：{settings.ALLOWED_IMAGE_TYPES}，最大 {settings.MAX_FILE_SIZE // 1024 // 1024}MB")
):
    try:
        # 验证文件类型
        if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"仅支持 {settings.ALLOWED_IMAGE_TYPES} 格式"
            )

        # 验证文件大小
        image_data = await file.read()
        await file.close()
        if len(image_data) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件大小超过 {settings.MAX_FILE_SIZE // 1024 // 1024}MB 限制"
            )

        # 获取模型实例
        model = model_manager.get_model()
        result = model.predict(image_data)

        return JSONResponse(
            content=result,
            headers={"X-Model-Version": model.version}
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Classification failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="模型推理错误"
        )


# ------------------------- 边缘检测接口 -------------------------
@router.post(
    "/edge-detection",
    summary="图像边缘检测",
    description="""### 处理流程
1. 接收上传图像文件
2. 执行Canny边缘检测算法
3. 保存结果到存储系统
4. 记录处理元数据到数据库

### 输出说明
- 结果文件保留24小时
- 支持PNG/JPG两种输出格式
""",
    response_model=EdgeDetectionResult,
    responses={
        status.HTTP_201_CREATED: {
            "description": "处理成功",
            "content": {"application/json": {"example": {
                "result_url": "/results/edge_123.jpg",
                "record_id": 42
            }}}
        }
    }
)
async def edge_detection(
        file: UploadFile = File(...,
                                description="支持JPEG/PNG格式，建议分辨率不超过1920x1080"),
        #db: Session = Depends(get_db)
):
    with contextlib.ExitStack() as stack:
        try:
            # 保存上传文件
            tmp_file = stack.enter_context(
                tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            )
            await file.seek(0)
            tmp_file.write(await file.read())
            tmp_path = tmp_file.name

            # 处理图像
            output_path = process_image(
                tmp_path,
                target_size=settings.MODEL_INPUT_SIZE
            )
            stack.callback(lambda: os.unlink(output_path))

            # 数据库事务
            #db.begin()
            #record = crud.image.create_image_record(db, tmp_path, output_path)
            #db.commit()

            return JSONResponse(
                content={"result_url": output_path},
                status_code=status.HTTP_201_CREATED
            )

        except Exception as e:
            #db.rollback()
            logging.error(f"Edge detection failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"处理失败: {str(e)}"
            )