# app/ml_models/model_manager.py
import logging
import threading
import hashlib
import torch
from pathlib import Path
from ultralytics import YOLO
from typing import Optional, Dict, Any
from project_backend.app.config.settings import settings
from project_backend.app.ml_models.mock_model import MockGenderClassifier
from project_backend.app.config.prometheus import MODEL_LOAD_STATUS
from project_backend.app.ml_models.video_processor import VideoProcessor
from project_backend.app.ml_models.gender_model import GenderClassifier

class SecurityError(Exception):
    """自定义模型安全异常"""
    pass

class PyTorchGenderClassifier:
    """PyTorch模型封装类（支持YOLO和自定义模型）"""
    def __init__(self, model_path: str):
        self.name = Path(model_path).stem
        self.device = torch.device("cuda" if torch.cuda.is_available() and not settings.FORCE_CPU else "cpu")
        self.model_type = "custom"
        self.model = self._load_yolo_model(model_path)
        self.preprocess = GenderClassifier.get_preprocess_transform()

    def _load_model(self, model_path: str) -> torch.nn.Module:
        """智能加载模型"""
        try:
            # 尝试作为标准PyTorch模型加载
            return self._load_pytorch_model(model_path)
        except (KeyError, RuntimeError) as e:
            logging.warning(f"标准PyTorch加载失败，尝试YOLO加载: {str(e)}")
            return self._load_yolo_model(model_path)

    def _load_pytorch_model(self, model_path: str) -> torch.nn.Module:
        """加载自定义PyTorch模型"""
        checkpoint: Dict[str, Any] = torch.load(model_path, map_location=self.device)

        # 自动识别检查点格式
        state_dict = checkpoint.get('model', checkpoint)  # 优先取'model'键值
        if hasattr(state_dict, 'state_dict'):  # 处理完整模型实例
            state_dict = state_dict.state_dict()

        model = GenderClassifier()
        model.load_state_dict(state_dict)
        model.to(self.device)
        model.eval()
        return model

    def _load_yolo_model(self, model_path: str) -> torch.nn.Module:
        """加载YOLO模型"""
        self.model_type = "yolo"
        model = YOLO(model_path)
        model.to(self.device)
        model.fuse()
        return model

    def predict(self, image_data: bytes) -> dict:
        """统一预测接口"""
        try:
            if self.model_type == "yolo":
                return self._predict_yolo(image_data)
            return self._predict_custom(image_data)
        except Exception as e:
            logging.error(f"预测失败: {str(e)}")
            return {"error": str(e)}

    def _predict_custom(self, image_data: bytes) -> dict:
        """自定义模型预测逻辑"""
        from PIL import Image
        from io import BytesIO

        # 预处理
        image = Image.open(BytesIO(image_data)).convert("RGB")
        input_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        # 推理
        with torch.no_grad():
            logits = self.model(input_tensor)
            probs = torch.softmax(logits, dim=1)

        # 后处理
        return {
            "gender": "male" if torch.argmax(probs).item() == 1 else "female",
            "confidence": torch.max(probs).item()
        }

    def _predict_yolo(self, image_data: bytes) -> dict:
        """YOLO模型预测逻辑"""
        import cv2
        import numpy as np

        # 转换图像
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        # 推理
        results = self.model(img, imgsz=640, verbose=False)

        # 格式化结果
        if len(results) == 0 or results[0].boxes is None:
            return {"gender": "unknown", "confidence": 0.0}

        best_box = results[0].boxes[0]
        return {
            "gender": "male" if best_box.cls.item() == 0 else "female",
            "confidence": best_box.conf.item(),
            "bbox": best_box.xyxy[0].tolist()
        }

class ModelManager:
    """增强版模型管理器"""
    def __init__(self):
        self._lock = threading.Lock()
        self.current_model: Optional[PyTorchGenderClassifier] = None
        self._load_count = 0  # 加载次数统计

    def load_model(self):
        """线程安全的模型加载"""
        with self._lock:
            try:
                self._load_count += 1
                if self.current_model:
                    self.release_model()

                if settings.USE_MOCK_MODEL:
                    self.current_model = MockGenderClassifier()
                    model_name = self.current_model.name
                else:
                    self._validate_model_path()
                    self._validate_model_signature()
                    self.current_model = PyTorchGenderClassifier(settings.MODEL_PATH)
                    model_name = self.current_model.name

                MODEL_LOAD_STATUS.labels(model_name=model_name).set(1)
                logging.info(f"成功加载模型（第{self._load_count}次）：{model_name}")

            except Exception as e:
                self._handle_load_error(e)

    def _validate_model_path(self):
        """验证模型路径有效性"""
        model_path = Path(settings.MODEL_PATH)
        if not model_path.exists():
            raise FileNotFoundError(f"模型文件不存在：{model_path.resolve()}")
        if model_path.stat().st_size < 1024:  # 最小1KB
            raise ValueError("模型文件异常（大小<1KB）")

    def _validate_model_signature(self):
        """模型哈希校验"""
        expected_hash = settings.MODEL_SHA256.lower()
        with open(settings.MODEL_PATH, "rb") as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        if actual_hash != expected_hash:
            raise SecurityError(f"模型哈希不匹配\n预期：{expected_hash}\n实际：{actual_hash}")

    def _handle_load_error(self, error: Exception):
        """统一错误处理"""
        model_name = "mock_fallback" if settings.USE_MOCK_MODEL else "unknown"
        MODEL_LOAD_STATUS.labels(model_name=model_name).set(0)
        logging.critical(f"模型加载失败：{str(error)}", exc_info=settings.DEBUG_MODE)

        if not settings.USE_MOCK_MODEL:
            self.current_model = MockGenderClassifier()
            logging.warning(f"已回退到模拟模型：{self.current_model.name}")

    def release_model(self):
        """安全释放模型资源"""
        with self._lock:
            if self.current_model:
                if hasattr(self.current_model.model, 'session'):  # ONNX Runtime会话
                    self.current_model.model.session.end_profiling()
                del self.current_model
                torch.cuda.empty_cache()
                self.current_model = None
                logging.info("模型资源已释放")

    def get_model(self):
        """获取当前模型实例"""
        with self._lock:
            return self.current_model or MockGenderClassifier()

    def reload_model(self, model_path: str = None):
        """动态重载模型"""
        with self._lock:
            old_model = self.current_model
            try:
                if model_path:
                    settings.MODEL_PATH = model_path
                self.load_model()
                if old_model:
                    old_model.release_model()
            except Exception as e:
                logging.error(f"热重载失败：{str(e)}")
                if old_model:
                    self.current_model = old_model

model_manager = ModelManager()

class StreamProcessor:
    """视频流处理器（支持硬件加速）"""
    def __init__(self):
        self._device = torch.device("cuda" if torch.cuda.is_available() and not settings.FORCE_CPU else "cpu")
        self._model = None
        self._warmup_count = 10  # GPU预热帧数

    async def initialize(self):
        """初始化视频流模型"""
        try:
            # 加载YOLO模型
            self._model = YOLO(settings.MODEL_PATH)
            self._model.to(self._device)

            # GPU预热
            if "cuda" in str(self._device):
                dummy_input = torch.rand(1, 3, 640, 640).to(self._device)
                for _ in range(self._warmup_count):
                    self._model(dummy_input)

            VideoProcessor.register_pipeline('gender', lambda frame: self.process_frame(frame))
            logging.info(f"视频流处理器已初始化（设备：{self._device}）")

        except Exception as e:
            logging.critical(f"视频流处理器初始化失败：{str(e)}")
            raise

    @torch.inference_mode()
    async def process_frame(self, frame: bytes) -> list:
        """处理视频帧"""
        try:
            # 转换帧数据
            img = self._bytes_to_cv2(frame)

            # 执行推理
            results = self._model(img, imgsz=640, verbose=False)

            # 格式化结果
            return self._format_results(results)
        except Exception as e:
            logging.error(f"帧处理失败：{str(e)}")
            return []

    def _bytes_to_cv2(self, image_data: bytes):
        """字节流转OpenCV图像"""
        import cv2
        import numpy as np
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    def _format_results(self, results) -> list:
        """标准化输出格式"""
        output = []
        for result in results:
            if result.boxes is None:
                continue
            for box, conf, cls in zip(result.boxes.xyxy, result.boxes.conf, result.boxes.cls):
                output.append({
                    "bbox": box.tolist(),
                    "confidence": float(conf),
                    "label": "male" if cls == 0 else "female",
                    "model_type": "gender"
                })
        return output

# 初始化流处理器
stream_processor = StreamProcessor()
async def startup_event():
    await stream_processor.initialize()

async def shutdown_event():
    if model_manager.current_model:
        model_manager.release_model()
