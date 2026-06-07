from dataclasses import dataclass
from typing import List, Optional, Dict, Protocol
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go


# ==============================================================================
# 1. МОДЕЛИ ДАННЫХ (DTO)
# Используем dataclass для строгой типизации и иммутабельности (SRP)
# ==============================================================================
@dataclass(frozen=True)
class ParetoPoint:
    azimuth: int
    imbalance: float
    degradation: float
    traffic: float
    cluster_id: str  # Идентификатор источника (важно для мульти-кластерного анализа)


# ==============================================================================
# 2. ИНТЕРФЕЙСЫ (Protocols) - DIP и ISP
# ==============================================================================
class ParetoFilterStrategy(Protocol):
    """Стратегия фильтрации недоминируемых решений."""

    def filter(self, points: List[ParetoPoint]) -> List[ParetoPoint]:
        ...


class ParetoFrontProvider(Protocol):
    """Интерфейс для любого источника, который может выдать Парето-фронт."""

    @property
    def cluster_id(self) -> str: ...

    def get_front(self) -> List[ParetoPoint]: ...


# ==============================================================================
# 3. КОНКРЕТНЫЕ РЕАЛИЗАЦИИ СТРАТЕГИЙ (OCP, LSP)
# ==============================================================================
class StandardParetoFilter:
    """Классический O(N^2) фильтр Парето-доминирования."""

    def filter(self, points: List[ParetoPoint]) -> List[ParetoPoint]:
        pareto = []
        for i, point_i in enumerate(points):
            dominated = False
            for j, point_j in enumerate(points):
                if i == j:
                    continue

                # Минимизируем imbalance и degradation, максимизируем traffic
                f1_better = point_j.imbalance <= point_i.imbalance
                f2_better = point_j.degradation <= point_i.degradation
                f3_better = point_j.traffic >= point_i.traffic

                f1_strict = point_j.imbalance < point_i.imbalance
                f2_strict = point_j.degradation < point_i.degradation
                f3_strict = point_j.traffic > point_i.traffic

                if (f1_better and f2_better and f3_better and
                        (f1_strict or f2_strict or f3_strict)):
                    dominated = True
                    break

            if not dominated:
                pareto.append(point_i)
        return pareto


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


# ==============================================================================
# 4. ИСТОЧНИКИ ДАННЫХ (SRP: только извлечение и подготовка данных)
# ==============================================================================
class ClusterParetoProvider:
    """Адаптирует SectorCluster под интерфейс ParetoFrontProvider."""

    def __init__(self, cluster_id: str, cluster, filter_strategy: ParetoFilterStrategy):
        self._cluster_id = cluster_id
        self._cluster = cluster
        self._filter_strategy = filter_strategy

    @property
    def cluster_id(self) -> str:
        return self._cluster_id

    def get_front(self) -> List[ParetoPoint]:
        """Извлекает сырые данные из кластера и применяет фильтр."""
        raw_points = []
        imbalance_dict = self._cluster.get_max_pairwise_imbalance()
        treshhold = self._cluster.azimuths_more_than_treshhold()

        for azimuth in range(360):
            if azimuth in treshhold:
                raw_points.append(ParetoPoint(
                    azimuth=azimuth,
                    imbalance=imbalance_dict[azimuth],
                    degradation=self._cluster.sum_degradation[azimuth],
                    traffic=self._cluster.sum_traffic[azimuth],
                    cluster_id=self._cluster_id
                ))

        # Делегируем фильтрацию стратегии (DIP)
        return self._filter_strategy.filter(raw_points)


# ==============================================================================
# 5. ВЫСОКОУРОВНЕВЫЙ ОРКЕСТРАТОР (DIP, SRP)
# ==============================================================================
class MultiClusterParetoAnalyzer:
    """
    Управляет двухуровневым Парето-анализом.
    Не знает о внутренней структуре SectorCluster, работает только с абстракциями.
    """

    def __init__(self, providers: Dict[str, ParetoFrontProvider], global_filter: ParetoFilterStrategy):
        self._providers = providers
        self._global_filter = global_filter
        self._local_fronts: Dict[str, List[ParetoPoint]] = {}
        self._global_front: List[ParetoPoint] = []

    def analyze(self) -> None:
        """Выполняет полный цикл локального и глобального анализа."""
        all_candidate_points = []

        print("🔄 Этап 1: Локальный анализ кластеров...")
        for cluster_id, provider in self._providers.items():
            local_front = provider.get_front()
            self._local_fronts[cluster_id] = local_front
            all_candidate_points.extend(local_front)
            print(f"   - Кластер '{cluster_id}': {len(local_front)} локальных решений.")

        print(f"\n🔄 Этап 2: Глобальный анализ ({len(all_candidate_points)} кандидатов)...")
        self._global_front = self._global_filter.filter(all_candidate_points)
        print(f"✅ Глобальный Парето-фронт: {len(self._global_front)} решений.")

    @property
    def global_front(self) -> List[ParetoPoint]:
        return self._global_front

    @property
    def local_fronts(self) -> Dict[str, List[ParetoPoint]]:
        return self._local_fronts


# ==============================================================================
# 6. ВИЗУАЛИЗАЦИЯ (SRP: отделена от бизнес-логики)
# ==============================================================================
class ParetoVisualizer:
    """Отвечает исключительно за отрисовку графиков."""

    @staticmethod
    def plot_3d_global(
            front: List[ParetoPoint],
            best_point: Optional[ParetoPoint] = None,
            save_path: Optional[str] = None
    ):
        if not front:
            return

        fig = go.Figure()
        cluster_ids = sorted(list(set(p.cluster_id for p in front)))

        # Генерация цветов для разных кластеров
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'cyan', 'magenta']

        for idx, c_id in enumerate(cluster_ids):
            points = [p for p in front if p.cluster_id == c_id]
            color = colors[idx % len(colors)]

            fig.add_trace(go.Scatter3d(
                x=[p.imbalance for p in points],
                y=[p.degradation for p in points],
                z=[p.traffic for p in points],
                mode='markers', # 'markers+text',
                marker=dict(size=5, color=color, opacity=0.8,line=dict(width=0.5, color='black')),
                #text=[f"{p.cluster_id}<br>Az: {p.azimuth}°" for p in points],
                name=f"Кластер: {c_id}",
                #hovertemplate="<b>%{text}</b><br>Imb: %{x:.2f}%<br>Deg: %{y:.2f}<br>Traf: %{z:.2f}<extra></extra>"
                hovertemplate = (
                    f"<b>Глобальный Парето: {c_id}</b><br>"
                    "Азимут: %{text}<br>"
                    "Дисбаланс: %{x:.2f}%<br>"
                    "Деградация: %{y:.2f}<br>"
                    "Трафик: %{z:.2f}<extra></extra>"
                ),
                text=[str(p.azimuth) for p in points],
            ))

        # Отрисовка лучшей точки желтым цветом
        if best_point:
            fig.add_trace(go.Scatter3d(
                x=[best_point.imbalance],
                y=[best_point.degradation],
                z=[best_point.traffic],
                mode='markers+text',
                marker=dict(
                    size=5,
                    color='yellow',
                    symbol='circle',
                    line=dict(width=0.5, color='black')
                ),
                text=[f"ЛУЧШЕЕ<br>Az: {best_point.azimuth}°"],
                textposition='top center',
                textfont=dict(size=12, color='black', family="Arial Black"),
                name="Лучшее решение",
                hovertemplate=(
                    f"<b>ЛУЧШЕЕ РЕШЕНИЕ</b><br>"
                    f"Кластер: {best_point.cluster_id}<br>"
                    "Азимут: %{text}<br>"
                    "Дисбаланс: %{x:.2f}%<br>"
                    "Деградация: %{y:.2f}<br>"
                    "Трафик: %{z:.2f}<extra></extra>"
                ),
            ))

        fig.update_layout(
            title='Глобальный Парето-фронт (сравнение кластеров)',
            scene=dict(
                xaxis_title='Дисбаланс (%)',
                yaxis_title='Деградация',
                zaxis_title='Трафик',
            ),
            width=1200,
            height=800,
            legend=dict(x=0.01, y=0.99)
        )

        if save_path:
            fig.write_html(save_path)
        fig.show()
