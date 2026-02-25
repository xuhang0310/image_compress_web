"""
水印检测器模块

提供多种检测策略：
- PositionStrategy: 基于固定位置的检测
- ColorStrategy: 基于颜色特征的检测
- TextureStrategy: 基于纹理特征的检测
- FusionEngine: 多策略融合决策
"""

from .core import WatermarkDetector, DetectionResult, FusionResult
from .strategies import PositionStrategy, ColorStrategy, TextureStrategy
from .fusion import FusionEngine

__all__ = [
    'WatermarkDetector',
    'DetectionResult',
    'FusionResult',
    'PositionStrategy',
    'ColorStrategy',
    'TextureStrategy',
    'FusionEngine'
]
