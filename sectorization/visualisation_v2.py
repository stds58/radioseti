import matplotlib
matplotlib.use('TkAgg')

import numpy as np
from typing import Dict, List
from decimal import Decimal
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec


class SectorVisualizer:
    """Класс для визуализации конфигураций секторов"""

    def __init__(self, density_map: Dict[int, Decimal]):
        self.density_map = density_map
        self._prepare_data()

    def _prepare_data(self):
        list_degrees = []
        list_densities = []

        for degrees, densities in self.density_map.items():
            list_degrees.append(degrees)
            list_densities.append(float(densities))

        sorted_data = sorted(zip(list_degrees, list_densities), key=lambda x: x[0])
        self.degrees = [x[0] for x in sorted_data]
        self.densities = [x[1] for x in sorted_data]

        self.degrees_closed = self.degrees + [self.degrees[0]]
        self.densities_closed = self.densities + [self.densities[0]]
        self.radians_closed = np.deg2rad(self.degrees_closed)

    def plot_multiple_configurations(
            self,
            configurations: List[Dict],
            show: bool = True
    ):
        """Визуализирует несколько конфигураций с прокруткой"""

        root = tk.Tk()
        root.title("СРАВНЕНИЕ КОНФИГУРАЦИЙ СЕКТОРОВ")
        root.geometry("1600x900")

        # Создаем Canvas и Scrollbar
        canvas = tk.Canvas(root)
        scrollbar_y = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)

        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_y.set)

        # Цвета для секторов
        SECTOR_COLORS = [
            '#e5a491', '#e35327', '#e5a491',
            '#b0bda8', '#61e012', '#b0bda8',
            '#60d1af', '#138fd6', '#60d1af',
            '#808bc4', '#800080', '#808bc4',
            '#c1c274', '#f6fa02', '#c1c274',
            '#eddf5f', '#fcab08', '#eddf5f',
            '#c4b376', '#94938e', '#d6d5d2'
        ]

        num_configs = len(configurations)

        # Создаем фигуру с явными размерами
        # Ширина 14, высота 6 на каждый конфиг
        fig_width = 14
        fig_height = num_configs * 6

        fig = Figure(figsize=(fig_width, fig_height), dpi=100)

        # Используем GridSpec для явного позиционирования
        gs = GridSpec(num_configs, 2, figure=fig, hspace=0.4, wspace=0.3,
                      top=0.95, bottom=0.02, left=0.08, right=0.95)

        for idx, config in enumerate(configurations):
            config_name = config['name']
            best_azimuth = config['best_start_azimuth']
            intervals = config['intervals_at_best']
            best_traffic = config.get('best_traffic')
            sector_azimuths = config.get('sector_azimuths')
            metrics = config.get('metrics')

            # 1️ Декартова система
            ax_cart = fig.add_subplot(gs[idx, 0])

            # Рисуем график трафика
            ax_cart.plot(self.degrees, self.densities,
                         marker='', linestyle='-', color='steelblue', linewidth=0.5, zorder=3)

            # Рисуем интервалы секторов
            for i, (start, end) in enumerate(intervals):
                color_idx = i % len(SECTOR_COLORS)
                if start <= end:
                    ax_cart.axvspan(start, end, alpha=0.6, color=SECTOR_COLORS[color_idx], zorder=1)
                else:
                    ax_cart.axvspan(start, 360, alpha=0.6, color=SECTOR_COLORS[color_idx], zorder=1)
                    ax_cart.axvspan(0, end, alpha=0.6, color=SECTOR_COLORS[color_idx], zorder=1)

            # Формируем заголовок
            title = f'{config_name}\nСтарт: {best_azimuth}° | Трафик: {best_traffic:.0f}'
            if sector_azimuths:
                az_str = ", ".join(map(str, sector_azimuths))
                title += f'\nАзимуты секторов: [{az_str}]'

            ax_cart.set_title(title, fontsize=11, fontweight='bold')
            ax_cart.set_xlabel('Азимут (градусы)', fontsize=10)
            ax_cart.set_ylabel('Плотность трафика', fontsize=10)
            ax_cart.set_xlim(0, 360)
            ax_cart.grid(True, linestyle=':', alpha=0.5)

            # 2️⃣ Полярная система
            ax_polar = fig.add_subplot(gs[idx, 1], projection='polar')

            max_val = max(self.densities)

            # Рисуем сектора
            for i, (start, end) in enumerate(intervals):
                color_idx = i % len(SECTOR_COLORS)
                if start <= end:
                    theta = np.linspace(np.deg2rad(start), np.deg2rad(end), 50)
                else:
                    t1 = np.linspace(np.deg2rad(start), np.deg2rad(360), 25)
                    t2 = np.linspace(0, np.deg2rad(end), 25)
                    theta = np.concatenate([t1, t2])

                r = np.full_like(theta, max_val)
                ax_polar.fill_between(theta, 0, r, alpha=0.5, color=SECTOR_COLORS[color_idx], zorder=1)

            # Настраиваем полярную систему
            ax_polar.set_theta_zero_location('N')
            ax_polar.set_theta_direction(-1)
            ax_polar.plot(self.radians_closed, self.densities_closed,
                          marker='', linestyle='-', color='crimson', linewidth=0.5, zorder=2)
            ax_polar.set_title('Полярная система координат', fontsize=11, pad=10)
            ax_polar.grid(True)

        # Создаем canvas и добавляем в scrollable_frame
        canvas_fig = FigureCanvasTkAgg(fig, master=scrollable_frame)
        canvas_fig.draw()
        canvas_fig.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Добавляем toolbar
        toolbar = NavigationToolbar2Tk(canvas_fig, scrollable_frame)
        toolbar.update()

        # Размещаем scrollbar
        scrollbar_y.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Привязка колесика мыши
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel)
        canvas.bind_all("<Button-5>", _on_mousewheel)

        if show:
            root.mainloop()

        return fig


