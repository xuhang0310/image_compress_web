"""
多策略融合决策引擎

将多个检测策略的结果融合成最终的检测决策
"""

from typing import List, Dict, Tuple, Optional
import numpy as np

from .core import DetectionResult, FusionResult


class FusionEngine:
    """
    融合决策引擎

    综合多个策略的检测结果，输出最终的决策
    """

    # 策略权重配置（可调整）
    STRATEGY_WEIGHTS = {
        'position': 0.40,
        'color': 0.35,
        'texture': 0.15,
        'frequency': 0.10
    }

    # 置信度阈值
    THRESHOLDS = {
        'high': 0.80,      # 高置信度，正常处理
        'medium': 0.50,    # 中等置信度，保守模式
        'low': 0.30        # 低置信度，跳过
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        thresholds: Optional[Dict[str, float]] = None
    ):
        """
        初始化融合引擎

        Args:
            weights: 策略权重配置，默认使用 STRATEGY_WEIGHTS
            thresholds: 置信度阈值，默认使用 THRESHOLDS
        """
        self.weights = weights or self.STRATEGY_WEIGHTS.copy()
        self.thresholds = thresholds or self.THRESHOLDS.copy()

    def fuse(
        self,
        all_results: Dict[str, List[DetectionResult]]
    ) -> FusionResult:
        """
        融合多策略结果

        Args:
            all_results: 各策略检测结果 {strategy_name: [DetectionResult, ...]}

        Returns:
            FusionResult: 融合决策结果
        """
        # 收集所有候选框
        candidates = self._collect_candidates(all_results)

        if not candidates:
            return FusionResult(
                success=False,
                reason="No detection candidates"
            )

        # 计算候选框之间的 IoU 矩阵
        iou_matrix = self._compute_iou_matrix(candidates)

        # 聚类：找到重叠的候选框组
        clusters = self._cluster_by_iou(iou_matrix, threshold=0.5)

        if not clusters:
            # 没有重叠的候选框，选择单个置信度最高的
            best_candidate = max(candidates, key=lambda x: x['weighted_confidence'])
            return self._create_result_from_single(best_candidate, candidates)

        # 评估每个聚类
        best_cluster, best_score = self._select_best_cluster(candidates, clusters)

        if best_cluster is None or best_score < self.thresholds['low']:
            return FusionResult(
                success=False,
                reason=f"Confidence too low: {best_score:.2f}",
                confidence=best_score
            )

        # 融合最佳聚类内的所有框
        final_bbox = self._fuse_bboxes([candidates[i] for i in best_cluster])

        # 确定处理模式
        mode = self._determine_mode(best_score)

        # 收集贡献者信息
        contributors = list(set(
            candidates[i]['method'] for i in best_cluster
        ))

        return FusionResult(
            success=True,
            bbox=tuple(int(x) for x in final_bbox),
            confidence=round(best_score, 4),
            mode=mode,
            contributors=contributors
        )

    def _collect_candidates(
        self,
        all_results: Dict[str, List[DetectionResult]]
    ) -> List[Dict]:
        """
        收集所有候选框并计算加权置信度
        """
        candidates = []

        for strategy_name, results in all_results.items():
            weight = self.weights.get(strategy_name, 0.1)

            for r in results:
                candidates.append({
                    'bbox': r.bbox,
                    'confidence': r.confidence,
                    'weighted_confidence': r.confidence * weight,
                    'method': r.method,
                    'strategy': strategy_name,
                    'weight': weight,
                    'area': r.area
                })

        return candidates

    def _compute_iou_matrix(
        self,
        candidates: List[Dict]
    ) -> np.ndarray:
        """
        计算候选框之间的 IoU 矩阵
        """
        n = len(candidates)
        iou_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(i + 1, n):
                iou = self._calculate_iou(
                    candidates[i]['bbox'],
                    candidates[j]['bbox']
                )
                iou_matrix[i, j] = iou
                iou_matrix[j, i] = iou

        return iou_matrix

    def _calculate_iou(
        self,
        bbox1: Tuple[int, ...],
        bbox2: Tuple[int, ...]
    ) -> float:
        """
        计算两个边界框的 IoU
        """
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        # 计算交集
        xi1 = max(x1_1, x1_2)
        yi1 = max(y1_1, y1_2)
        xi2 = min(x2_1, x2_2)
        yi2 = min(y2_1, y2_2)

        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0

        inter_area = (xi2 - xi1) * (yi2 - yi1)
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)

        union_area = box1_area + box2_area - inter_area
        return inter_area / (union_area + 1e-6)

    def _cluster_by_iou(
        self,
        iou_matrix: np.ndarray,
        threshold: float = 0.5
    ) -> List[List[int]]:
        """
        基于 IoU 进行聚类

        使用并查集（Union-Find）算法
        """
        n = len(iou_matrix)
        if n == 0:
            return []

        parent = list(range(n))

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # 合并 IoU > threshold 的框
        for i in range(n):
            for j in range(i + 1, n):
                if iou_matrix[i, j] > threshold:
                    union(i, j)

        # 收集聚类结果
        clusters_dict: Dict[int, List[int]] = {}
        for i in range(n):
            root = find(i)
            if root not in clusters_dict:
                clusters_dict[root] = []
            clusters_dict[root].append(i)

        return list(clusters_dict.values())

    def _select_best_cluster(
        self,
        candidates: List[Dict],
        clusters: List[List[int]]
    ) -> Tuple[Optional[List[int]], float]:
        """
        选择最佳聚类
        """
        best_cluster = None
        best_score = 0.0

        for cluster in clusters:
            score = self._calculate_cluster_score(
                [candidates[i] for i in cluster]
            )

            if score > best_score:
                best_score = score
                best_cluster = cluster

        return best_cluster, best_score

    def _calculate_cluster_score(
        self,
        cluster_candidates: List[Dict]
    ) -> float:
        """
        计算聚类的综合得分

        考虑：
        1. 加权平均置信度
        2. 策略多样性奖励
        3. 框的一致性（IoU 越高越好）
        """
        # 加权平均置信度
        total_weight = sum(c['weight'] for c in cluster_candidates)
        if total_weight == 0:
            return 0.0

        weighted_conf = sum(
            c['weighted_confidence'] for c in cluster_candidates
        ) / total_weight

        # 策略多样性奖励
        unique_strategies = len(set(
            c['strategy'] for c in cluster_candidates
        ))
        diversity_bonus = 0.05 * (unique_strategies - 1)

        # 数量奖励（多个策略都检测到同一区域）
        count_bonus = 0.03 * min(len(cluster_candidates) - 1, 3)

        score = weighted_conf + diversity_bonus + count_bonus
        return min(score, 1.0)

    def _fuse_bboxes(
        self,
        candidates: List[Dict]
    ) -> Tuple[float, float, float, float]:
        """
        融合多个边界框

        使用加权平均
        """
        total_weight = sum(c['weight'] for c in candidates)

        x1 = sum(c['bbox'][0] * c['weight'] for c in candidates) / total_weight
        y1 = sum(c['bbox'][1] * c['weight'] for c in candidates) / total_weight
        x2 = sum(c['bbox'][2] * c['weight'] for c in candidates) / total_weight
        y2 = sum(c['bbox'][3] * c['weight'] for c in candidates) / total_weight

        return (x1, y1, x2, y2)

    def _determine_mode(self, score: float) -> str:
        """
        根据分数确定处理模式
        """
        if score >= self.thresholds['high']:
            return 'normal'
        elif score >= self.thresholds['medium']:
            return 'conservative'
        else:
            return 'low_confidence'

    def _create_result_from_single(
        self,
        candidate: Dict,
        all_candidates: List[Dict]
    ) -> FusionResult:
        """
        从单个最佳候选创建结果
        """
        confidence = candidate['confidence']
        mode = self._determine_mode(confidence)

        if confidence < self.thresholds['low']:
            return FusionResult(
                success=False,
                reason=f"Single candidate confidence too low: {confidence:.2f}",
                confidence=confidence
            )

        return FusionResult(
            success=True,
            bbox=candidate['bbox'],
            confidence=round(confidence, 4),
            mode=mode,
            contributors=[candidate['method']]
        )


class ConservativeFusionEngine(FusionEngine):
    """
    保守型融合引擎

    提高阈值，减少误检
    """

    THRESHOLDS = {
        'high': 0.85,
        'medium': 0.65,
        'low': 0.45
    }

    def __init__(self):
        super().__init__(thresholds=self.THRESHOLDS.copy())


class AggressiveFusionEngine(FusionEngine):
    """
    激进型融合引擎

    降低阈值，尽可能检测
    """

    THRESHOLDS = {
        'high': 0.70,
        'medium': 0.40,
        'low': 0.20
    }

    def __init__(self):
        super().__init__(thresholds=self.THRESHOLDS.copy())
