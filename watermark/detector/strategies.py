"""
水印检测策略实现

包含：
- PositionStrategy: 基于固定位置的检测策略
- ColorStrategy: 基于颜色特征的检测策略
- TextureStrategy: 基于纹理特征的检测策略
"""

from typing import List, Tuple, Optional, Dict, Any
from abc import ABC, abstractmethod
import numpy as np
import cv2

from .core import DetectionResult


class BaseStrategy(ABC):
    """检测策略基类"""

    @abstractmethod
    def detect(self, image: np.ndarray) -> List[DetectionResult]:
        """执行检测"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """获取策略名称"""
        pass


class PositionStrategy(BaseStrategy):
    """
    基于固定位置的检测策略

    针对 AI 生成图片常见的水印位置（右下角、左下角等）进行检测
    """

    # 预定义常见水印位置（按出现频率排序）
    POSITION_PRESETS = [
        {
            'name': 'bottom-right-1',
            'desc': '右下角标准位置',
            'right_margin': 3,
            'bottom_margin': 3,
            'width_percent': 18,
            'height_percent': 8,
            'priority': 1
        },
        {
            'name': 'bottom-right-2',
            'desc': '右下角较大水印',
            'right_margin': 2,
            'bottom_margin': 2,
            'width_percent': 25,
            'height_percent': 12,
            'priority': 2
        },
        {
            'name': 'bottom-left',
            'desc': '左下角水印',
            'left_margin': 3,
            'bottom_margin': 3,
            'width_percent': 18,
            'height_percent': 8,
            'priority': 3
        },
        {
            'name': 'bottom-center',
            'desc': '底部居中',
            'bottom_margin': 2,
            'width_percent': 30,
            'height_percent': 10,
            'centered': True,
            'priority': 4
        },
        {
            'name': 'top-right',
            'desc': '右上角水印',
            'right_margin': 3,
            'top_margin': 3,
            'width_percent': 15,
            'height_percent': 8,
            'priority': 5
        }
    ]

    def __init__(self, presets: Optional[List[Dict]] = None):
        """
        初始化位置策略

        Args:
            presets: 自定义位置配置列表，默认使用 POSITION_PRESETS
        """
        self.presets = presets or self.POSITION_PRESETS

    def get_name(self) -> str:
        return "position"

    def detect(self, image: np.ndarray) -> List[DetectionResult]:
        """
        执行位置检测

        Returns:
            候选位置列表，按优先级排序
        """
        h, w = image.shape[:2]
        results = []

        for preset in self.presets:
            bbox = self._calculate_bbox(w, h, preset)

            # 验证边界
            if not self._validate_bbox(bbox, w, h):
                continue

            # 提取 ROI
            x1, y1, x2, y2 = bbox
            roi = image[y1:y2, x1:x2]

            # 基础置信度（基于位置的合理性）
            # 优先级越高，基础置信度越高
            base_confidence = 0.6 - (preset['priority'] - 1) * 0.1

            # 根据 ROI 特征微调置信度
            adjusted_confidence = self._adjust_confidence_by_roi(
                roi, base_confidence
            )

            results.append(DetectionResult(
                bbox=bbox,
                confidence=adjusted_confidence,
                method=f"position:{preset['name']}",
                roi=roi,
                metadata={'preset': preset}
            ))

        # 按置信度排序
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

    def _calculate_bbox(self, width: int, height: int, preset: Dict) -> Tuple[int, int, int, int]:
        """
        根据预设计算边界框

        Args:
            width: 图片宽度
            height: 图片高度
            preset: 位置预设配置

        Returns:
            (x1, y1, x2, y2) 边界框坐标
        """
        if 'centered' in preset and preset['centered']:
            # 居中位置
            w = int(width * preset['width_percent'] / 100)
            h = int(height * preset['height_percent'] / 100)
            x1 = (width - w) // 2
            y1 = height - int(height * preset['bottom_margin'] / 100) - h
            x2 = x1 + w
            y2 = y1 + h
        elif 'left_margin' in preset:
            # 左下角
            w = int(width * preset['width_percent'] / 100)
            h = int(height * preset['height_percent'] / 100)
            x1 = int(width * preset['left_margin'] / 100)
            y1 = height - int(height * preset['bottom_margin'] / 100) - h
            x2 = x1 + w
            y2 = y1 + h
        elif 'top_margin' in preset:
            # 右上角
            w = int(width * preset['width_percent'] / 100)
            h = int(height * preset['height_percent'] / 100)
            x1 = width - int(width * preset['right_margin'] / 100) - w
            y1 = int(height * preset['top_margin'] / 100)
            x2 = x1 + w
            y2 = y1 + h
        else:
            # 右下角（默认）
            w = int(width * preset['width_percent'] / 100)
            h = int(height * preset['height_percent'] / 100)
            x1 = width - int(width * preset['right_margin'] / 100) - w
            y1 = height - int(height * preset['bottom_margin'] / 100) - h
            x2 = x1 + w
            y2 = y1 + h

        return (max(0, x1), max(0, y1), min(width, x2), min(height, y2))

    def _validate_bbox(self, bbox: Tuple[int, ...], width: int, height: int) -> bool:
        """验证边界框是否有效"""
        x1, y1, x2, y2 = bbox

        # 基本检查
        if x2 <= x1 or y2 <= y1:
            return False

        # 大小检查（不能太小区或太大）
        area = (x2 - x1) * (y2 - y1)
        img_area = width * height

        if area < 100:  # 小于 100 像素
            return False
        if area > img_area * 0.4:  # 大于 40% 图片面积
            return False

        return True

    def _adjust_confidence_by_roi(
        self,
        roi: np.ndarray,
        base_confidence: float
    ) -> float:
        """
        根据 ROI 特征调整置信度

        检查：
        1. ROI 是否包含明显的边缘（可能是文字）
        2. ROI 颜色是否均匀（可能是纯色水印背景）
        """
        if roi.size == 0:
            return base_confidence * 0.5

        # 计算边缘密度
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        # 计算颜色方差（低方差可能是纯色背景）
        color_std = np.std(gray)

        # 调整逻辑：
        # - 中等边缘密度 (+0.1)：可能是文字
        # - 低颜色方差 (+0.05)：可能是纯色水印
        adjustment = 0
        if 0.05 < edge_density < 0.3:
            adjustment += 0.1
        if color_std < 40:
            adjustment += 0.05

        return min(base_confidence + adjustment, 0.95)


class ColorStrategy(BaseStrategy):
    """
    基于颜色特征的检测策略

    检测常见的水印颜色：白色半透明、浅灰色、品牌蓝色等
    """

    # 常见水印颜色特征配置
    COLOR_PROFILES = {
        'white_semi': {
            'hsv_lower': np.array([0, 0, 180]),
            'hsv_upper': np.array([180, 80, 255]),
            'min_ratio': 0.25,
            'desc': '白色半透明'
        },
        'light_gray': {
            'hsv_lower': np.array([0, 0, 140]),
            'hsv_upper': np.array([180, 60, 220]),
            'min_ratio': 0.20,
            'desc': '浅灰色'
        },
        'brand_blue': {
            'hsv_lower': np.array([100, 50, 150]),
            'hsv_upper': np.array([140, 255, 255]),
            'min_ratio': 0.15,
            'desc': '品牌蓝色'
        },
        'dark_text': {
            'hsv_lower': np.array([0, 0, 0]),
            'hsv_upper': np.array([180, 255, 80]),
            'min_ratio': 0.10,
            'desc': '深色文字'
        }
    }

    def __init__(self, profiles: Optional[Dict[str, Dict]] = None):
        """
        初始化颜色策略

        Args:
            profiles: 自定义颜色配置，默认使用 COLOR_PROFILES
        """
        self.profiles = profiles or self.COLOR_PROFILES

    def get_name(self) -> str:
        return "color"

    def detect(self, image: np.ndarray) -> List[DetectionResult]:
        """
        执行颜色检测

        在全图范围内搜索颜色特征匹配的区域
        """
        h, w = image.shape[:2]
        results = []

        for profile_name, profile in self.profiles.items():
            # 颜色分割
            mask = self._color_segment(image, profile)

            # 查找连通区域
            contours = self._find_contours(mask)

            for contour in contours:
                x, y, cw, ch = cv2.boundingRect(contour)
                bbox = (x, y, x + cw, y + ch)

                # 过滤太小或太大的区域
                area_ratio = (cw * ch) / (w * h)
                if not (0.002 < area_ratio < 0.3):
                    continue

                # 过滤不在边缘的区域（水印通常在边缘）
                edge_distance = min(
                    x, y,              # 距离左/上
                    w - (x + cw),      # 距离右
                    h - (y + ch)       # 距离下
                )
                edge_ratio = edge_distance / max(w, h)
                if edge_ratio > 0.15:  # 距离边缘超过 15%
                    continue

                # 计算置信度
                confidence = self._calculate_confidence(
                    image, bbox, profile, mask
                )

                if confidence > 0.3:
                    results.append(DetectionResult(
                        bbox=bbox,
                        confidence=confidence,
                        method=f"color:{profile_name}",
                        mask=mask[y:y+ch, x:x+cw]
                    ))

        # 按置信度排序
        results.sort(key=lambda x: x.confidence, reverse=True)

        # 返回 top 5，避免过多结果
        return results[:5]

    def _color_segment(self, image: np.ndarray, profile: Dict) -> np.ndarray:
        """
        颜色分割

        Args:
            image: BGR 图像
            profile: 颜色配置

        Returns:
            二值掩码
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(
            hsv,
            profile['hsv_lower'],
            profile['hsv_upper']
        )

        # 形态学操作去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        return mask

    def _find_contours(self, mask: np.ndarray) -> List[np.ndarray]:
        """
        查找连通区域

        过滤条件：
        - 面积足够大
        - 宽高比合理（水印通常是横向或纵向文字）
        """
        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        valid_contours = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 100:  # 太小忽略
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            if w == 0 or h == 0:
                continue

            aspect_ratio = max(w / h, h / w)
            if aspect_ratio > 15:  # 太细长忽略
                continue

            valid_contours.append(cnt)

        # 按面积排序
        valid_contours.sort(key=cv2.contourArea, reverse=True)
        return valid_contours

    def _calculate_confidence(
        self,
        image: np.ndarray,
        bbox: Tuple[int, ...],
        profile: Dict,
        mask: np.ndarray
    ) -> float:
        """
        计算颜色匹配置信度
        """
        x1, y1, x2, y2 = bbox
        roi = image[y1:y2, x1:x2]
        roi_mask = mask[y1:y2, x1:x2]

        if roi.size == 0:
            return 0.0

        # 计算匹配像素比例
        match_ratio = np.sum(roi_mask > 0) / roi_mask.size

        # 基础置信度
        base_conf = 0.3

        # 颜色匹配度
        match_score = min(match_ratio / profile['min_ratio'], 1.0) * 0.5

        # 边缘位置奖励（水印通常在边缘）
        h, w = image.shape[:2]
        is_near_edge = (
            x1 < w * 0.1 or
            x2 > w * 0.9 or
            y1 < h * 0.1 or
            y2 > h * 0.9
        )
        edge_bonus = 0.2 if is_near_edge else 0

        confidence = base_conf + match_score + edge_bonus
        return min(confidence, 0.95)


class TextureStrategy(BaseStrategy):
    """
    基于纹理特征的检测策略

    检测边缘密度较高的区域（文字型水印特征）
    """

    def __init__(
        self,
        window_sizes: Optional[List[Tuple[int, int]]] = None,
        edge_threshold: float = 0.1
    ):
        """
        初始化纹理策略

        Args:
            window_sizes: 滑动窗口大小列表，默认 [(40, 120), (60, 180)]
            edge_threshold: 边缘密度阈值
        """
        self.window_sizes = window_sizes or [(40, 120), (60, 180)]
        self.edge_threshold = edge_threshold

    def get_name(self) -> str:
        return "texture"

    def detect(self, image: np.ndarray) -> List[DetectionResult]:
        """
        执行纹理检测

        使用滑动窗口分析边缘密度
        """
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 边缘检测
        edges = cv2.Canny(gray, 50, 150)

        all_results = []

        for win_h, win_w in self.window_sizes:
            results = self._detect_with_window(edges, win_h, win_w, w, h)
            all_results.extend(results)

        # 按置信度排序并去重
        all_results.sort(key=lambda x: x.confidence, reverse=True)
        filtered_results = self._remove_duplicates(all_results, iou_threshold=0.5)

        return filtered_results[:5]

    def _detect_with_window(
        self,
        edges: np.ndarray,
        win_h: int,
        win_w: int,
        img_w: int,
        img_h: int
    ) -> List[DetectionResult]:
        """使用指定窗口大小检测"""
        results = []
        step = max(win_h, win_w) // 2  # 50% 重叠

        hotspots = []

        for y in range(0, img_h - win_h, step):
            for x in range(0, img_w - win_w, step):
                window = edges[y:y+win_h, x:x+win_w]
                edge_density = np.sum(window > 0) / window.size

                if edge_density > self.edge_threshold:
                    # 距离边缘越近分数越高
                    dist_to_right = img_w - (x + win_w)
                    dist_to_bottom = img_h - (y + win_h)
                    is_near_edge = min(x, y, dist_to_right, dist_to_bottom) < max(img_w, img_h) * 0.15

                    if is_near_edge:
                        hotspots.append((x, y, edge_density))

        # 对热点进行非极大值抑制
        hotspots = self._nms(hotspots, win_w, win_h)

        for x, y, density in hotspots:
            bbox = (x, y, x + win_w, y + win_h)

            # 计算边缘模式分数（文字通常有水平条纹）
            pattern_score = self._analyze_pattern(edges[y:y+win_h, x:x+win_w])

            confidence = 0.4 * min(density / 0.2, 1.0) + 0.6 * pattern_score

            if confidence > 0.4:
                results.append(DetectionResult(
                    bbox=bbox,
                    confidence=confidence,
                    method=f"texture:window_{win_h}x{win_w}"
                ))

        return results

    def _analyze_pattern(self, edge_patch: np.ndarray) -> float:
        """
        分析边缘模式，文字通常有水平条纹特征
        """
        # 水平投影
        h_proj = np.sum(edge_patch, axis=1)

        # 归一化
        if np.max(h_proj) > 0:
            h_proj = h_proj / np.max(h_proj)

        # 计算方差（有条纹的方差较大）
        variance = np.var(h_proj)

        # 转换为分数
        return min(variance * 5, 0.95)

    def _nms(
        self,
        hotspots: List[Tuple[int, int, float]],
        win_w: int,
        win_h: int
    ) -> List[Tuple[int, int, float]]:
        """非极大值抑制"""
        if not hotspots:
            return []

        # 按密度排序
        hotspots.sort(key=lambda x: x[2], reverse=True)

        suppressed = []
        used = set()

        for i, (x1, y1, density) in enumerate(hotspots):
            if i in used:
                continue

            suppressed.append((x1, y1, density))

            # 抑制邻近区域
            for j, (x2, y2, _) in enumerate(hotspots[i+1:], start=i+1):
                if j in used:
                    continue
                dist = np.sqrt((x1 - x2)**2 + (y1 - y2)**2)
                if dist < max(win_w, win_h):
                    used.add(j)

        return suppressed

    def _remove_duplicates(
        self,
        results: List[DetectionResult],
        iou_threshold: float = 0.5
    ) -> List[DetectionResult]:
        """使用 IoU 去重"""
        if not results:
            return []

        filtered = [results[0]]

        for r in results[1:]:
            is_duplicate = False
            for f in filtered:
                if self._calculate_iou(r.bbox, f.bbox) > iou_threshold:
                    is_duplicate = True
                    break
            if not is_duplicate:
                filtered.append(r)

        return filtered

    def _calculate_iou(
        self,
        bbox1: Tuple[int, ...],
        bbox2: Tuple[int, ...]
    ) -> float:
        """计算 IoU"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        xi1 = max(x1_1, x1_2)
        yi1 = max(y1_1, y1_2)
        xi2 = min(x2_1, x2_2)
        yi2 = min(y2_1, y2_2)

        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0

        inter_area = (xi2 - xi1) * (yi2 - yi1)
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)

        return inter_area / (box1_area + box2_area - inter_area + 1e-6)
