# app/ml_models/gender_model.py
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from collections import OrderedDict

class GenderClassifier(nn.Module):
    def __init__(self, yolo_mode=False):
        """
        增强版性别分类模型

        参数：
            in_channels: 输入通道数（默认3对应RGB）
            base_channels: 基础通道数（控制模型复杂度）
            num_classes: 输出类别数（二分类设为2）
            input_size: 模型预期输入尺寸（H, W）
        """
        super().__init__()
        self.yolo_mode = yolo_mode
        self.model = self._build_yolo_layers()

    def _build_yolo_layers(self):
        """构建与YOLO权重匹配的层结构"""
        layers = [
            ('0.conv', nn.Conv2d(3, 64, 3)),
            ('0.bn', nn.BatchNorm2d(64)),
            ('0.act', nn.ReLU()),
            ('1.pool', nn.MaxPool2d(2)),
            # 根据错误提示补充所有缺失层结构...
        ]
        return nn.Sequential(OrderedDict(layers))
    def _init_weights(self):
        """使用He初始化优化卷积层"""
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播

        输入：
            x: 形状为 (batch_size, 3, H, W) 的输入张量
        输出：
            形状为 (batch_size, num_classes) 的未归一化logits
        """
        # 输入验证
        if x.dim() != 4:
            raise ValueError(f"预期输入维度4，实际得到{x.dim()}")

        # 特征提取
        x = self.features(x)

        # 自适应池化
        x = self.adaptive_pool(x)

        # 展平
        x = torch.flatten(x, 1)

        # 分类
        return self.classifier(x)

    @property
    def device(self):
        """获取模型当前设备"""
        return next(self.parameters()).device

    @torch.no_grad()
    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """输出概率预测"""
        logits = self.forward(x)
        return F.softmax(logits, dim=1)

    @staticmethod
    def get_preprocess_transform():
        """获取标准预处理转换（需与训练时一致）"""
        return transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],  # ImageNet标准均值
                std=[0.229, 0.224, 0.225]    # ImageNet标准方差
            )
        ])

# 示例用法
if __name__ == "__main__":
    model = GenderClassifier()
    dummy_input = torch.randn(1, 3, 224, 224)
    output = model(dummy_input)
    print(f"输入形状: {dummy_input.shape}")
    print(f"输出形状: {output.shape}")
    print(f"概率预测示例:\n{model.predict_proba(dummy_input)}")
