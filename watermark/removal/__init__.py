"""
水印去除模块

提供：
- 自适应参数配置
- 现有算法包装器
"""

from .adaptive import AdaptiveRemovalConfig, RemovalConfig
from .wrapper import WatermarkRemoverWrapper

__all__ = [
    'AdaptiveRemovalConfig',
    'RemovalConfig',
    'WatermarkRemoverWrapper'
]
