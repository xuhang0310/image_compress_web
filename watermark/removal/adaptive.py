"""
自适应去除参数配置

根据检测结果智能选择最优的去除参数
"""

from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional
import numpy as np


@dataclass
class RemovalConfig:
    """去除配置"""
    algorithm: str = "NS"              # NS (Navier-Stokes) 或 Telea
    inpaint_radius: int = 5            # 修复半径（增大以获得更好效果）
    feather_radius: int = 8            # 掩码边缘羽化半径（增大以获得更平滑过渡）
    dilation_iterations: int = 2       # 掩码膨胀次数（增大以确保覆盖水印边缘）
    output_quality: int = 98           # 输出质量
    preserve_exif: bool = True         # 保留 EXIF 信息
    output_format: str = "auto"        # 输出格式: auto, png, jpeg
                                       # auto: 透明图用PNG，其他用JPEG
                                       # png: 强制PNG无损
                                       # jpeg: 强制JPEG有损


class AdaptiveRemovalConfig:
    """
    自适应去除参数配置器

    根据检测结果和图片特征自动选择最优参数
    """

    # 算法选择阈值
    ALGORITHM_THRESHOLDS = {
        'small_area': 0.05,    # 面积小于 5% 使用 NS
        'large_area': 0.15     # 面积大于 15% 使用 Telea
    }

    # 半径配置
    RADIUS_CONFIG = {
        'base': 5,
        'conservative_multiplier': 1.3,
        'large_image_multiplier': 1.2,
        'small_area_multiplier': 1.1
    }

    @classmethod
    def get_config(
        cls,
        image_size: Tuple[int, int],
        bbox: Tuple[int, int, int, int],
        mode: str = "normal",
        confidence: float = 0.8
    ) -> RemovalConfig:
        """
        根据检测参数生成最优去除配置

        Args:
            image_size: (width, height)
            bbox: (x1, y1, x2, y2) 水印区域
            mode: normal / conservative
            confidence: 检测置信度

        Returns:
            RemovalConfig: 最优配置
        """
        w, h = image_size
        x1, y1, x2, y2 = bbox

        # 计算水印区域特征
        watermark_area = (x2 - x1) * (y2 - y1)
        image_area = w * h
        area_ratio = watermark_area / image_area
        min_dim = min(w, h)

        config = RemovalConfig()

        # 1. 算法选择
        config.algorithm = cls._select_algorithm(area_ratio)

        # 2. 修复半径
        config.inpaint_radius = cls._calculate_radius(
            min_dim, area_ratio, mode
        )

        # 3. 羽化半径
        config.feather_radius = cls._calculate_feather_radius(
            area_ratio, mode
        )

        # 4. 膨胀次数
        config.dilation_iterations = cls._calculate_dilation(
            mode, confidence
        )

        # 5. 输出质量
        if mode == "conservative":
            config.output_quality = 98  # 保守模式提高质量

        return config

    @classmethod
    def _select_algorithm(cls, area_ratio: float) -> str:
        """
        选择修复算法

        - NS: 适合小面积，保留更多细节
        - Telea: 适合大面积，平滑效果更好
        """
        if area_ratio < cls.ALGORITHM_THRESHOLDS['small_area']:
            return "NS"
        elif area_ratio > cls.ALGORITHM_THRESHOLDS['large_area']:
            return "Telea"
        else:
            # 中等面积，根据其他因素决定
            return "NS"

    @classmethod
    def _calculate_radius(
        cls,
        min_image_dim: int,
        area_ratio: float,
        mode: str
    ) -> int:
        """
        计算修复半径
        """
        base = cls.RADIUS_CONFIG['base']

        # 根据图片尺寸调整
        if min_image_dim > 2000:
            base = int(base * cls.RADIUS_CONFIG['large_image_multiplier'])

        # 根据水印面积调整
        if area_ratio < 0.02:
            base = int(base * cls.RADIUS_CONFIG['small_area_multiplier'])

        # 保守模式扩大半径
        if mode == "conservative":
            base = int(base * cls.RADIUS_CONFIG['conservative_multiplier'])

        return max(base, 2)  # 最小为 2

    @classmethod
    def _calculate_feather_radius(
        cls,
        area_ratio: float,
        mode: str
    ) -> int:
        """
        计算羽化半径

        羽化可以使修复边缘更平滑
        """
        if mode == "conservative":
            return 4

        if area_ratio > 0.1:
            return 3

        return 2

    @classmethod
    def _calculate_dilation(
        cls,
        mode: str,
        confidence: float
    ) -> int:
        """
        计算掩码膨胀次数

        膨胀可以确保水印边界被完全覆盖
        """
        if mode == "conservative":
            return 2

        if confidence < 0.7:
            return 2  # 置信度低时扩大范围

        return 1

    @staticmethod
    def create_mask(
        image_shape: Tuple[int, ...],
        bbox: Tuple[int, int, int, int],
        feather_radius: int = 2,
        dilation_iterations: int = 1
    ) -> np.ndarray:
        """
        创建修复掩码

        Args:
            image_shape: 图片形状 (H, W) 或 (H, W, C)
            bbox: (x1, y1, x2, y2) 水印区域
            feather_radius: 羽化半径
            dilation_iterations: 膨胀次数

        Returns:
            np.ndarray: 二值掩码 (H, W)
        """
        import cv2

        h, w = image_shape[:2]
        x1, y1, x2, y2 = bbox

        # 确保坐标在有效范围
        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(x1 + 1, min(x2, w))
        y2 = max(y1 + 1, min(y2, h))

        # 创建基础掩码
        mask = np.zeros((h, w), dtype=np.uint8)
        mask[y1:y2, x1:x2] = 255

        # 膨胀处理 - 使用椭圆形核对边缘更友好
        if dilation_iterations > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            mask = cv2.dilate(mask, kernel, iterations=dilation_iterations)

        # 边缘羽化 - 使用更大的核进行高斯模糊，让过渡更平滑
        if feather_radius > 0:
            # 使用更大的羽化半径
            blur_size = min(feather_radius * 4 + 1, 51)  # 最大 51
            mask_float = mask.astype(np.float32)
            mask_blurred = cv2.GaussianBlur(mask_float, (blur_size, blur_size), feather_radius)
            # 保留羽化效果，不直接二值化
            mask = np.clip(mask_blurred, 0, 255).astype(np.uint8)

        return mask

    @staticmethod
    def create_optimized_mask(
        image_shape: Tuple[int, ...],
        bbox: Tuple[int, int, int, int],
        feather_radius: int = 15,
        dilation_iterations: int = 2
    ) -> np.ndarray:
        """
        创建优化的修复掩码（带边缘羽化）

        这是 create_mask 的增强版本，提供更好的边缘融合效果
        """
        import cv2

        h, w = image_shape[:2]
        x1, y1, x2, y2 = bbox

        # 确保坐标有效
        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(x1 + 1, min(x2, w))
        y2 = max(y1 + 1, min(y2, h))

        # 创建基础掩码
        mask = np.zeros((h, w), dtype=np.uint8)
        mask[y1:y2, x1:x2] = 255

        # 膨胀处理（覆盖更多边缘）
        if dilation_iterations > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
            mask = cv2.dilate(mask, kernel, iterations=dilation_iterations)

        # 关键：边缘羽化，让过渡更平滑
        if feather_radius > 0:
            mask_float = mask.astype(np.float32)
            mask_blurred = cv2.GaussianBlur(
                mask_float,
                (feather_radius * 2 + 1, feather_radius * 2 + 1),
                feather_radius
            )
            mask = mask_blurred.astype(np.uint8)

        return mask
