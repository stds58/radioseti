import matplotlib
matplotlib.use('Agg')

from decimal import Decimal
from typing import List
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import numpy as np
from sectorization2.sector_cluster import SectorCluster


class ParetoAnalyzer:
    """Анализатор Парето-фронта для секторов"""

    def __init__(self, cluster: SectorCluster):
        self._cluster = cluster

    def get_pareto_front(self) -> List[dict]:
        """
        Возвращает Парето-фронт.
        Деградация = МАКСИМУМ деградаций среди секторов кластера.
        """
        points = []
        imbalance_dict = self._cluster.get_max_pairwise_imbalance()

        treshhold = self._cluster.azimuths_more_than_treshhold()

        for azimuth in range(360):
            if azimuth in treshhold:
                imbalance = imbalance_dict[azimuth]
                traffic = self._cluster.sum_traffic[azimuth]
                sector_degradation = self._cluster.sum_degradation[azimuth]

                points.append({
                    'azimuth': azimuth,
                    'imbalance': imbalance,
                    'degradation': sector_degradation,
                    'traffic': traffic
                })

        pareto_front = self._pareto_filter(points)
        return pareto_front

    def _pareto_filter(self, points: List[dict]) -> List[dict]:
        """
        Фильтр недоминируемых решений
        """
        pareto = []

        for i, point_i in enumerate(points):
            dominated = False

            for j, point_j in enumerate(points):
                if i == j:
                    continue

                # Проверяем доминирование: point_j доминирует point_i
                # если все критерии point_j <= point_i И хотя бы один строго <
                f1_better = point_j['imbalance'] <= point_i['imbalance']
                f2_better = point_j['degradation'] <= point_i['degradation']
                f3_better = point_j['traffic'] >= point_i['traffic']

                f1_strict = point_j['imbalance'] < point_i['imbalance']
                f2_strict = point_j['degradation'] < point_i['degradation']
                f3_strict = point_j['traffic'] > point_i['traffic']

                if (f1_better and f2_better and f3_better and
                        (f1_strict or f2_strict or f3_strict)):
                    dominated = True
                    break

            if not dominated:
                pareto.append(point_i)

        return pareto

    def visualize_2d_projections(self, pareto_front: List[dict], save_path: str = None):
        """Визуализация через 2D проекции"""
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        imbalances = [p['imbalance'] for p in pareto_front]
        degradations = [p['degradation'] for p in pareto_front]
        traffics = [p['traffic'] for p in pareto_front]
        azimuths = [p['azimuth'] for p in pareto_front]

        # График 1: Imbalance vs Degradation
        scatter1 = axes[0].scatter(imbalances, degradations, c=azimuths, cmap='viridis')
        axes[0].set_xlabel('Imbalance (%)')
        axes[0].set_ylabel('Degradation')
        axes[0].set_title('Imbalance vs Degradation')
        plt.colorbar(scatter1, ax=axes[0], label='Azimuth')

        # График 2: Imbalance vs Traffic
        scatter2 = axes[1].scatter(imbalances, traffics, c=azimuths, cmap='viridis')
        axes[1].set_xlabel('Imbalance (%)')
        axes[1].set_ylabel('Traffic')
        axes[1].set_title('Imbalance vs Traffic')
        plt.colorbar(scatter2, ax=axes[1], label='Azimuth')

        # График 3: Degradation vs Traffic
        scatter3 = axes[2].scatter(degradations, traffics, c=azimuths, cmap='viridis')
        axes[2].set_xlabel('Degradation')
        axes[2].set_ylabel('Traffic')
        axes[2].set_title('Degradation vs Traffic')
        plt.colorbar(scatter3, ax=axes[2], label='Azimuth')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300)
        plt.show()

    def visualize_3d(self, pareto_front: List[dict], all_points: List[dict] = None, save_path: str = None):
        """3D визуализация с понятными подписями"""

        # Если переданы все точки, рисуем их серым фоном
        if all_points:
            fig = go.Figure(data=[go.Scatter3d(
                x=[p['imbalance'] for p in all_points],
                y=[p['degradation'] for p in all_points],
                z=[p['traffic'] for p in all_points],
                mode='markers',
                marker=dict(
                    size=3,
                    color='lightgray',
                    opacity=0.3
                ),
                hovertemplate=(
                        "<b>Азимут: %{text}°</b><br>" +
                        "Дисбаланс: %{x:.2f}%<br>" +
                        "Деградация: %{y:.2f}<br>" +
                        "Трафик: %{z:.2f}<extra></extra>"
                ),
                text=[str(p['azimuth']) for p in all_points],
                name='Все решения'
            )])
        else:
            fig = go.Figure()

        # Добавляем Парето-фронт яркими точками
        imbalances = [p['imbalance'] for p in pareto_front]
        degradations = [p['degradation'] for p in pareto_front]
        traffics = [p['traffic'] for p in pareto_front]
        azimuths = [p['azimuth'] for p in pareto_front]

        fig.add_trace(go.Scatter3d(
            x=imbalances,
            y=degradations,
            z=traffics,
            mode='markers+text',
            marker=dict(
                size=4,
                color=azimuths,
                colorscale='Viridis',
                opacity=1.0,
                line=dict(width=2, color='black')
            ),
            hovertemplate=(
                    "<b>Азимут: %{text}°</b><br>" +
                    "Дисбаланс: %{x:.2f}%<br>" +
                    "Деградация: %{y:.2f}<br>" +
                    "Трафик: %{z:.2f}<extra>Парето-фронт</extra>"
            ),
            text=[str(p['azimuth']) for p in pareto_front],
            name='Парето-фронт'
        ))

        fig.update_layout(
            title='Парето-фронт: Дисбаланс vs Деградация vs Трафик',
            scene=dict(
                xaxis_title='Дисбаланс между секторами (%)',
                yaxis_title='Потери в деградации',
                zaxis_title='Суммарный трафик',
                xaxis=dict(showgrid=True, gridcolor='lightgray'),
                yaxis=dict(showgrid=True, gridcolor='lightgray'),
                zaxis=dict(showgrid=True, gridcolor='lightgray'),
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.5)
                )
            ),
            width=1400,  # Увеличили ширину
            height=900,  # Увеличили высоту
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )

        if save_path:
            fig.write_html(save_path)
        fig.show()

    def select_best_by_distance(self, pareto_front: List[dict]) -> dict|None:
        """
        Выбор лучшего решения по расстоянию до идеальной точки (0,0,0)
        с нормализацией
        """
        if not pareto_front:
            return None

        # Находим min/max для нормализации
        imbalances = [p['imbalance'] for p in pareto_front]
        degradations = [p['degradation'] for p in pareto_front]
        traffics = [p['traffic'] for p in pareto_front]

        min_imb, max_imb = min(imbalances), max(imbalances)
        min_deg, max_deg = min(degradations), max(degradations)
        min_traf, max_traf = min(traffics), max(traffics)

        # Нормализуем и считаем расстояние до идеальной точки
        best_point = None
        min_distance = float('inf')

        for point in pareto_front:
            # Нормализация [0, 1]
            imb_norm = (point['imbalance'] - min_imb) / (max_imb - min_imb) if max_imb != min_imb else 0
            deg_norm = (point['degradation'] - min_deg) / (max_deg - min_deg) if max_deg != min_deg else 0
            traf_norm = (point['traffic'] - min_traf) / (max_traf - min_traf) if max_traf != min_traf else 0

            # Евклидово расстояние до (0,0,0)
            distance = np.sqrt(imb_norm ** 2 + deg_norm ** 2 + traf_norm ** 2)

            if distance < min_distance:
                min_distance = distance
                best_point = point

        return best_point


    def select_by_constraints(self, pareto_front: List[dict], max_imbalance: float) -> List[dict]:
        """
        Выбор решений с ограничениями (например, imbalance <= 5%)
        """
        return [p for p in pareto_front if p['imbalance'] <= max_imbalance]


    def select_by_traffic_constraint(self, pareto_front: List[dict],
                                     min_traffic_threshold: Decimal = Decimal(0.85)) -> dict|None:
        """
        Выбирает лучшее решение из Парето-фронта с учетом порога трафика.

        :param pareto_front: Список точек Парето-фронта.
        :param min_traffic_threshold: Минимально допустимый уровень трафика
                                      (доля от максимума на фронте, например 0.85 = 85%).
        :return: Лучшая точка или None.
        """
        if not pareto_front:
            return None

        # 1. Находим максимальный трафик на Парето-фронте для нормализации порога
        max_traffic_on_front = max(p['traffic'] for p in pareto_front)
        absolute_min_traffic = max_traffic_on_front * min_traffic_threshold

        # 2. Фильтруем точки, которые не дотягивают до порога трафика
        filtered_points = [p for p in pareto_front if p['traffic'] >= absolute_min_traffic]

        if not filtered_points:
            print(f"⚠️ Предупреждение: Ни одна точка Парето-фронта не достигла "
                  f"порога трафика {min_traffic_threshold:.0%} ({absolute_min_traffic:.0f}). "
                  f"Берем точку с макс. трафиком.")
            # Если все отфильтровалось, берем ту, что ближе всего к порогу (макс. трафик)
            filtered_points = sorted(pareto_front, key=lambda x: x['traffic'], reverse=True)[:1]

        # 3. Среди подходящих по трафику выбираем лучшую по балансу и деградации
        # Используем тот же принцип расстояния до идеала, но только по двум осям
        imbalances = [p['imbalance'] for p in filtered_points]
        degradations = [p['degradation'] for p in filtered_points]

        min_imb, max_imb = min(imbalances), max(imbalances)
        min_deg, max_deg = min(degradations), max(degradations)

        best_point = None
        min_distance = float('inf')

        for point in filtered_points:
            # Нормализация [0, 1] для дисбаланса и деградации
            imb_norm = (point['imbalance'] - min_imb) / (max_imb - min_imb) if max_imb != min_imb else 0
            deg_norm = (point['degradation'] - min_deg) / (max_deg - min_deg) if max_deg != min_deg else 0

            # Расстояние до идеальной точки (0 imbalance, 0 degradation)
            distance = np.sqrt(imb_norm ** 2 + deg_norm ** 2)

            if distance < min_distance:
                min_distance = distance
                best_point = point

        return best_point
