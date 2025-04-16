# \app\ml_models\onnx_inference.py
import onnxruntime
import numpy as np
from PIL import Image
from io import BytesIO
from project_backend.app.config.settings import settings
from pathlib import Path


class ONNXGenderClassifier:
    def __init__(self, model_path: str):
        """仅负责单个模型的初始化和推理"""
        self.name = Path(model_path).stem
        # 动态选择可用 Provider
        available_providers = onnxruntime.get_available_providers()
        if 'CUDAExecutionProvider' in available_providers:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        else:
            providers = ['CPUExecutionProvider']

        # 初始化会话配置
        sess_options = onnxruntime.SessionOptions()
        sess_options.intra_op_num_threads = 2
        sess_options.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL

        self.session = onnxruntime.InferenceSession(
            model_path,
            providers=providers,
            sess_options=sess_options
        )
        self.input_name = self.session.get_inputs()[0].name

    def predict(self, image_data: bytes) -> dict:
        """完整推理流程"""
        image = self._bytes_to_image(image_data)
        processed = self._preprocess(image)
        outputs = self._inference(processed)
        return self._postprocess(outputs)

    def _bytes_to_image(self, data: bytes) -> Image.Image:
        """字节流转 PIL 图像"""
        return Image.open(BytesIO(data))

    def _preprocess(self, image: Image.Image) -> np.ndarray:
        """图像预处理"""
        image = image.resize(settings.MODEL_INPUT_SIZE)
        image_array = np.array(image, dtype=np.float32)
        # 归一化 (根据模型训练配置)
        image_array = (image_array / 255.0 - 0.5) / 0.5
        # 调整维度顺序为 CHW 并添加 batch 维度
        return np.transpose(image_array, (2, 0, 1))[np.newaxis, ...]

    def _inference(self, input_tensor: np.ndarray) -> list:
        """执行 ONNX 推理"""
        return self.session.run(None, {self.input_name: input_tensor})

    def _postprocess(self, outputs: list) -> dict:
        """后处理适配多场景"""
        output_data = outputs[0]
        # 二分类 sigmoid 输出
        if output_data.shape == (1, 1):
            confidence = float(output_data[0][0])
            gender = "male" if confidence > 0.5 else "female"
            return {"gender": gender, "confidence": confidence}
        # 多分类 softmax 输出
        else:
            probs = output_data[0]
            class_idx = np.argmax(probs)
            return {
                "gender": settings.CLASS_LABELS[class_idx],
                "confidence": float(probs[class_idx])
            }