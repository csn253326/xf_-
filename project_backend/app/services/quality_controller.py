from typing import Dict, Literal, Optional
import time
import numpy as np
from project_backend.app.utils.metrics import monitor

ResolutionType = Literal["1080p", "720p", "480p", "360p"]
FrameRateType = Literal["30fps", "24fps", "15fps", "10fps"]
CodecType = Literal["h264", "h265", "vp9"]


class ClientProfile:
    """客户端质量档案（内存数据库存储）"""

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.resolution: ResolutionType = "1080p"
        self.framerate: FrameRateType = "30fps"
        self.codec: CodecType = "h264"
        self.last_adjusted = time.time()
        self._quality_lock = False  # 防止频繁调整


class DynamicQualityController:
    """
    智能视频质量调控器

    功能特性：
    - 基于网络状况的ABR（Adaptive Bitrate）算法
    - 分级降级/升级策略
    - 客户端能力协商
    - 防抖动处理
    """

    def __init__(self):
        self.client_profiles: Dict[str, ClientProfile] = {}
        self._load_model()  # 加载预测模型

    def _load_model(self):
        """加载质量预测模型（示例为简单线性回归）"""
        # 生产环境应替换为实际ML模型
        self.bitrate_model = np.poly1d([-0.5, 2.5])  # 示例模型: bitrate = -0.5x + 2.5

    def get_client_profile(self, client_id: str) -> ClientProfile:
        """获取或创建客户端质量档案"""
        if client_id not in self.client_profiles:
            self.client_profiles[client_id] = ClientProfile(client_id)
        return self.client_profiles[client_id]

    def adjust(self, client_id: str, network_stats: dict) -> Optional[dict]:
        """
        动态调整视频处理参数

        参数:
            network_stats: {
                "rtt": 100,       # 毫秒
                "jitter": 50,     # 毫秒
                "bandwidth": 2.5, # Mbps
                "packet_loss": 0.02 # 丢包率
            }
        返回:
            调整指令，例如 {"action": "downscale", "resolution": "720p"}
        """
        profile = self.get_client_profile(client_id)

        # 防抖动处理：10秒内不重复调整
        if time.time() - profile.last_adjusted < 10:
            return None

        # 计算推荐参数
        target_bitrate = self._calculate_target_bitrate(network_stats)
        action = self._determine_action(profile, target_bitrate, network_stats)

        if action:
            profile.last_adjusted = time.time()
            self._apply_adjustment(profile, action)
            monitor.record_quality_change(client_id, action)
            return action

    def _calculate_target_bitrate(self, stats: dict) -> float:
        """基于网络指标计算目标码率（Mbps）"""
        # 简化的线性模型，实际应使用更复杂算法
        score = 0.7 * stats['bandwidth'] - 0.2 * stats['rtt'] - 0.1 * stats['packet_loss']
        return max(0.5, self.bitrate_model(score))

    def _determine_action(self, profile: ClientProfile, target_bitrate: float, stats: dict) -> Optional[dict]:
        """决策树生成调整指令"""
        current_bitrate = self._estimate_current_bitrate(profile)

        # 紧急降级条件
        if stats['packet_loss'] > 0.1 or stats['rtt'] > 500:
            return self._generate_downgrade(profile, "emergency")

        # 带宽不足时降级
        if target_bitrate < current_bitrate * 0.8:
            return self._generate_downgrade(profile, "bandwidth")

        # 带宽充足时尝试升级
        if target_bitrate > current_bitrate * 1.2:
            return self._generate_upgrade(profile)

        return None

    def _generate_downgrade(self, profile: ClientProfile, reason: str) -> dict:
        """生成降级指令"""
        resolutions = ["1080p", "720p", "480p", "360p"]
        current_idx = resolutions.index(profile.resolution)

        if current_idx < len(resolutions) - 1:
            new_res = resolutions[current_idx + 1]
            return {
                "action": "downscale",
                "reason": reason,
                "resolution": new_res,
                "framerate": self._adjust_framerate(profile.framerate, -5)
            }
        return None

    def _generate_upgrade(self, profile: ClientProfile) -> Optional[dict]:
        """生成升级指令"""
        resolutions = ["1080p", "720p", "480p", "360p"]
        current_idx = resolutions.index(profile.resolution)

        if current_idx > 0:
            new_res = resolutions[current_idx - 1]
            return {
                "action": "upscale",
                "resolution": new_res,
                "framerate": self._adjust_framerate(profile.framerate, +5)
            }
        return None

    def _adjust_framerate(self, current: str, delta: int) -> str:
        """调整帧率（示例逻辑）"""
        current_fps = int(current.replace("fps", ""))
        new_fps = max(10, min(30, current_fps + delta))
        return f"{new_fps}fps"

    def _estimate_current_bitrate(self, profile: ClientProfile) -> float:
        """估算当前配置的码率需求"""
        res_map = {"1080p": 4.0, "720p": 2.5, "480p": 1.5, "360p": 0.8}
        fps_map = {"30fps": 1.0, "24fps": 0.8, "15fps": 0.5, "10fps": 0.3}
        return res_map[profile.resolution] * fps_map[profile.framerate]

    def _apply_adjustment(self, profile: ClientProfile, action: dict):
        """应用调整到客户端档案"""
        if "resolution" in action:
            profile.resolution = action["resolution"]
        if "framerate" in action:
            profile.framerate = action["framerate"]

    def force_downgrade(self, client_id: str, level: int = 1):
        """外部触发强制降级（如系统过载）"""
        profile = self.get_client_profile(client_id)
        for _ in range(level):
            action = self._generate_downgrade(profile, "system_overload")
            if action:
                self._apply_adjustment(profile, action)
        return action


# 单例实例
quality_controller = DynamicQualityController()