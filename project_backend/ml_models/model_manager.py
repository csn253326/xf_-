import torch
from ultralytics import YOLO
from .video_processor import VideoProcessor


class ModelLoader:
    def __init__(self):
        self._models = {}
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    async def load_gender_model(self):
        model = YOLO("ml_models/model_weights/gender.pt") # 加载模型
        model.to(self._device) # 模型部署到指定位置
        model.fuse() # 融合模型层加速推理
        self._models["gender"] = model # 存储模型实例
        VideoProcessor.register_pipeline('gender', self.process_frame) # 注册处理函数

    @torch.inference_mode()
    async def process_frame(self, frame):
        results = self._models["gender"](frame, imgsz=640, verbose=False)
        return self._format_results(results)

    def _format_results(self, results):
        return [{
            "bbox": box.xyxy[0].tolist(),
            "confidence": float(conf),
            "label": "male" if cls == 0 else "female",
            "model_type": "gender"
        } for box, conf, cls in zip(results[0].boxes.xyxy,
                                    results[0].boxes.conf,
                                    results[0].boxes.cls)]