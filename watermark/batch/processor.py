"""
批量处理器

智能批量水印去除，支持：
- 自动位置检测和一致性检查
- 进度跟踪
- 错误处理和降级
"""

import os
import time
import random
import threading
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class BatchTask:
    """批量处理任务"""
    task_id: str
    input_folder: str
    output_folder: str
    status: str = "pending"  # pending/processing/completed/failed
    total_files: int = 0
    processed: int = 0
    successful: int = 0
    skipped: int = 0
    failed: int = 0
    current_file: str = ""
    message: str = ""
    average_confidence: float = 0.0
    detections: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'status': self.status,
            'progress': {
                'total': self.total_files,
                'processed': self.processed,
                'successful': self.successful,
                'skipped': self.skipped,
                'failed': self.failed,
                'percentage': round(self.processed / self.total_files * 100, 1) if self.total_files > 0 else 0
            },
            'current_file': self.current_file,
            'message': self.message,
            'average_confidence': round(self.average_confidence, 4),
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'duration': round(time.time() - self.created_at, 1) if self.status != 'completed' else round(self.completed_at - self.created_at, 1)
        }

    def update(self, **kwargs):
        """更新任务状态（线程安全）"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)

    def complete(self, status: str = "completed"):
        """完成任务"""
        with self._lock:
            self.status = status
            self.completed_at = time.time()


class BatchProcessor:
    """
    批量处理器

    智能优化策略：
    1. 抽样检测前 N 张图片，确定统一位置
    2. 位置一致性高的批量使用统一位置
    3. 位置不一致的单独检测
    """

    # 默认配置
    DEFAULT_SAMPLE_SIZE = 3
    POSITION_TOLERANCE = 0.05  # 5% 偏差容忍
    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}

    def __init__(
        self,
        sample_size: int = DEFAULT_SAMPLE_SIZE,
        position_tolerance: float = POSITION_TOLERANCE
    ):
        """
        初始化批量处理器

        Args:
            sample_size: 抽样数量
            position_tolerance: 位置一致性偏差阈值
        """
        self.sample_size = sample_size
        self.position_tolerance = position_tolerance
        self._tasks: Dict[str, BatchTask] = {}
        self._task_counter = 0
        self._lock = threading.Lock()

    def create_task(
        self,
        input_folder: str,
        output_folder: str
    ) -> BatchTask:
        """
        创建批量处理任务

        Args:
            input_folder: 输入文件夹
            output_folder: 输出文件夹

        Returns:
            BatchTask: 任务对象
        """
        with self._lock:
            self._task_counter += 1
            task_id = f"batch_{int(time.time())}_{self._task_counter}"

        task = BatchTask(
            task_id=task_id,
            input_folder=input_folder,
            output_folder=output_folder
        )

        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[BatchTask]:
        """获取任务"""
        return self._tasks.get(task_id)

    def process(
        self,
        task: BatchTask,
        skip_low_confidence: bool = True,
        progress_callback: Optional[Callable[[BatchTask], None]] = None
    ) -> BatchTask:
        """
        执行批量处理

        Args:
            task: 任务对象
            skip_low_confidence: 是否跳过低置信度图片
            progress_callback: 进度回调函数

        Returns:
            完成的任务
        """
        try:
            task.update(status="processing", message="正在扫描文件...")

            # 1. 获取图片列表
            image_files = self._scan_images(task.input_folder)
            task.update(total_files=len(image_files))

            if not image_files:
                task.update(message="未找到图片文件", status="completed")
                return task

            # 2. 智能位置检测（抽样）
            task.update(message="正在检测水印位置...")
            unified_bbox = self._detect_unified_position(
                image_files,
                task
            )

            # 3. 批量处理
            task.update(message="开始批量去除...")
            self._process_batch(
                image_files,
                task,
                unified_bbox,
                skip_low_confidence,
                progress_callback
            )

            # 4. 完成
            task.complete("completed")
            return task

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            task.update(
                status="failed",
                message=f"处理失败: {str(e)}"
            )
            task.complete("failed")
            return task

    def _scan_images(self, folder: str) -> List[str]:
        """
        扫描文件夹中的图片

        Returns:
            图片路径列表（按文件名排序）
        """
        if not os.path.exists(folder):
            return []

        files = []
        for f in os.listdir(folder):
            ext = Path(f).suffix.lower()
            if ext in self.SUPPORTED_EXTENSIONS:
                files.append(os.path.join(folder, f))

        return sorted(files)

    def _detect_unified_position(
        self,
        image_files: List[str],
        task: BatchTask
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        检测统一的水印位置

        策略：
        1. 随机抽样 sample_size 张图片
        2. 分别检测水印位置
        3. 计算位置一致性
        4. 如果偏差 < tolerance，返回平均位置
        5. 否则返回 None（每张单独检测）
        """
        from ..detector import WatermarkDetector

        sample_size = min(self.sample_size, len(image_files))
        sample_files = random.sample(image_files, sample_size)

        detector = WatermarkDetector()
        detections = []

        for img_path in sample_files:
            try:
                result = detector.detect_file(img_path)
                if result.success and result.bbox:
                    detections.append({
                        'file': img_path,
                        'bbox': result.bbox,
                        'confidence': result.confidence
                    })
            except Exception as e:
                logger.warning(f"Detection failed for {img_path}: {e}")

        task.detections = detections

        if len(detections) < 2:
            return None  # 样本不足，单独检测

        # 检查位置一致性
        bboxes = [d['bbox'] for d in detections]
        if self._check_position_consistency(bboxes):
            # 计算平均位置
            avg_bbox = self._average_bboxes(bboxes)
            logger.info(f"Unified position detected: {avg_bbox}")
            return avg_bbox

        return None

    def _check_position_consistency(
        self,
        bboxes: List[Tuple[int, int, int, int]]
    ) -> bool:
        """
        检查位置一致性

        计算各框之间的相对位置偏差
        """
        if len(bboxes) < 2:
            return False

        # 计算归一化坐标（相对图片中心）
        normalized = []
        for x1, y1, x2, y2 in bboxes:
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            w = x2 - x1
            h = y2 - y1
            normalized.append((cx, cy, w, h))

        # 计算相对偏差
        for i in range(len(normalized)):
            for j in range(i + 1, len(normalized)):
                cx1, cy1, w1, h1 = normalized[i]
                cx2, cy2, w2, h2 = normalized[j]

                # 中心点相对偏差
                c_diff = abs(cx1 - cx2) / max(cx1, cx2) + abs(cy1 - cy2) / max(cy1, cy2)
                # 尺寸相对偏差
                s_diff = abs(w1 - w2) / max(w1, w2) + abs(h1 - h2) / max(h1, h2)

                if (c_diff / 2) > self.position_tolerance or (s_diff / 2) > self.position_tolerance:
                    return False

        return True

    def _average_bboxes(
        self,
        bboxes: List[Tuple[int, int, int, int]]
    ) -> Tuple[int, int, int, int]:
        """计算平均边界框"""
        n = len(bboxes)
        x1 = sum(b[0] for b in bboxes) // n
        y1 = sum(b[1] for b in bboxes) // n
        x2 = sum(b[2] for b in bboxes) // n
        y2 = sum(b[3] for b in bboxes) // n
        return (x1, y1, x2, y2)

    def _process_batch(
        self,
        image_files: List[str],
        task: BatchTask,
        unified_bbox: Optional[Tuple[int, int, int, int]],
        skip_low_confidence: bool,
        progress_callback: Optional[Callable[[BatchTask], None]]
    ):
        """
        批量处理图片
        """
        from ..detector import WatermarkDetector
        from ..removal import WatermarkRemoverWrapper

        detector = WatermarkDetector()
        remover = WatermarkRemoverWrapper()

        confidences = []

        for i, img_path in enumerate(image_files):
            task.update(
                current_file=os.path.basename(img_path),
                processed=i
            )

            try:
                # 确定水印位置
                if unified_bbox:
                    # 使用统一位置
                    bbox = unified_bbox
                    detection_confidence = 0.85  # 抽样确定的置信度
                    mode = "normal"
                else:
                    # 单独检测
                    detection = detector.detect_file(img_path)
                    if not detection.success:
                        if skip_low_confidence:
                            task.skipped += 1
                            continue
                        else:
                            task.errors.append(f"{img_path}: 检测失败")
                            task.failed += 1
                            continue

                    bbox = detection.bbox
                    detection_confidence = detection.confidence
                    mode = detection.mode

                # 检查置信度
                if skip_low_confidence and detection_confidence < 0.5:
                    task.skipped += 1
                    continue

                confidences.append(detection_confidence)

                # 构建输出路径
                rel_path = os.path.relpath(img_path, task.input_folder)
                output_path = os.path.join(task.output_folder, rel_path)
                output_dir = os.path.dirname(output_path)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)

                # 执行去除
                result = remover.remove_file(
                    img_path,
                    output_path,
                    bbox,
                    mode=mode,
                    confidence=detection_confidence
                )

                if result['success']:
                    task.successful += 1
                else:
                    task.failed += 1
                    task.errors.append(f"{img_path}: {result.get('error', 'Unknown')}")

            except Exception as e:
                logger.error(f"Failed to process {img_path}: {e}")
                task.failed += 1
                task.errors.append(f"{img_path}: {str(e)}")

            # 更新平均置信度
            if confidences:
                task.average_confidence = sum(confidences) / len(confidences)

            # 进度回调
            if progress_callback:
                progress_callback(task)

        task.update(processed=len(image_files))

    def cleanup_old_tasks(self, max_age: float = 3600):
        """
        清理旧任务

        Args:
            max_age: 最大保留时间（秒）
        """
        current_time = time.time()
        to_remove = []

        for task_id, task in self._tasks.items():
            if current_time - task.created_at > max_age:
                to_remove.append(task_id)

        for task_id in to_remove:
            del self._tasks[task_id]
