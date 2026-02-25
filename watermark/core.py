"""
全自动水印去除器

主入口类，整合检测、去除、批量处理功能
"""

import os
import time
import uuid
from typing import Optional, Dict, Any, Callable
from pathlib import Path

import cv2
import numpy as np

from .detector import WatermarkDetector, FusionResult
from .removal import WatermarkRemoverWrapper, RemovalConfig
from .batch import BatchProcessor, BatchTask


class AutoWatermarkRemover:
    """
    全自动水印去除器

    一键式水印检测与去除，无需人工干预

    使用示例:
        >>> remover = AutoWatermarkRemover()
        >>>
        >>> # 单张处理
        >>> result = remover.remove('input.jpg', 'output.jpg')
        >>> print(f"检测区域: {result['detection']['bbox']}")
        >>>
        >>> # 批量处理
        >>> task = remover.batch_remove('./input', './output')
        >>> task.wait_for_completion()
        >>> print(f"处理完成: {task.stats}")
    """

    def __init__(self):
        """初始化去除器"""
        self.detector = WatermarkDetector()
        self.remover = WatermarkRemoverWrapper()
        self.batch_processor = BatchProcessor()

    def remove(
        self,
        input_path: str,
        output_path: str,
        min_confidence: float = 0.5,
        visualize: bool = False,
        visualization_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        全自动去除单张图片水印

        Args:
            input_path: 输入图片路径
            output_path: 输出图片路径
            min_confidence: 最小置信度阈值
            visualize: 是否生成可视化结果
            visualization_path: 可视化结果保存路径

        Returns:
            处理结果字典
        """
        start_time = time.time()

        # 1. 检测水印
        detection = self.detector.detect_file(input_path, min_confidence)

        if not detection.success:
            return {
                'success': False,
                'error': detection.reason or "Detection failed",
                'input_path': input_path,
                'output_path': output_path,
                'detection': detection.to_dict()
            }

        # 2. 执行去除
        result = self.remover.remove_file(
            input_path,
            output_path,
            detection.bbox,
            mode=detection.mode,
            confidence=detection.confidence
        )

        # 3. 可选：生成可视化
        if visualize and detection.success:
            self._generate_visualization(
                input_path,
                detection,
                visualization_path
            )

        processing_time = time.time() - start_time

        return {
            'success': result['success'],
            'input_path': input_path,
            'output_path': output_path,
            'detection': detection.to_dict(),
            'processing_time': round(processing_time, 3),
            'visualization_path': visualization_path if visualize else None
        }

    def remove_image(
        self,
        image: np.ndarray,
        min_confidence: float = 0.5
    ) -> Dict[str, Any]:
        """
        直接处理 numpy 图像

        Args:
            image: BGR 格式图像
            min_confidence: 最小置信度阈值

        Returns:
            包含处理后图像的字典
        """
        # 1. 检测
        detection = self.detector.detect(image, min_confidence)

        if not detection.success:
            return {
                'success': False,
                'error': detection.reason or "Detection failed",
                'detection': detection.to_dict(),
                'image': image
            }

        # 2. 去除
        success, result_image = self.remover.remove(
            image,
            detection.bbox,
            mode=detection.mode,
            confidence=detection.confidence
        )

        return {
            'success': success,
            'detection': detection.to_dict(),
            'image': result_image
        }

    def batch_remove(
        self,
        input_folder: str,
        output_folder: str,
        skip_low_confidence: bool = True,
        progress_callback: Optional[Callable[[BatchTask], None]] = None
    ) -> BatchTask:
        """
        批量去除水印

        Args:
            input_folder: 输入文件夹
            output_folder: 输出文件夹
            skip_low_confidence: 是否跳过低置信度图片
            progress_callback: 进度回调函数

        Returns:
            BatchTask: 任务对象，可通过 get_task 查询进度
        """
        # 创建任务
        task = self.batch_processor.create_task(input_folder, output_folder)

        # 在后台线程执行
        import threading
        thread = threading.Thread(
            target=self._run_batch,
            args=(task, skip_low_confidence, progress_callback)
        )
        thread.daemon = True
        thread.start()

        return task

    def _run_batch(
        self,
        task: BatchTask,
        skip_low_confidence: bool,
        progress_callback: Optional[Callable[[BatchTask], None]]
    ):
        """执行批量处理"""
        self.batch_processor.process(task, skip_low_confidence, progress_callback)

    def get_task(self, task_id: str) -> Optional[BatchTask]:
        """
        获取批量任务状态

        Args:
            task_id: 任务ID

        Returns:
            BatchTask 或 None
        """
        return self.batch_processor.get_task(task_id)

    def detect_only(
        self,
        input_path: str,
        visualize: bool = False,
        output_vis_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        仅检测水印位置，不执行去除

        Args:
            input_path: 输入图片路径
            visualize: 是否生成可视化
            output_vis_path: 可视化输出路径

        Returns:
            检测结果
        """
        detection = self.detector.detect_file(input_path)

        vis_path = None
        if visualize and detection.success:
            vis_path = output_vis_path or f"/tmp/detection_{uuid.uuid4().hex[:8]}.jpg"
            self._generate_visualization(input_path, detection, vis_path)

        return {
            'success': detection.success,
            'detection': detection.to_dict(),
            'visualization_path': vis_path
        }

    def _generate_visualization(
        self,
        input_path: str,
        detection: FusionResult,
        output_path: str
    ):
        """生成检测可视化结果"""
        try:
            from PIL import Image
            pil_img = Image.open(input_path)
            image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

            vis_image = self.detector.visualize_detection(
                image,
                detection,
                save_path=output_path
            )

            return True
        except Exception as e:
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取处理统计"""
        return {
            'removal_stats': self.remover.get_stats(),
            'active_batch_tasks': len([
                t for t in self.batch_processor._tasks.values()
                if t.status == 'processing'
            ])
        }


class QuickWatermarkRemover:
    """
    快速水印去除器（简化版）

    针对固定位置水印的快速处理，跳过复杂检测
    """

    # 预设位置配置
    PRESETS = {
        'doubao_bottom_right': {
            'right_margin': 3,
            'bottom_margin': 3,
            'width_percent': 18,
            'height_percent': 8
        },
        'doubao_large': {
            'right_margin': 2,
            'bottom_margin': 2,
            'width_percent': 25,
            'height_percent': 12
        },
        'wenxin_bottom': {
            'bottom_margin': 2,
            'width_percent': 30,
            'height_percent': 10
        }
    }

    def __init__(self, preset: str = 'doubao_bottom_right'):
        """
        初始化快速去除器

        Args:
            preset: 预设名称，默认 'doubao_bottom_right'
        """
        self.preset = self.PRESETS.get(preset, self.PRESETS['doubao_bottom_right'])
        self.remover = WatermarkRemoverWrapper()

    def remove(
        self,
        input_path: str,
        output_path: str
    ) -> bool:
        """
        快速去除水印

        使用预设位置，跳过检测步骤
        """
        try:
            from PIL import Image
            pil_img = Image.open(input_path)
            image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            h, w = image.shape[:2]

            # 计算水印区域
            cfg = self.preset
            if 'right_margin' in cfg:
                x1 = int(w - w * (cfg['right_margin'] / 100 + cfg['width_percent'] / 100))
                y1 = int(h - h * (cfg['bottom_margin'] / 100 + cfg['height_percent'] / 100))
                x2 = int(w - w * cfg['right_margin'] / 100)
                y2 = int(h - h * cfg['bottom_margin'] / 100)
            else:
                # 底部居中
                ww = int(w * cfg['width_percent'] / 100)
                hh = int(h * cfg['height_percent'] / 100)
                x1 = (w - ww) // 2
                y1 = h - int(h * cfg['bottom_margin'] / 100) - hh
                x2 = x1 + ww
                y2 = y1 + hh

            bbox = (max(0, x1), max(0, y1), min(w, x2), min(h, y2))

            # 直接去除
            result = self.remover.remove_file(input_path, output_path, bbox)
            return result['success']

        except Exception as e:
            return False
