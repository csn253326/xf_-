# app/ml_models/mock_model.py
from io import BytesIO
from PIL import Image
import random

class MockGenderClassifier:
    def __init__(self):
        """初始化模拟分类器"""
        self.name = "mock_gender_v1"  # 新增的关键属性
        self.version = "1.0.0"

    def predict(self, image_data: bytes) -> dict:
        """
        模拟分类结果生成（兼容 PIL.Image 和字节流输入）

        参数:
            image_data: 字节流或已加载的 PIL.Image 对象

        返回:
            {
                "gender": 随机生成的性别标签,
                "confidence": 随机置信度 (0.5~0.99)
            }
        """
        # 统一的输入验证逻辑
        if not isinstance(image_data, Image.Image):
            try:
                image = Image.open(BytesIO(image_data))
                image.verify()  # 基础图像校验
            except Exception as e:
                raise ValueError(f"无效的图像输入: {str(e)}") from e
        else:
            image = image_data

        # 返回模拟结果
        return {
            "gender": random.choice(["male", "female"]),
            "confidence": round(random.uniform(0.5, 0.99), 2),
            "model_info": self._get_model_metadata()  # 新增元数据
        }

    def _get_model_metadata(self) -> dict:
        """返回模拟模型的元信息"""
        return {
            "name": self.name,
            "version": self.version,
            "type": "mock"
        }