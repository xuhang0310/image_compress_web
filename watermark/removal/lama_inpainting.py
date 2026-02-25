"""
LaMa 深度学习修复模块

提供基于 LaMa (Large Mask Inpainting) 的高质量图像修复
效果远优于 OpenCV 传统算法

安装依赖:
    pip install lama-cleaner

模型会自动下载到: ~/.cache/lama-cleaner/
"""

import os
import sys
import cv2
import numpy as np
from typing import Tuple, Optional
from pathlib import Path


class LamaInpainter:
    """
    LaMa 深度学习修复器

    特点:
    - 基于 Large Mask Inpainting 模型
    - 对大面积修复效果好
    - 边缘自然，纹理合理
    - 支持 CPU/GPU 推理
    """

    def __init__(self, device: str = "cpu"):
        """
        初始化 LaMa 修复器

        Args:
            device: "cpu" 或 "cuda"
        """
        self.device = device
        self.model = None
        self._initialized = False

    def _init_model(self):
        """延迟初始化模型"""
        if self._initialized:
            return True

        try:
            # 尝试导入 lama-cleaner
            from lama_inpainting import load_model as lama_load_model

            print(f"[LaMa] 正在加载模型 (device={self.device})...")
            self.model = lama_load_model(device=self.device)
            self._initialized = True
            print("[LaMa] 模型加载完成")
            return True

        except ImportError:
            print("[LaMa] 警告: lama-cleaner 未安装，将使用 OpenCV 降级")
            print("[LaMa] 安装命令: pip install lama-cleaner")
            return False

        except Exception as e:
            print(f"[LaMa] 模型加载失败: {e}")
            return False

    def inpaint(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        resize_limit: int = 2048
    ) -> Tuple[bool, np.ndarray]:
        """
        使用 LaMa 修复图像

        Args:
            image: BGR 图像 (H, W, 3)
            mask: 单通道掩码 (H, W), 255=需要修复区域
            resize_limit: 最大边长限制，超过则缩放

        Returns:
            (success, result_image)
        """
        # 尝试初始化
        if not self._init_model():
            return False, image

        try:
            from lama_inpainting import inpaint_img_with_lama

            h, w = image.shape[:2]
            original_size = (w, h)

            # 检查是否需要缩放（大图处理慢）
            max_dim = max(h, w)
            scale = 1.0

            if max_dim > resize_limit:
                scale = resize_limit / max_dim
                new_w, new_h = int(w * scale), int(h * scale)
                image_resized = cv2.resize(image, (new_w, new_h))
                mask_resized = cv2.resize(mask, (new_w, new_h))
                print(f"[LaMa] 图片过大，缩放至 {new_w}x{new_h} 处理")
            else:
                image_resized = image
                mask_resized = mask

            # 确保格式正确
            # LaMa 期望 RGB 格式
            image_rgb = cv2.cvtColor(image_resized, cv2.COLOR_BGR2RGB)

            # 执行修复
            print("[LaMa] 开始修复...")
            result_rgb = inpaint_img_with_lama(
                image_rgb,
                mask_resized,
                self.model,
                device=self.device
            )
            print("[LaMa] 修复完成")

            # 转回 BGR
            result = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)

            # 如果缩放过，放大回原尺寸
            if scale < 1.0:
                result = cv2.resize(result, original_size)
                # 与原图融合，避免缩放造成的模糊
                mask_original = cv2.resize(mask, original_size)
                mask_inv = cv2.bitwise_not(mask_original)
                original_part = cv2.bitwise_and(image, image, mask=mask_inv)
                repair_part = cv2.bitwise_and(result, result, mask=mask_original)
                result = cv2.add(original_part, repair_part)

            return True, result

        except Exception as e:
            print(f"[LaMa] 修复失败: {e}")
            import traceback
            traceback.print_exc()
            return False, image

    def is_available(self) -> bool:
        """检查 LaMa 是否可用"""
        return self._init_model()


class HybridInpainter:
    """
    混合修复器

    优先使用 LaMa，不可用则降级到 OpenCV
    """

    def __init__(self, device: str = "cpu"):
        self.lama = LamaInpainter(device=device)
        self.fallback_used = False

    def inpaint(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        use_lama: bool = True,
        resize_limit: int = 2048
    ) -> Tuple[bool, np.ndarray]:
        """
        智能选择修复算法

        Args:
            image: BGR 图像
            mask: 修复掩码
            use_lama: 是否尝试使用 LaMa
            resize_limit: LaMa 处理尺寸限制

        Returns:
            (success, result)
        """
        if use_lama:
            # 尝试 LaMa
            success, result = self.lama.inpaint(image, mask, resize_limit)
            if success:
                self.fallback_used = False
                return True, result
            else:
                self.fallback_used = True
                print("[Hybrid] LaMa 失败，降级到 OpenCV")

        # 降级到 OpenCV
        print("[Hybrid] 使用 OpenCV Inpainting")
        return self._opencv_inpaint(image, mask)

    def _opencv_inpaint(
        self,
        image: np.ndarray,
        mask: np.ndarray
    ) -> Tuple[bool, np.ndarray]:
        """
        OpenCV 增强修复方案
        多尺度修复 + 边缘融合优化
        """
        try:
            h, w = image.shape[:2]
            mask_binary = (mask > 128).astype(np.uint8) * 255
            mask_area = np.sum(mask_binary > 0)
            total_area = h * w
            ratio = mask_area / total_area

            print(f"[Hybrid] 使用增强 OpenCV 修复 (水印占比: {ratio:.2%})")

            # 根据水印大小选择策略
            if ratio > 0.03:
                # 大水印：使用多尺度修复
                result = self._multi_scale_inpaint(image, mask_binary, ratio)
            else:
                # 小水印：单尺度优化修复
                result = self._optimized_single_inpaint(image, mask_binary, ratio)

            return True, result

        except Exception as e:
            print(f"[Hybrid] OpenCV 修复失败: {e}")
            import traceback
            traceback.print_exc()
            return False, image

    def _optimized_single_inpaint(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        ratio: float
    ) -> np.ndarray:
        """
        优化的单尺度修复
        """
        # 根据水印大小选择半径
        if ratio < 0.01:
            radius = 5
        elif ratio < 0.03:
            radius = 7
        else:
            radius = 9

        # 第一次修复：NS 算法保留细节
        result = cv2.inpaint(image, mask, radius, cv2.INPAINT_NS)

        # 第二次修复：小半径 Telea 平滑边缘
        result = cv2.inpaint(result, mask, max(2, radius // 2), cv2.INPAINT_TELEA)

        # 边缘融合优化
        result = self._edge_blending(image, result, mask)

        # 后处理：轻微锐化恢复细节
        result = self._sharpen_repair_area(image, result, mask)

        return result

    def _multi_scale_inpaint(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        ratio: float
    ) -> np.ndarray:
        """
        多尺度修复：先缩小修复再精修
        效果更平滑，适合大面积水印
        """
        h, w = image.shape[:2]

        # 计算缩放比例（保持最小边至少 512px）
        min_dim = min(h, w)
        if min_dim > 1024:
            scale = 512 / min_dim
        else:
            scale = 0.5

        new_w, new_h = int(w * scale), int(h * scale)

        # 缩小图像和掩码
        small = cv2.resize(image, (new_w, new_h))
        small_mask = cv2.resize(mask, (new_w, new_h))

        # 小图上修复（更平滑）
        # 小图使用较大半径，获得更好的平滑效果
        small_radius = max(3, int(5 * scale))
        result_small = cv2.inpaint(small, small_mask, small_radius, cv2.INPAINT_NS)

        # 放大回原尺寸
        result_up = cv2.resize(result_small, (w, h))

        # 与原图非掩码区域融合（保留原图细节）
        mask_inv = cv2.bitwise_not(mask)
        original_part = cv2.bitwise_and(image, image, mask=mask_inv)

        # 对修复区域进行轻微模糊，减少缩放带来的锯齿
        repair_blurred = cv2.GaussianBlur(result_up, (3, 3), 0.5)
        repair_part = cv2.bitwise_and(repair_blurred, repair_blurred, mask=mask)

        # 合并
        result = cv2.add(original_part, repair_part)

        # 小半径精修边缘（Telea 算法对边缘处理更好）
        result = cv2.inpaint(result, mask, 3, cv2.INPAINT_TELEA)

        # 最终边缘融合
        result = self._edge_blending(image, result, mask)

        return result

    def _edge_blending(
        self,
        original: np.ndarray,
        repaired: np.ndarray,
        mask: np.ndarray,
        blend_width: int = 10
    ) -> np.ndarray:
        """
        边缘融合：让修复区域与原图边界过渡更自然

        Args:
            original: 原图
            repaired: 修复后的图
            mask: 修复掩码
            blend_width: 融合带宽
        """
        # 创建边缘区域掩码
        kernel = np.ones((blend_width, blend_width), np.uint8)
        mask_dilated = cv2.dilate(mask, kernel, iterations=1)
        mask_eroded = cv2.erode(mask, kernel, iterations=1)

        # 边缘区域 = 膨胀后的掩码 - 腐蚀后的掩码
        edge_mask = cv2.subtract(mask_dilated, mask_eroded)

        # 对边缘区域进行高斯模糊（创建渐变权重）
        edge_mask_float = edge_mask.astype(np.float32) / 255.0
        edge_blurred = cv2.GaussianBlur(edge_mask_float, (blend_width * 2 + 1, blend_width * 2 + 1), blend_width)

        # 扩展维度用于广播
        edge_blurred = np.expand_dims(edge_blurred, axis=2)

        # 在边缘区域进行渐变混合
        # 边缘外 = 原图，边缘内 = 修复图，边缘上 = 渐变混合
        result = (original * (1 - edge_blurred) + repaired * edge_blurred).astype(np.uint8)

        # 非边缘区域：直接使用修复结果（掩码内）或原图（掩码外）
        mask_inv = cv2.bitwise_not(mask)
        outside_mask = cv2.bitwise_and(original, original, mask=mask_inv)
        inside_mask = cv2.bitwise_and(repaired, repaired, mask=mask)

        result = cv2.add(outside_mask, inside_mask)

        return result

    def _sharpen_repair_area(
        self,
        original: np.ndarray,
        repaired: np.ndarray,
        mask: np.ndarray,
        strength: float = 0.3
    ) -> np.ndarray:
        """
        对修复区域进行轻微锐化，恢复细节

        Args:
            original: 原图（水印图）
            repaired: 修复后的图
            mask: 修复掩码
            strength: 锐化强度 (0-1)
        """
        # 创建锐化核
        kernel = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ], dtype=np.float32)

        # 对修复区域进行锐化
        sharpened = cv2.filter2D(repaired, -1, kernel)

        # 只在修复区域内应用锐化，保持边缘外不变
        mask_float = mask.astype(np.float32) / 255.0
        mask_3ch = np.stack([mask_float] * 3, axis=2)

        # 混合：原修复结果 + 锐化效果 * 强度
        result = repaired * (1 - mask_3ch * strength) + sharpened * (mask_3ch * strength)
        result = np.clip(result, 0, 255).astype(np.uint8)

        return result

    def get_status(self) -> dict:
        """获取当前状态"""
        return {
            "lama_available": self.lama.is_available(),
            "fallback_used": self.fallback_used,
            "device": self.lama.device
        }


# 便捷函数
def inpaint_image(
    image: np.ndarray,
    mask: np.ndarray,
    method: str = "auto",
    device: str = "cpu"
) -> Tuple[bool, np.ndarray]:
    """
    便捷的图像修复函数

    Args:
        image: BGR 图像
        mask: 修复掩码
        method: "auto" | "lama" | "opencv"
        device: "cpu" | "cuda"

    Returns:
        (success, result)
    """
    if method == "opencv":
        # 纯 OpenCV
        hybrid = HybridInpainter(device=device)
        return hybrid._opencv_inpaint(image, mask)

    elif method == "lama":
        # 强制 LaMa
        lama = LamaInpainter(device=device)
        return lama.inpaint(image, mask)

    else:  # auto
        # 智能选择
        hybrid = HybridInpainter(device=device)
        return hybrid.inpaint(image, mask, use_lama=True)


# 安装检查
def check_lama_installation():
    """检查 LaMa 是否已安装"""
    try:
        import lama_inpainting
        return True
    except ImportError:
        return False


def print_install_guide():
    """打印安装指南"""
    print("""
========================================
LaMa 深度学习修复模型安装指南
========================================

1. 安装 lama-cleaner:
   pip install lama-cleaner

2. 首次运行会自动下载模型（约 500MB）:
   - 模型将下载到: ~/.cache/lama-cleaner/
   - 或: ~/.torch/iob/

3. GPU 加速（可选）:
   - 确保 CUDA 已安装
   - 使用 device="cuda"

4. 验证安装:
   python -c "from lama_inpainting import load_model; print('OK')"

========================================
""")


if __name__ == "__main__":
    # 测试
    print("LaMa 修复模块测试")

    if not check_lama_installation():
        print_install_guide()
        sys.exit(1)

    print(f"LaMa 已安装: {check_lama_installation()}")
