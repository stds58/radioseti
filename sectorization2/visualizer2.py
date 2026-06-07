import matplotlib
matplotlib.use('TkAgg')

import os
import matplotlib.pyplot as plt
import matplotlib.colors as mc
import colorsys
import numpy as np
from typing import List, Optional, Dict
from dataclasses import dataclass
from matplotlib.widgets import Button, RadioButtons
import matplotlib.widgets as mwidgets


# ==============================================================================
# DTO (если нет ParetoPoint)
# ==============================================================================
@dataclass
class VizPoint:
    azimuth: int
    imbalance: float
    degradation: float
    traffic: float
    cluster_id: str


class SectorVisualizer:
    def __init__(self, density_map: dict = None):
        self.base_colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
            '#9467bd', '#8c564b', '#e377c2'
        ]
        self.density_map = density_map

    def _lighten_color(self, color, amount=0.6):
        c = colorsys.rgb_to_hls(*mc.to_rgb(color))
        new_l = min(1.0, c[1] + amount * (1.0 - c[1]))
        return colorsys.hls_to_rgb(c[0], new_l, c[2])

    # ==========================================================================
    # ВНУТРЕННИЙ МЕТОД: рисует один субплот
    # ==========================================================================
    def _draw_single_polar(self, ax, azimuth: int, cluster, title_lines: list):
        """Рисует полярный график с правильными подписями."""
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_rticks([])  # Убираем цифры радиуса для чистоты

        # 1. Трафик
        if self.density_map:
            degrees = sorted(self.density_map.keys())
            traffic_values = [float(self.density_map[deg]) for deg in degrees]
            max_traffic = max(traffic_values) if traffic_values else 1
            angles = np.deg2rad(degrees)
            normalized_traffic = [v / max_traffic for v in traffic_values]
            ax.bar(angles, normalized_traffic, width=np.deg2rad(1),
                   color='#1e3a5f', alpha=0.9, edgecolor='none', zorder=1)

        # 2. Сектора и расчет диапазонов
        current_start_angle = azimuth
        sector_ranges_text = []

        for i, sector in enumerate(cluster.sectors):
            base_color = self.base_colors[i % len(self.base_colors)]
            light_color = self._lighten_color(base_color, amount=0.6)

            left_w = sector.left
            center_w = sector.center
            right_w = sector.right
            total_w = left_w + center_w + right_w

            start_rad = np.deg2rad(current_start_angle)

            # Деградация левая
            ax.bar(start_rad, 1.1, width=np.deg2rad(left_w), bottom=0,
                   color=light_color, edgecolor='black', linewidth=0.5, align='edge', alpha=0.5, zorder=2)

            # Деградация правая
            right_start_rad = np.deg2rad(current_start_angle + left_w + center_w)
            ax.bar(right_start_rad, 1.1, width=np.deg2rad(right_w), bottom=0,
                   color=light_color, edgecolor='black', linewidth=0.5, align='edge', alpha=0.5, zorder=2)

            # Центр
            center_start_rad = np.deg2rad(current_start_angle + left_w)
            ax.bar(center_start_rad, 1.1, width=np.deg2rad(center_w), bottom=0,
                   color=base_color, edgecolor='black', linewidth=0.5, align='edge', alpha=0.7, zorder=2)

            # Текст диапазона сектора (пункт 3)
            end_angle = (current_start_angle + total_w) % 360
            sector_ranges_text.append(f"S{i + 1}: {current_start_angle}°-{end_angle}°")

            current_start_angle = (current_start_angle + total_w) % 360

        ax.set_ylim(0, 1.3)

        # Формируем многострочный заголовок (пункт 3)
        full_title = "\n".join(title_lines + sector_ranges_text)
        ax.set_title(full_title, pad=20, fontsize=10, family='monospace')

    # ==========================================================================
    # РЕЖИМ 2: ИНТЕРАКТИВНЫЙ ПРОСМОТР (Исправленный)
    # ==========================================================================
    def plot_interactive(
            self,
            points: List[VizPoint],
            clusters: Dict[str, object],
            save_path: str = None,
            show: bool = True,
    ):
        if not points:
            return

        # Группируем точки по кластерам
        points_by_cluster = {}
        for p in points:
            if p.cluster_id not in points_by_cluster:
                points_by_cluster[p.cluster_id] = []
            points_by_cluster[p.cluster_id].append(p)

        for cid in points_by_cluster:
            points_by_cluster[cid].sort(key=lambda x: x.azimuth)

        cluster_ids = sorted(points_by_cluster.keys())

        # Находим максимальное количество точек среди всех кластеров для инициализации
        max_azimuths = max(len(pts) for pts in points_by_cluster.values())

        state = {
            'cluster': cluster_ids[0],
            'azimuth_idx': 0
        }

        fig = plt.figure(figsize=(16, 10))

        # ✅ УМЕНЬШЕН квадрат для кластеров
        ax_clusters = plt.axes([0.02, 0.75, 0.20, 0.20])
        ax_azimuths = plt.axes([0.02, 0.05, 0.25, 0.65])
        ax_main = fig.add_axes([0.32, 0.10, 0.60, 0.75], projection='polar')

        # 1. RadioButtons для КЛАСТЕРОВ
        cluster_radio = RadioButtons(ax_clusters, cluster_ids, active=0)
        for label in cluster_radio.labels:
            label.set_fontsize(8)

        # 2. RadioButtons для АЗИМУТОВ (инициализируем с запасом)
        def get_azimuth_labels(cluster_id):
            pts = points_by_cluster[cluster_id]
            return [
                f"{p.azimuth}° | Дисбаланс:{p.imbalance:.1f}% Деградация:{p.degradation:.0f} Трафик:{p.traffic:.0f}"
                for p in pts
            ]

        # Создаем заглушки для максимального количества
        initial_labels = get_azimuth_labels(state['cluster'])
        # Добавляем пустые метки если нужно
        while len(initial_labels) < max_azimuths:
            initial_labels.append("")

        azimuth_radio = RadioButtons(ax_azimuths, initial_labels, active=0)
        for label in azimuth_radio.labels:
            label.set_fontsize(6)

        # Создаем текстовые элементы ОДИН РАЗ при инициализации
        text_cluster = fig.text(0.62, 0.95, "",
                                ha='center', va='center', fontsize=14, fontweight='bold', color='black')
        text_sectors = fig.text(0.62, 0.90, "",
                                ha='center', va='center', fontsize=11, color='darkblue', family='monospace')
        text_metrics = fig.text(0.62, 0.82, "",
                                ha='center', va='center', fontsize=10, color='black', family='monospace')

        def update_plot():
            ax_main.clear()

            selected_cluster = state['cluster']
            pts = points_by_cluster[selected_cluster]

            idx = min(state['azimuth_idx'], len(pts) - 1)
            point = pts[idx]

            cluster_obj = clusters.get(selected_cluster)
            if cluster_obj is None:
                return

            # Вычисляем азимуты секторов
            current_angle = point.azimuth
            sector_ranges = []

            for i, sector in enumerate(cluster_obj.sectors):
                sector_start = current_angle
                sector_width = sector.left + sector.center + sector.right
                # Центр сектора = начало + половина ширины
                center_azimuth = int(sector_start + sector_width / 2) % 360

                sector_ranges.append(f"S{i + 1}: {center_azimuth}°")
                current_angle += sector_width

            # Отрисовка диаграммы
            self._draw_single_polar(ax_main, point.azimuth, cluster_obj, title_lines=[])
            ax_main.set_title("")

            # ✅ ОБНОВЛЯЕМ ТЕКСТ вместо создания нового
            text_cluster.set_text(f"Кластер: {selected_cluster}")
            text_sectors.set_text(" | ".join(sector_ranges))
            text_metrics.set_text(
                f"Imb: {point.imbalance:.1f}% | Deg: {point.degradation:.0f} | Traf: {point.traffic:.0f}")

            # Легенда
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='#1e3a5f', alpha=0.9, label='Трафик'),
                Patch(facecolor=self.base_colors[0], alpha=0.7, label='Центральная зона'),
                Patch(facecolor=self._lighten_color(self.base_colors[0], 0.6), alpha=0.5, label='Зона деградации')
            ]
            ax_main.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.15, 0.95), fontsize=9)

            fig.canvas.draw_idle()

        def on_cluster_change(label):
            state['cluster'] = label
            state['azimuth_idx'] = 0

            new_labels = get_azimuth_labels(label)
            num_new = len(new_labels)
            num_total = len(azimuth_radio.labels)

            # Показываем и обновляем нужные метки
            for i in range(num_total):
                if i < num_new:
                    azimuth_radio.labels[i].set_text(new_labels[i])
                    azimuth_radio.labels[i].set_visible(True)
                else:
                    # Скрываем лишние метки
                    azimuth_radio.labels[i].set_visible(False)

            update_plot()

        def on_azimuth_change(label):
            pts = points_by_cluster[state['cluster']]
            target_az = int(label.split('°')[0])
            for i, p in enumerate(pts):
                if p.azimuth == target_az:
                    state['azimuth_idx'] = i
                    break
            update_plot()

        cluster_radio.on_clicked(on_cluster_change)
        azimuth_radio.on_clicked(on_azimuth_change)

        update_plot()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close(fig)