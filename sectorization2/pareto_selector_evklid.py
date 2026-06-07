from typing import List, Optional
from sectorization2.pareto_interface import ParetoPoint
import numpy as np


class DistanceBasedSelector:
    """Выбор по евклидову расстоянию до идеальной точки (0 imbalance, 0 degradation, MAX traffic)."""

    def select(self, points: List[ParetoPoint]) -> Optional[ParetoPoint]:
        if not points:
            return None

        min_imb, max_imb = min(p.imbalance for p in points), max(p.imbalance for p in points)
        min_deg, max_deg = min(p.degradation for p in points), max(p.degradation for p in points)
        min_traf, max_traf = min(p.traffic for p in points), max(p.traffic for p in points)

        best_point = None
        min_distance = float('inf')

        for point in points:
            # Нормализация [0, 1]
            # Находим диапазоны каждого критерия. Для нормализации нужно знать минимум и максимум по каждому измерению
            # (imbalance, degradation, traffic) среди всех точек фронта.
            # Это позволит привести все значения к единой шкале [0, 1].
            imb_norm = (point.imbalance - min_imb) / (max_imb - min_imb) if max_imb != min_imb else 0
            deg_norm = (point.degradation - min_deg) / (max_deg - min_deg) if max_deg != min_deg else 0
            traf_norm = (point.traffic - min_traf) / (max_traf - min_traf) if max_traf != min_traf else 0

            # ✅ РАССТОЯНИЕ ДО ТОЧКИ (0, 0, 1)
            distance = np.sqrt(
                imb_norm ** 2 +
                deg_norm ** 2 +       # расстояние от текущего до ИДЕАЛА 0 deg_norm²
                (1 - traf_norm) ** 2  # расстояние от текущего до ИДЕАЛА 1 (1 - traf_norm)²
            )

            if distance < min_distance:
                min_distance = distance
                best_point = point

        return best_point

