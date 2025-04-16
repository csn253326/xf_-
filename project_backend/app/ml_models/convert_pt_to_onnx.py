# convert_pt_to_onnx.py
import torch
import torch.onnx
import os
from pathlib import Path
from project_backend.app.ml_models.gender_model import GenderClassifier

# ------------------------- 路径配置 -------------------------
# 获取项目根目录（假设脚本在 app/ml_models/ 目录下）
BASE_DIR = Path(__file__).parent.parent.parent  # 根据实际层级调整
MODEL_PT_PATH = BASE_DIR / "ml_models" / "model_weights" / "gender.pt"
MODEL_ONNX_PATH = BASE_DIR / "ml_models" / "model_weights" / "gender.onnx"

# 验证路径存在性
if not MODEL_PT_PATH.exists():
    raise FileNotFoundError(f"❌ 模型文件不存在：{MODEL_PT_PATH}")

# ------------------------- 转换配置 -------------------------
INPUT_SHAPE = (1, 3, 224, 224)  # 与训练时完全一致

def convert():
    # 1. 加载检查点
    checkpoint = torch.load(
        MODEL_PT_PATH,
        map_location='cpu',
        weights_only=False
    )

    # 2. 直接获取模型对象
    model = checkpoint['model']  # 直接获取已实例化的模型
    model.eval()
    dummy_input = torch.randn(INPUT_SHAPE)

    # 3. 导出ONNX
    torch.onnx.export(
        model,
        dummy_input,
        str(MODEL_ONNX_PATH),
        opset_version=12,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}}
    )
    print(f"✅ 成功导出ONNX模型到：{MODEL_ONNX_PATH}")

if __name__ == "__main__":
    convert()

