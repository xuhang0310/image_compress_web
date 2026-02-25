"""
全自动水印检测与去除模块

提供功能：
- 智能水印位置检测（多策略融合）
- 自适应水印去除
- 批量处理优化

使用示例：
    >>> from watermark import AutoWatermarkRemover
    >>> remover = AutoWatermarkRemover()
    >>> result = remover.remove('input.jpg', 'output.jpg')
"""

from .core import AutoWatermarkRemover, QuickWatermarkRemover
from .detector.core import WatermarkDetector, DetectionResult, FusionResult
from .removal.adaptive import AdaptiveRemovalConfig, RemovalConfig

__all__ = [
    'AutoWatermarkRemover',
    'QuickWatermarkRemover',
    'WatermarkDetector',
    'DetectionResult',
    'FusionResult',
    'AdaptiveRemovalConfig',
    'RemovalConfig'
]
