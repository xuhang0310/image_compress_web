"""
水印去除包装器（LaMa 深度学习版本）

集成 LaMa 深度学习模型，提供高质量水印去除
效果远优于传统 OpenCV 算法
"""

import os
import sys
import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any
from pathlib import Path

# 导入自适应配置
from .adaptive import AdaptiveRemovalConfig, RemovalConfig

# 导入 LaMa
from .lama_inpainting import HybridInpainter, check_lama_installation, print_install_guide


class WatermarkRemoverWrapper:
    """
    水印去除包装器（基于 LaMa 深度学习）

    特点:
    - 优先使用 LaMa 深度学习修复
    - 自动降级到 OpenCV（如果 LaMa 未安装）
    - 智能格式保持（保留 PNG 透明）
    - 高质量输出
    """

    def __init__(self, device: str = "cpu", use_lama: bool = True):
        """
        初始化去除器

        Args:
            device: "cpu" 或 "cuda"
            use_lama: 是否使用 LaMa（如果可用）
        """
        self._stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'lama_used': 0,
            'opencv_used': 0
        }

        # 检查 LaMa 是否可用
        self.lama_available = check_lama_installation()
        if use_lama and not self.lama_available:
            print("=" * 60)
            print("[WatermarkRemover] LaMa 未安装，将使用 OpenCV")
            print("[WatermarkRemover] 安装 LaMa 可获得更好效果:")
            print("  pip install lama-cleaner")
            print("=" * 60)

        # 初始化混合修复器
        self.inpainter = HybridInpainter(device=device)
        self.use_lama = use_lama

    def remove(
        self,
        image: np.ndarray,
        bbox: Tuple[int, int, int, int],
        mode: str = "normal",
        confidence: float = 0.8,
        config: Optional[RemovalConfig] = None
    ) -> Tuple[bool, np.ndarray]:
        """
        去除水印

        Args:
            image: 输入图像 (BGR)
            bbox: (x1, y1, x2, y2) 水印区域
            mode: normal / conservative
            confidence: 检测置信度
            config: 可选的自定义配置

        Returns:
            (success, result_image)
        """
        try:
            # 获取配置
            if config is None:
                h, w = image.shape[:2]
                config = AdaptiveRemovalConfig.get_config(
                    (w, h), bbox, mode, confidence
                )

            # 创建掩码（使用优化的掩码生成）
            mask = AdaptiveRemovalConfig.create_optimized_mask(
                image.shape,
                bbox,
                config.feather_radius,
                config.dilation_iterations
            )

            # 执行修复（使用 LaMa 或 OpenCV）
            success, result = self.inpainter.inpaint(
                image,
                mask,
                use_lama=self.use_lama and self.lama_available
            )

            # 记录统计
            self._stats['processed'] += 1
            if success:
                self._stats['successful'] += 1
                if self.inpainter.fallback_used:
                    self._stats['opencv_used'] += 1
                else:
                    self._stats['lama_used'] += 1
            else:
                self._stats['failed'] += 1

            return success, result

        except Exception as e:
            print(f"[WatermarkRemover] 错误: {e}")
            import traceback
            traceback.print_exc()
            self._stats['failed'] += 1
            return False, image

    def remove_file(
        self,
        input_path: str,
        output_path: str,
        bbox: Tuple[int, int, int, int],
        mode: str = "normal",
        confidence: float = 0.8,
        config: Optional[RemovalConfig] = None
    ) -> Dict[str, Any]:
        """
        从文件去除水印（智能格式保持）

        Args:
            input_path: 输入图片路径
            output_path: 输出图片路径
            bbox: 水印区域
            mode: 处理模式
            confidence: 置信度
            config: 可选配置

        Returns:
            处理结果字典
        """
        import time
        start_time = time.time()

        try:
            # 读取图片（使用 PIL 处理中文路径和格式）
            from PIL import Image

            pil_img = Image.open(input_path)
            original_format = pil_img.format
            original_mode = pil_img.mode

            print(f"[WatermarkRemover] 处理: {os.path.basename(input_path)}")
            print(f"[WatermarkRemover] 原图格式: {original_format}, 模式: {original_mode}")

            # 处理透明通道
            has_alpha = original_mode in ('RGBA', 'LA', 'P')
            alpha_channel = None

            if has_alpha:
                # 转换为 RGBA 保持透明
                pil_img = pil_img.convert('RGBA')
                alpha_channel = pil_img.split()[3]
                # 创建白色背景用于处理
                white_bg = Image.new('RGB', pil_img.size, (255, 255, 255))
                white_bg.paste(pil_img, mask=alpha_channel)
                process_img = white_bg
            else:
                process_img = pil_img.convert('RGB')

            # 转 OpenCV BGR 格式
            image = cv2.cvtColor(np.array(process_img), cv2.COLOR_RGB2BGR)

            # 执行去除
            success, result = self.remove(image, bbox, mode, confidence, config)

            if not success:
                return {
                    'success': False,
                    'error': 'Removal failed',
                    'input_path': input_path,
                    'output_path': output_path
                }

            # 转回 PIL
            result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
            result_pil = Image.fromarray(result_rgb)

            # 恢复透明通道（如果有）
            if has_alpha and alpha_channel:
                # 关键修复：水印区域应该变为不透明（255）
                # 因为我们已经修复了这个区域
                alpha_array = np.array(alpha_channel)

                # 根据bbox创建掩码区域
                x1, y1, x2, y2 = bbox
                h, w = alpha_array.shape[:2]
                x1 = max(0, min(x1, w - 1))
                y1 = max(0, min(y1, h - 1))
                x2 = max(x1 + 1, min(x2, w))
                y2 = max(y1 + 1, min(y2, h))

                # 水印区域设为不透明
                alpha_array[y1:y2, x1:x2] = 255

                # 轻微羽化边缘，避免硬边
                from .adaptive import AdaptiveRemovalConfig
                feather_mask = np.zeros((h, w), dtype=np.uint8)
                feather_mask[y1:y2, x1:x2] = 255
                kernel = np.ones((5, 5), np.uint8)
                feather_mask = cv2.dilate(feather_mask, kernel, iterations=1)
                feather_mask = cv2.GaussianBlur(feather_mask, (9, 9), 2)

                # 边缘区域保持原透明度，内部设为255
                edge_mask = (feather_mask > 0) & (feather_mask < 255)
                inner_mask = feather_mask >= 255

                final_alpha = alpha_array.copy()
                final_alpha[inner_mask] = 255

                result_pil.putalpha(Image.fromarray(final_alpha.astype(np.uint8)))

            # 保存结果
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # 智能格式选择
            output_format = config.output_format if config else 'auto'

            # 判断是否应该使用PNG
            use_png = (output_format == 'png' or
                      (output_format == 'auto' and (has_alpha or original_format == 'PNG')))

            if use_png:
                # 保存为 PNG（无损+透明）
                result_pil.save(output_path, 'PNG', optimize=True)
                print(f"[WatermarkRemover] 保存为 PNG（无损+透明）")
            else:
                # 保存为 JPEG（高质量）
                # JPEG不支持透明，需要转换为RGB
                if result_pil.mode == 'RGBA':
                    # 创建白色背景
                    bg = Image.new('RGB', result_pil.size, (255, 255, 255))
                    bg.paste(result_pil, mask=result_pil.split()[3])  # 使用alpha通道作为mask
                    result_pil = bg
                elif result_pil.mode != 'RGB':
                    result_pil = result_pil.convert('RGB')

                quality = config.output_quality if config else 98
                result_pil.save(output_path, 'JPEG', quality=quality, optimize=True)
                print(f"[WatermarkRemover] 保存为 JPEG（质量{quality}）")

            processing_time = time.time() - start_time

            return {
                'success': True,
                'input_path': input_path,
                'output_path': output_path,
                'bbox': bbox,
                'mode': mode,
                'processing_time': round(processing_time, 3),
                'algorithm': 'LaMa' if (self.use_lama and not self.inpainter.fallback_used) else 'OpenCV'
            }

        except Exception as e:
            print(f"[WatermarkRemover] 错误: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'input_path': input_path,
                'output_path': output_path
            }

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self._stats.copy()

    def reset_stats(self):
        """重置统计"""
        self._stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'lama_used': 0,
            'opencv_used': 0
        }

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            'lama_available': self.lama_available,
            'use_lama': self.use_lama,
            'stats': self._stats,
            'inpainter': self.inpainter.get_status()
        }


class LegacyWatermarkRemover:
    """
    兼容现有 advanced_watermark_remover_fixed.py 的包装器

    如果用户想使用原有的精确坐标参数
    """

    def __init__(self):
        self.wrapper = WatermarkRemoverWrapper()

    def remove_with_margins(
        self,
        input_path: str,
        output_path: str,
        right_margin_percent: float = 5.0,
        bottom_margin_percent: float = 5.0,
        watermark_width_percent: float = 20.0,
        watermark_height_percent: float = 10.0,
        algorithm: str = "NS",
        inpaint_radius: int = 3
    ) -> bool:
        """
        使用边距参数去除水印（兼容旧接口）

        Args:
            input_path: 输入路径
            output_path: 输出路径
            right_margin_percent: 距离右边距百分比
            bottom_margin_percent: 距离底边距百分比
            watermark_width_percent: 水印宽度百分比
            watermark_height_percent: 水印高度百分比
            algorithm: 算法 NS/Telea
            inpaint_radius: 修复半径

        Returns:
            是否成功
        """
        try:
            # 读取图片
            from PIL import Image
            pil_img = Image.open(input_path)
            image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            h, w = image.shape[:2]

            # 计算水印区域
            x1 = int(w - w * (right_margin_percent / 100.0 + watermark_width_percent / 100.0))
            y1 = int(h - h * (bottom_margin_percent / 100.0 + watermark_height_percent / 100.0))
            x2 = int(w - w * right_margin_percent / 100.0)
            y2 = int(h - h * bottom_margin_percent / 100.0)

            bbox = (max(0, x1), max(0, y1), min(w, x2), min(h, y2))

            # 创建配置
            config = RemovalConfig(
                algorithm=algorithm,
                inpaint_radius=inpaint_radius,
                feather_radius=2,
                dilation_iterations=1
            )

            # 执行去除
            result = self.wrapper.remove_file(
                input_path,
                output_path,
                bbox,
                config=config
            )

            return result['success']

        except Exception as e:
            print(f"Legacy removal failed: {e}")
            return False
