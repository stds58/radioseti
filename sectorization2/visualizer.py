import matplotlib
matplotlib.use('Agg')

import os
import matplotlib.pyplot as plt
import matplotlib.colors as mc
import colorsys
import numpy as np


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

    def draw_cluster_with_traffic(self, azimuth: int, cluster,
                                  save_path: str = None, show: bool = True):
        """
        Рисует ВСЁ на одной полярной диаграмме.
        Исправлено сохранение файлов.
        """
        fig, ax = plt.subplots(subplot_kw={'projection': 'polar'}, figsize=(12, 12))
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)

        # 1. Рисуем трафик как барчарт
        if self.density_map:
            degrees = sorted(self.density_map.keys())
            traffic_values = [float(self.density_map[deg]) for deg in degrees]
            max_traffic = max(traffic_values) if traffic_values else 1

            angles = np.deg2rad(degrees)
            normalized_traffic = [v / max_traffic for v in traffic_values]

            ax.bar(angles, normalized_traffic, width=np.deg2rad(1),
                   color='#1e3a5f', alpha=0.9, edgecolor='none', zorder=1)

        # 2. Рисуем сектора поверх
        current_start_angle = azimuth

        for i, sector in enumerate(cluster.sectors):
            base_color = self.base_colors[i % len(self.base_colors)]
            light_color = self._lighten_color(base_color, amount=0.6)

            left_width = sector.left
            center_width = sector.center
            right_width = sector.right
            total_width = left_width + center_width + right_width

            start_rad = np.deg2rad(current_start_angle)

            # Зоны деградации
            ax.bar(start_rad, 1.1, width=np.deg2rad(left_width), bottom=0,
                   color=light_color, edgecolor='black', linewidth=1,
                   align='edge', alpha=0.5, zorder=2)

            right_start_rad = np.deg2rad(current_start_angle + left_width + center_width)
            ax.bar(right_start_rad, 1.1, width=np.deg2rad(right_width), bottom=0,
                   color=light_color, edgecolor='black', linewidth=1,
                   align='edge', alpha=0.5, zorder=2)

            # Центральная зона
            center_start_rad = np.deg2rad(current_start_angle + left_width)
            ax.bar(center_start_rad, 1.1, width=np.deg2rad(center_width), bottom=0,
                   color=base_color, edgecolor='black', linewidth=1,
                   align='edge', alpha=0.7, zorder=2)

            # Подпись сектора
            mid_angle_rad = np.deg2rad(current_start_angle + total_width / 2)
            ax.text(mid_angle_rad, 1.15, f"S{i + 1}\n{total_width}°",
                    horizontalalignment='center', verticalalignment='center',
                    color='black', fontweight='bold', fontsize=10, zorder=3)

            current_start_angle = (current_start_angle + total_width) % 360

        ax.set_ylim(0, 1.3)
        ax.set_title(f"Сектора + Трафик (Старт: {azimuth}°)", pad=20, fontsize=14)

        # Легенда
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='steelblue', alpha=0.6, label='Трафик'),
            Patch(facecolor=self.base_colors[0], alpha=0.7, label='Центральная зона'),
            Patch(facecolor=self._lighten_color(self.base_colors[0], 0.6), alpha=0.5, label='Зона деградации')
        ]
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.3, 1.1))

        plt.tight_layout()

        if save_path:
            # Принудительно перерисовываем холст перед сохранением
            fig.canvas.draw()

            try:
                # Убрали bbox_inches='tight', так как он ломает полярные графики
                plt.savefig(save_path, dpi=300, format='png')

                # Проверяем, действительно ли файл создался
                if os.path.exists(save_path):
                    file_size = os.path.getsize(save_path)
                    print(f"✅ Файл успешно сохранен: {os.path.abspath(save_path)} ({file_size} байт)")
                else:
                    print(f"❌ ОШИБКА: Файл НЕ был создан по пути: {os.path.abspath(save_path)}")

            except Exception as e:
                print(f" Ошибка при сохранении файла: {e}")

        if show:
            plt.show()
        else:
            plt.close(fig)

