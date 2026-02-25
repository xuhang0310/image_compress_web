"""
水印检测器核心类

提供统一的水印检测接口，整合多种检测策略
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
import numpy as np
import cv2
from pathlib import Path


class DetectionMode(Enum):
    """检测模式"""
    AUTO = "auto"           # 自动选择策略
    POSITION = "position"   # 仅位置策略
    COLOR = "color"         # 仅颜色策略
    TEXTURE = "texture"     # 仅纹理策略


@dataclass
class DetectionResult:
    """单策略检测结果"""
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float                # 置信度 0.0-1.0
    method: str                      # 检测方法名称
    roi: Optional[np.ndarray] = None # ROI 区域图像
    mask: Optional[np.ndarray] = None # 二值掩码
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外信息

    def __post_init__(self):
        """验证数据"""
        if not (0 <= self.confidence <= 1):
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")
        if len(self.bbox) != 4:
            raise ValueError(f"bbox must have 4 elements, got {len(self.bbox)}")

    @property
    def area(self) -> int:
        """计算区域面积"""
        return (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])

    @property
    def width(self) -> int:
        """区域宽度"""
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> int:
        """区域高度"""
        return self.bbox[3] - self.bbox[1]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'bbox': list(self.bbox),
            'confidence': round(self.confidence, 4),
            'method': self.method,
            'area': self.area,
            'width': self.width,
            'height': self.height
        }


@dataclass
class FusionResult:
    """融合决策结果"""
    success: bool
    bbox: Optional[Tuple[int, int, int, int]] = None
    confidence: float = 0.0
    mode: str = ""                    # normal / conservative
    contributors: List[str] = field(default_factory=list)
    reason: str = ""
    all_results: Dict[str, List[DetectionResult]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'success': self.success,
            'confidence': round(self.confidence, 4),
            'mode': self.mode,
            'contributors': self.contributors,
            'reason': self.reason
        }
        if self.bbox:
            result['bbox'] = list(self.bbox)
        if self.all_results:
            result['all_results'] = {
                k: [r.to_dict() for r in v]
                for k, v in self.all_results.items()
            }
        return result


class WatermarkDetector:
    """
    水印检测器主类

    整合多种检测策略，提供统一的检测接口

    使用示例:
        >>> detector = WatermarkDetector()
        >>> image = cv2.imread('image.jpg')
        >>> result = detector.detect(image)
        >>> print(result.bbox, result.confidence)
    """

    def __init__(self, mode: DetectionMode = DetectionMode.AUTO):
        """
        初始化检测器

        Args:
            mode: 检测模式，默认 AUTO
        """
        self.mode = mode
        self._strategies = {}
        self._init_strategies()

    def _init_strategies(self):
        """初始化检测策略"""
        from .strategies import PositionStrategy, ColorStrategy

        self._strategies['position'] = PositionStrategy()
        self._strategies['color'] = ColorStrategy()

        # 可选策略（如果依赖存在）
        try:
            from .strategies import TextureStrategy
            self._strategies['texture'] = TextureStrategy()
        except ImportError:
            pass

    def detect(
        self,
        image: np.ndarray,
        min_confidence: float = 0.5
    ) -> FusionResult:
        """
        检测水印位置

        Args:
            image: 输入图像 (BGR格式)
            min_confidence: 最小置信度阈值

        Returns:
            FusionResult: 融合决策结果
        """
        if image is None or image.size == 0:
            return FusionResult(
                success=False,
                reason="Invalid image"
            )

        # 执行所有策略
        all_results = {}

        if self.mode == DetectionMode.AUTO:
            # 执行所有策略
            for name, strategy in self._strategies.items():
                try:
                    results = strategy.detect(image)
                    if results:
                        all_results[name] = results
                except Exception as e:
                    # 单个策略失败不影响整体
                    continue
        else:
            # 仅执行指定策略
            strategy_name = self.mode.value
            if strategy_name in self._strategies:
                results = self._strategies[strategy_name].detect(image)
                if results:
                    all_results[strategy_name] = results

        if not all_results:
            return FusionResult(
                success=False,
                reason="No detection results from any strategy"
            )

        # 融合决策
        from .fusion import FusionEngine
        fusion_engine = FusionEngine()
        result = fusion_engine.fuse(all_results)
        result.all_results = all_results

        return result

    def detect_file(
        self,
        image_path: str,
        min_confidence: float = 0.5
    ) -> FusionResult:
        """
        从文件检测水印

        Args:
            image_path: 图片路径
            min_confidence: 最小置信度阈值

        Returns:
            FusionResult: 融合决策结果
        """
        try:
            # 使用 PIL 处理中文路径
            from PIL import Image
            pil_img = Image.open(image_path)
            image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            return self.detect(image, min_confidence)
        except Exception as e:
            return FusionResult(
                success=False,
                reason=f"Failed to load image: {str(e)}"
            )

    def visualize_detection(
        self,
        image: np.ndarray,
        result: FusionResult,
        save_path: Optional[str] = None
    ) -> np.ndarray:
        """
        可视化检测结果

        Args:
            image: 原始图像
            result: 检测结果
            save_path: 可选的保存路径

        Returns:
            可视化后的图像
        """
        vis_image = image.copy()

        # 绘制所有策略的候选框（半透明）
        colors = {
            'position': (255, 0, 0),    # 蓝色
            'color': (0, 255, 0),        # 绿色
            'texture': (0, 0, 255)       # 红色
        }

        for strategy_name, results in result.all_results.items():
            color = colors.get(strategy_name, (128, 128, 128))
            for r in results:
                x1, y1, x2, y2 = r.bbox
                cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 1)
                cv2.putText(
                    vis_image,
                    f"{strategy_name}:{r.confidence:.2f}",
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    color,
                    1
                )

        # 绘制最终结果（粗线）
        if result.success and result.bbox:
            x1, y1, x2, y2 = result.bbox
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), (0, 255, 255), 3)
            cv2.putText(
                vis_image,
                f"FINAL:{result.confidence:.2f}",
                (x1, y1 - 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2
            )

        if save_path:
            cv2.imwrite(save_path, vis_image)

        return vis_image
