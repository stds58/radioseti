import matplotlib
matplotlib.use('TkAgg')

import os

import matplotlib.pyplot as plt
import numpy as np
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict

from sectorization3.data.data import convert_to_decimal #, density_map
from sectorization2.data.data_raw1 import raw_data as metrics1
from sectorization2.data.data_raw2 import raw_data as metrics2
from sectorization2.data.data_raw3 import raw_data as metrics3



@dataclass
class AntennaPattern:
    name: str
    frequency: str
    gain_dbd: float
    gain_dbi: float
    angles: np.ndarray
    gains: np.ndarray

    @property
    def max_gain(self) -> float:
        return np.max(self.gains)

    def get_beamwidth_points(self, threshold_db: float = -3) -> Optional[Tuple[float, float]]:
        threshold = self.max_gain + threshold_db
        peak_idx = np.argmax(self.gains)

        left_angle = None
        for i in range(peak_idx, -1, -1):
            if self.gains[i] < threshold and i < len(self.gains) - 1:
                g1, g2 = self.gains[i], self.gains[i + 1]
                if g1 != g2:
                    left_angle = self.angles[i] + (threshold - g1) * (self.angles[i + 1] - self.angles[i]) / (g2 - g1)
                else:
                    left_angle = self.angles[i]
                break

        right_angle = None
        for i in range(peak_idx, len(self.gains)):
            if self.gains[i] < threshold and i > 0:
                g1, g2 = self.gains[i - 1], self.gains[i]
                if g1 != g2:
                    right_angle = self.angles[i - 1] + (threshold - g1) * (self.angles[i] - self.angles[i - 1]) / (g2 - g1)
                else:
                    right_angle = self.angles[i - 1]
                break

        if left_angle is not None and right_angle is not None:
            return left_angle, right_angle
        return None

    def get_degradation_zones(self, thresholds_db: List[float] = None) -> Dict[float, Optional[Tuple[float, float]]]:
        if thresholds_db is None:
            thresholds_db = [-3, -10, -20]
        zones = {}
        for thresh in thresholds_db:
            points = self.get_beamwidth_points(thresh)
            zones[thresh] = points
        return zones


@dataclass
class Sector:
    pattern: AntennaPattern
    azimuth: float
    label: str = ""

    def get_rotated_angles(self) -> np.ndarray:
        return (self.pattern.angles + self.azimuth) % 360

    def get_rotated_angles_rad(self) -> np.ndarray:
        return np.radians(self.get_rotated_angles())

    def get_beam_direction(self) -> float:
        peak_angle = self.pattern.angles[np.argmax(self.pattern.gains)]
        return (peak_angle + self.azimuth) % 360


@dataclass
class CIResult:
    azimuth: float
    serving_sector_label: str
    serving_gain: float
    interfering_sectors: List[Tuple[str, float]]
    ci_ratio: float
    serving_degraded: bool = False
    degradation_level: int = 0


@dataclass
class ProblemZone:
    start_azimuth: float
    end_azimuth: float
    min_ci: float
    min_gain: float
    zone_type: str


class IPatternParser(ABC):
    @abstractmethod
    def parse(self, filepath: str) -> AntennaPattern:
        pass


class IPatternRenderer(ABC):
    @abstractmethod
    def render(self, sectors: List[Sector], save_path: str, problem_zones: List[ProblemZone] = None):
        pass


class InterferenceAnalyzer:
    def __init__(self, interference_threshold_db: float = -25, degradation_threshold_db: float = -10):
        self.interference_threshold_db = interference_threshold_db
        self.degradation_threshold_db = degradation_threshold_db

    def calculate_ci(self, sectors: List[Sector], angular_resolution: float = 1.0) -> List[CIResult]:
        """
        считает C/I для сильнейшего сектора в каждой точке
        C/I = P_serving / P_interferers
        C/I_dB = 10·log₁₀(P_serving) - 10·log₁₀(Σ P_interferers) = C_dB - 10·log₁₀(10^(I₁/10) + 10^(I₂/10) + ...)
        C_dB: 10·log₁₀(P_serving)
        I: I₁, I₂, ...
        total_interference_linear: 10·log₁₀(Σ P_interferers)
        """
        if len(sectors) < 2:
            return []

        azimuths = np.arange(0, 360, angular_resolution)
        ci_results = []

        for azimuth in azimuths:
            sector_gains = []
            # Отбор секторов для азимута
            for idx, sector in enumerate(sectors):
                gain = self._get_gain_at_azimuth(sector, azimuth)
                max_gain = sector.pattern.max_gain
                if gain > (max_gain + self.interference_threshold_db):
                    # Сектор попадает в рассмотрение, только если его усиление в данном направлении
                    # превышает max_gain - self.degradation_threshold_db(25 дБ).
                    # Всё, что слабее этого порога, игнорируется как незначительная помеха
                    sector_gains.append((idx, sector, gain))

            if len(sector_gains) >= 1:
                # Определение несущей
                sector_gains.sort(key=lambda x: x[2], reverse=True)
                serving_idx, serving_sector, C_dB = sector_gains[0]

                is_degraded = C_dB < (serving_sector.pattern.max_gain + self.degradation_threshold_db)
                degradation_level = 0
                if C_dB < (serving_sector.pattern.max_gain - 20):
                    degradation_level = 2
                elif is_degraded:
                    degradation_level = 1

                interferers = []
                total_interference_linear = 0

                if len(sector_gains) > 1:
                    # Суммирование помех
                    for idx, sector, I in sector_gains[1:]:
                        interferers.append((sector.label or f"Sector_{idx}", I))
                        # 10^(I₁/10) + 10^(I₂/10) + ... + 10^(Iₙ/10)
                        total_interference_linear += 10 ** (I / 10)

                if total_interference_linear > 0:
                    # C/I = C_dB - 10·log₁₀(10^(I₁/10) + 10^(I₂/10) + ... + 10^(Iₙ/10))
                    interference_db = 10 * np.log10(total_interference_linear)
                    ci_ratio = C_dB - interference_db
                else:
                    ci_ratio = float('inf') # Нет помех

                ci_results.append(CIResult(
                    azimuth=azimuth,
                    serving_sector_label=serving_sector.label or f"Sector_{serving_idx}",
                    serving_gain=C_dB,
                    interfering_sectors=interferers,
                    ci_ratio=ci_ratio,
                    serving_degraded=is_degraded,
                    degradation_level=degradation_level
                ))
            else:
                ci_results.append(CIResult(
                    azimuth=azimuth,
                    serving_sector_label="NO_COVERAGE",
                    serving_gain=-999,
                    interfering_sectors=[],
                    ci_ratio=float('-inf'), # Нет покрытия
                    serving_degraded=True,
                    degradation_level=2
                ))

        return ci_results

    def find_problem_zones(self, ci_results: List[CIResult], min_ci_threshold: float = 6.0) -> List[ProblemZone]:
        problem_zones = []
        i = 0
        while i < len(ci_results):
            result = ci_results[i]

            if result.degradation_level >= 2 and result.serving_sector_label == "NO_COVERAGE":
                start_az = result.azimuth
                min_gain = result.serving_gain
                while i < len(ci_results) and ci_results[i].serving_sector_label == "NO_COVERAGE":
                    if ci_results[i].serving_gain > min_gain:
                        min_gain = ci_results[i].serving_gain
                    i += 1
                end_az = ci_results[i - 1].azimuth
                problem_zones.append(ProblemZone(start_az, end_az, float('-inf'), min_gain, 'dead_zone'))
                continue

            has_ci_problem = result.ci_ratio < min_ci_threshold and result.ci_ratio != float('inf')
            has_coverage_problem = result.serving_degraded

            if has_ci_problem or has_coverage_problem:
                start_az = result.azimuth
                min_ci_in_zone = result.ci_ratio if result.ci_ratio != float('inf') else 999
                min_gain_in_zone = result.serving_gain
                zone_has_ci_problem = has_ci_problem
                zone_has_coverage_problem = has_coverage_problem

                while i < len(ci_results):
                    result = ci_results[i]
                    if result.degradation_level >= 2 and result.serving_sector_label == "NO_COVERAGE":
                        break
                    current_has_ci = result.ci_ratio < min_ci_threshold and result.ci_ratio != float('inf')
                    current_has_coverage = result.serving_degraded
                    if not current_has_ci and not current_has_coverage:
                        break
                    if result.ci_ratio != float('inf') and result.ci_ratio < min_ci_in_zone:
                        min_ci_in_zone = result.ci_ratio
                    if result.serving_gain > min_gain_in_zone:
                        min_gain_in_zone = result.serving_gain
                    zone_has_ci_problem = zone_has_ci_problem or current_has_ci
                    zone_has_coverage_problem = zone_has_coverage_problem or current_has_coverage
                    i += 1

                end_az = ci_results[i - 1].azimuth

                if zone_has_ci_problem and zone_has_coverage_problem:
                    zone_type = 'combined'
                elif zone_has_ci_problem:
                    zone_type = 'interference'
                else:
                    zone_type = 'weak_coverage'

                problem_zones.append(ProblemZone(start_az, end_az, min_ci_in_zone, min_gain_in_zone, zone_type))
            else:
                i += 1

        return problem_zones

    def _get_gain_at_azimuth(self, sector: Sector, azimuth: float) -> float:
        rotated_angles = sector.get_rotated_angles()
        gains = sector.pattern.gains
        azimuth = azimuth % 360
        sort_idx = np.argsort(rotated_angles)
        sorted_angles = rotated_angles[sort_idx]
        sorted_gains = gains[sort_idx]
        return np.interp(azimuth, sorted_angles, sorted_gains, period=360)


class MSIParser(IPatternParser):
    def parse(self, filepath: str) -> AntennaPattern:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        name = self._extract_name(content)
        freq = self._extract_frequency(content)
        gain_dbd = self._extract_gain(content)
        gain_dbi = gain_dbd + 2.15
        angles, gains = self._extract_horizontal_pattern(content)

        return AntennaPattern(
            name=name, frequency=freq, gain_dbd=gain_dbd, gain_dbi=gain_dbi,
            angles=np.array(angles), gains=np.array(gains)
        )

    def _extract_name(self, content: str) -> str:
        match = re.search(r'NAME\s+(.+)', content)
        return match.group(1).strip() if match else "Unknown"

    def _extract_frequency(self, content: str) -> str:
        match = re.search(r'FREQUENCY\s+(\d+)', content)
        return match.group(1) if match else "Unknown"

    def _extract_gain(self, content: str) -> float:
        match = re.search(r'GAIN\s+([\d.]+)', content)
        return float(match.group(1)) if match else 0.0

    def _extract_horizontal_pattern(self, content: str) -> Tuple[List[float], List[float]]:
        h_pattern = re.search(r'HORIZONTAL\s+360\s*\n([\s\S]+?)(?=\n[A-Z]|\Z)', content)
        if not h_pattern:
            return [], []

        lines = h_pattern.group(1).strip().split('\n')
        angles, gains = [], []

        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    angles.append(float(parts[0]))
                    gains.append(-float(parts[1]))
                except ValueError:
                    continue

        return angles, gains


class MultiPatternRenderer(IPatternRenderer):
    def __init__(self, density_map: dict, degradation_threshold_db: float = -10):
        self.colors = plt.cm.Set1(np.linspace(0, 1, 10))
        self.sectors = []
        self.problem_zones = []
        self.fig = None
        self.ax_polar = None
        self.density_angles = None
        self.density_values = None
        self.density_normalized = None
        self.degradation_threshold_db = degradation_threshold_db
        self._density_map = density_map


    def _prepare_density_data(self):
        angles = sorted(self._density_map.keys())
        values = [float(self._density_map[a]) for a in angles]
        self.density_angles = np.array(angles)
        self.density_values = np.array(values)
        if len(values) > 0:
            max_val = max(values)
            min_val = min(values)
            if max_val > min_val:
                self.density_normalized = -40 + (self.density_values - min_val) / (max_val - min_val) * 40
            else:
                self.density_normalized = np.full_like(self.density_values, -20)

    def render(self, sectors: List[Sector], save_path: str = 'radiation_patterns.png',
               problem_zones: List[ProblemZone] = None):
        self.sectors = sectors
        self.problem_zones = problem_zones or []
        self._prepare_density_data()
        plt.close('all')

        self.fig = plt.figure(figsize=(20, 8))
        self.ax_polar = self.fig.add_subplot(121, projection='polar')
        ax_cart = self.fig.add_subplot(122)

        self._render_polar(self.ax_polar)
        self._render_cartesian(ax_cart)

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"✓ График сохранён: {save_path}")

        self.fig.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        plt.show()

    def _on_mouse_move(self, event):
        if event.inaxes != self.ax_polar:
            self.ax_polar.set_title("Horizontal Radiation Patterns\n(Hover for details)", fontsize=12,
                                    fontweight='bold')
            self.fig.canvas.draw_idle()
            return

        if event.xdata is None or event.ydata is None:
            return

        theta_rad = event.xdata
        azimuth = np.degrees(theta_rad) % 360

        # Просто собираем усиление каждой антенны в порядке их добавления
        lines = []
        for sector in self.sectors:
            gain = self._get_gain_at_azimuth(sector, azimuth)
            label = sector.label or f"S{sector.azimuth}°"
            lines.append(f"{label}: {gain:.1f} dB")

        # Информация о плотности трафика
        density_info = ""
        nearest_degree = round(azimuth)
        if nearest_degree in self._density_map:
            density_info = f" | Density: {self._density_map[nearest_degree]}"

        # Формируем заголовок - каждая антенна с новой строки
        title_text = f"Azimuth: {azimuth:.1f}°{density_info}\n"
        title_text += "\n".join(lines)

        self.ax_polar.set_title(title_text, fontsize=9, fontweight='bold')
        self.fig.canvas.draw_idle()


    def _get_gain_at_azimuth(self, sector: Sector, azimuth: float) -> float:
        rotated_angles = sector.get_rotated_angles()
        gains = sector.pattern.gains
        azimuth = azimuth % 360
        sort_idx = np.argsort(rotated_angles)
        sorted_angles = rotated_angles[sort_idx]
        sorted_gains = gains[sort_idx]
        return np.interp(azimuth, sorted_angles, sorted_gains, period=360)

    def _render_polar(self, ax):
        if self.density_angles is not None and self.density_normalized is not None:
            angles_rad = np.radians(self.density_angles)
            sort_idx = np.argsort(angles_rad)
            angles_rad_sorted = angles_rad[sort_idx]
            density_sorted = self.density_normalized[sort_idx]
            angles_rad_closed = np.append(angles_rad_sorted, angles_rad_sorted[0])
            density_closed = np.append(density_sorted, density_sorted[0])
            ax.fill(angles_rad_closed, density_closed, alpha=0.3, color='green', label='Traffic Density', zorder=1)
            ax.plot(angles_rad_closed, density_closed, color='darkgreen', linewidth=1, alpha=0.5, zorder=2)

        legend_added = {'dead_zone': False, 'combined': False, 'interference': False, 'weak_coverage': False}

        for zone in self.problem_zones:
            start_rad = np.radians(zone.start_azimuth)
            end_rad = np.radians(zone.end_azimuth)
            angles_to_fill = np.linspace(start_rad, end_rad, max(int(abs(zone.end_azimuth - zone.start_azimuth) * 2), 10))

            if zone.zone_type == 'dead_zone':
                color, alpha, label = 'gray', 0.40, 'Dead Zone (No Coverage)'
            elif zone.zone_type == 'combined':
                color, alpha, label = 'red', 0.35, 'Critical (Weak + C/I<6dB)'
            elif zone.zone_type == 'interference':
                color, alpha, label = 'orange', 0.25, 'Interference (C/I<6dB)'
            elif zone.zone_type == 'weak_coverage':
                color, alpha, label = 'yellow', 0.20, f'Weak Coverage (<{self.degradation_threshold_db}dB)'
            else:
                continue

            show_label = not legend_added[zone.zone_type]
            legend_added[zone.zone_type] = True

            ax.fill_between(angles_to_fill, -40, -5, color=color, alpha=alpha,
                          zorder=20, label=label if show_label else "")

        for idx, sector in enumerate(self.sectors):
            color = self.colors[idx % len(self.colors)]
            rotated_angles = sector.get_rotated_angles()
            angles_rad = np.radians(rotated_angles)
            gains = sector.pattern.gains
            label = sector.label or f"{sector.pattern.name} ({sector.azimuth}°)"

            ax.plot(angles_rad, gains, color=color, linewidth=1.2, label=label, zorder=10)
            ax.fill(angles_rad, gains, alpha=0.02, color=color, zorder=5)

            max_gain = sector.pattern.max_gain
            threshold = max_gain - 3
            circle_angles = np.linspace(0, 2 * np.pi, 360)
            circle_radii = np.full_like(circle_angles, threshold)
            ax.plot(circle_angles, circle_radii, color=color, linestyle='--', linewidth=1, alpha=0.4, zorder=1)

            degradation_threshold = max_gain + self.degradation_threshold_db
            if degradation_threshold > -40:
                ax.plot(circle_angles, np.full_like(circle_angles, degradation_threshold),
                       color=color, linestyle=':', linewidth=1, alpha=0.3, zorder=1)

            beam_dir_deg = sector.get_beam_direction()
            beam_dir_rad = np.radians(beam_dir_deg)
            ax.plot(beam_dir_rad, max_gain, 'o', color=color, markersize=10,
                    markeredgecolor='black', markeredgewidth=1.5, zorder=12)

            annotation_radius = max_gain + 2
            ax.annotate(f'{beam_dir_deg:.0f}°',
                        xy=(beam_dir_rad, max_gain),
                        xytext=(beam_dir_rad, annotation_radius),
                        ha='center', va='bottom', fontsize=9, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='black', alpha=0.8),
                        zorder=13)

        max_gain_all = max(s.pattern.max_gain for s in self.sectors)
        ax.set_ylim(-40, max_gain_all + 5)
        ax.set_thetagrids(np.arange(0, 360, 15))
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)

        ax.set_yticklabels([])
        for val in range(-35, 0, 5):
            ax.text(0, val, f'{val} dB', ha='center', va='center', fontsize=8, color='gray')

        ax.set_title(f"Horizontal Radiation Patterns\nDegradation threshold: {self.degradation_threshold_db} dB\n(Hover for details)",
                    fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', bbox_to_anchor=(1.4, 1.0), fontsize=8)

    def _render_cartesian(self, ax):
        worst_combined = None
        worst_interference = None
        worst_weak_coverage = None

        for zone in self.problem_zones:
            if zone.zone_type == 'combined':
                if worst_combined is None or zone.min_ci < worst_combined.min_ci:
                    worst_combined = zone
            elif zone.zone_type == 'interference':
                if worst_interference is None or zone.min_ci < worst_interference.min_ci:
                    worst_interference = zone
            elif zone.zone_type == 'weak_coverage':
                if worst_weak_coverage is None or zone.min_gain < worst_weak_coverage.min_gain:
                    worst_weak_coverage = zone

        if self.density_angles is not None and self.density_values is not None:
            ax2 = ax.twinx()
            ax2.fill_between(self.density_angles, 0, self.density_values,
                             alpha=0.2, color='green', label='Traffic Density')
            ax2.plot(self.density_angles, self.density_values,
                     color='darkgreen', linewidth=1, alpha=0.7)
            ax2.set_ylabel('Traffic Density', color='darkgreen')
            ax2.tick_params(axis='y', labelcolor='darkgreen')
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=8)

        for idx, sector in enumerate(self.sectors):
            color = self.colors[idx % len(self.colors)]
            rotated_angles = sector.get_rotated_angles()
            gains = sector.pattern.gains
            label = sector.label or f"{sector.pattern.name} ({sector.azimuth}°)"

            sort_idx = np.argsort(rotated_angles)
            sorted_angles = rotated_angles[sort_idx]
            sorted_gains = gains[sort_idx]

            ax.plot(sorted_angles, sorted_gains, color=color, linewidth=0.8, label=label)
            ax.fill_between(sorted_angles, sorted_gains, -40, alpha=0.05, color=color)

            threshold = sector.pattern.max_gain - 3
            ax.axhline(y=threshold, color=color, linestyle='--', linewidth=1, alpha=0.5)

            degradation_threshold = sector.pattern.max_gain + self.degradation_threshold_db
            ax.axhline(y=degradation_threshold, color=color, linestyle=':', linewidth=1, alpha=0.3)

            beam_dir = sector.get_beam_direction()
            ax.axvline(x=beam_dir, color=color, linestyle=':', linewidth=1.5, alpha=0.6)
            ax.plot(beam_dir, sector.pattern.max_gain, 'o', color=color, markersize=8,
                    markeredgecolor='black', markeredgewidth=1.5, zorder=10)
            ax.annotate(f'{beam_dir:.0f}°', xy=(beam_dir, sector.pattern.max_gain),
                        xytext=(beam_dir + 5, sector.pattern.max_gain + 1),
                        fontsize=9, fontweight='bold', color=color,
                        bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8))

        for zone in self.problem_zones:
            if zone.zone_type == 'dead_zone':
                color, alpha = 'gray', 0.30
            elif zone.zone_type == 'combined':
                color, alpha = 'red', 0.25
            elif zone.zone_type == 'interference':
                color, alpha = 'orange', 0.20
            elif zone.zone_type == 'weak_coverage':
                color, alpha = 'yellow', 0.15
            else:
                continue
            ax.axvspan(zone.start_azimuth, zone.end_azimuth, color=color, alpha=alpha)

        y_pos = -38
        if worst_combined:
            mid_az = (worst_combined.start_azimuth + worst_combined.end_azimuth) / 2
            ax.annotate(f'WORST: C/I={worst_combined.min_ci:.1f}dB\n(Weak + Interference)',
                       xy=(mid_az, y_pos),
                       ha='center', va='center', fontsize=9, color='darkred', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='darkred', alpha=1.0), zorder=20)
            y_pos -= 5

        if worst_interference:
            mid_az = (worst_interference.start_azimuth + worst_interference.end_azimuth) / 2
            ax.annotate(f'Interference: C/I={worst_interference.min_ci:.1f}dB',
                       xy=(mid_az, y_pos),
                       ha='center', va='center', fontsize=8, color='darkorange', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='darkorange', alpha=1.0), zorder=20)
            y_pos -= 5

        if worst_weak_coverage:
            mid_az = (worst_weak_coverage.start_azimuth + worst_weak_coverage.end_azimuth) / 2
            ax.annotate(f'Weak Coverage: Gain={worst_weak_coverage.min_gain:.1f}dB',
                       xy=(mid_az, y_pos),
                       ha='center', va='center', fontsize=8, color='darkgoldenrod', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='darkgoldenrod', alpha=1.0), zorder=20)

        ax.set_xlim(0, 360)
        ax.set_ylim(-40, max(s.pattern.max_gain for s in self.sectors) + 3)
        ax.set_xticks(np.arange(0, 361, 30))
        ax.set_xlabel('Azimuth (degrees)')
        ax.set_ylabel('Gain (dB)')
        ax.set_title(f'Intersection Detail (Cartesian)\nDegradation threshold: {self.degradation_threshold_db} dB')
        ax.grid(True, alpha=0.3)


class AntennaPatternService:
    def __init__(self, parser=None, renderer=None, interference_analyzer=None, density_map=None):
        self.parser = parser or MSIParser()
        self.interference_analyzer = interference_analyzer or InterferenceAnalyzer(
            interference_threshold_db=-25,
            degradation_threshold_db=-10
        )
        self.renderer = renderer or MultiPatternRenderer(density_map=density_map, degradation_threshold_db=-10)

    def process_sectors(self,
                        sector_configs: List[dict],
                        save_plot: bool = True,
                        plot_path: str = 'radiation_patterns.png',
                        min_ci_threshold: float = 6.0,
                        degradation_threshold_db: float = -10
                        ):

        self.interference_analyzer.degradation_threshold_db = degradation_threshold_db
        self.renderer.degradation_threshold_db = degradation_threshold_db

        sectors = []

        for config in sector_configs:
            filepath = config['file']
            azimuth = config.get('azimuth', 0)
            label = config.get('label', '')

            if not os.path.exists(filepath):
                filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.basename(filepath))
                if not os.path.exists(filepath):
                    print(f"✗ Файл не найден: {filepath}")
                    continue

            pattern = self.parser.parse(filepath)
            sectors.append(Sector(pattern=pattern, azimuth=azimuth, label=label))
            print(f"✓ Загружен: {pattern.name} (Azimuth: {azimuth}°)")

        problem_zones = []
        if len(sectors) > 1:
            ci_results = self.interference_analyzer.calculate_ci(sectors)
            problem_zones = self.interference_analyzer.find_problem_zones(ci_results, min_ci_threshold)
            self._print_statistics(problem_zones, min_ci_threshold, degradation_threshold_db)

        if save_plot:
            self.renderer.render(sectors, plot_path, problem_zones)

        return sectors, problem_zones

    def _print_statistics(self, problem_zones: List[ProblemZone], min_ci_threshold: float,
                         degradation_threshold_db: float):
        print(f"\n{'='*70}")
        print(f"АНАЛИЗ ПРОБЛЕМНЫХ ЗОН")
        print(f"  Порог C/I: {min_ci_threshold} дБ")
        print(f"  Порог деградации: {degradation_threshold_db} дБ")
        print(f"{'='*70}")

        by_type = {}
        for zone in problem_zones:
            if zone.zone_type not in by_type:
                by_type[zone.zone_type] = []
            by_type[zone.zone_type].append(zone)

        type_descriptions = {
            'dead_zone': ('МЁРТВЫЕ ЗОНЫ (нет покрытия)', 'gray'),
            'combined': ('КРИТИЧЕСКИЕ ЗОНЫ (слабое покрытие + помехи)', 'red'),
            'interference': ('ЗОНЫ ИНТЕРФЕРЕНЦИИ (C/I ниже порога)', 'orange'),
            'weak_coverage': (f'ЗОНЫ СЛАБОГО ПОКРЫТИЯ (< {degradation_threshold_db} дБ)', 'yellow')
        }

        total_problematic_degrees = 0

        for zone_type in ['dead_zone', 'combined', 'interference', 'weak_coverage']:
            if zone_type in by_type:
                zones = by_type[zone_type]
                description, _ = type_descriptions[zone_type]
                total_degrees = sum(zone.end_azimuth - zone.start_azimuth for zone in zones)
                total_problematic_degrees += total_degrees

                print(f"\n  {description}:")
                print(f"    Количество зон: {len(zones)}")
                print(f"    Общая протяжённость: {total_degrees:.0f}°")

                for i, zone in enumerate(zones[:5]):
                    if zone.zone_type in ['dead_zone', 'weak_coverage']:
                        print(f"    [{zone.start_azimuth:.0f}°-{zone.end_azimuth:.0f}°] "
                              f"Gain min: {zone.min_gain:.1f} дБ")
                    elif zone.zone_type == 'interference':
                        print(f"    [{zone.start_azimuth:.0f}°-{zone.end_azimuth:.0f}°] "
                              f"C/I min: {zone.min_ci:.1f} дБ")
                    else:
                        print(f"    [{zone.start_azimuth:.0f}°-{zone.end_azimuth:.0f}°] "
                              f"C/I min: {zone.min_ci:.1f} дБ, Gain min: {zone.min_gain:.1f} дБ")

                if len(zones) > 5:
                    print(f"    ... и ещё {len(zones) - 5} зон(ы)")

        total_clean_degrees = 360 - total_problematic_degrees
        print(f"\n{'='*70}")
        print(f"ИТОГО:")
        print(f"  Проблемные зоны: {total_problematic_degrees:.0f}° ({total_problematic_degrees/360*100:.1f}%)")
        print(f"  Чистые зоны: {total_clean_degrees:.0f}° ({total_clean_degrees/360*100:.1f}%)")
        print(f"{'='*70}\n")



huawei_hbw60_metrics3 = {"density_map": metrics3,
 "sector_configs": [
     {'file': 'radiation_pattern/huawei/ATR4518R7/ATR4518R7_1850_X_CO_P45_06T_yL.msi', 'azimuth': 0 + 3 - 64,
      'label': 'hbw60° (az296°)'},
     {'file': 'radiation_pattern/huawei/ATR4518R7/ATR4518R7_1850_X_CO_M45_06T_yL.msi', 'azimuth': 63 + 3 - 39,
      'label': 'hbw60° (az27°)'},
     {'file': 'radiation_pattern/huawei/ATR4518R7/ATR4518R7_1850_X_CO_M45_06T_yL.msi', 'azimuth': 126 + 3 - 26,
      'label': 'hbw60° (az103°)'},
 ]
 }

huawei_hbw60_metrics1 = {"density_map": metrics1,
 "sector_configs": [
     {'file': 'radiation_pattern/huawei/ATR4518R7/ATR4518R7_1850_X_CO_P45_06T_yL.msi', 'azimuth': 0 + 3 - 71,
      'label': 'hbw60° (az292°)'},
     {'file': 'radiation_pattern/huawei/ATR4518R7/ATR4518R7_1850_X_CO_M45_06T_yL.msi', 'azimuth': 63 + 3 + 17,
      'label': 'hbw60° (az83°)'},
     {'file': 'radiation_pattern/huawei/ATR4518R7/ATR4518R7_1850_X_CO_M45_06T_yL.msi', 'azimuth': 126 + 3 + 55,
      'label': 'hbw60° (az184°)'},
 ]}

kathrein_hbw30_metrics1 = {"density_map": metrics3,
 "sector_configs": [
     {'file': 'radiation_pattern/kathrein/741785X2.msi', 'azimuth': 0 - 66, 'label': 'hbw 30°(az294°)'},
     {'file': 'radiation_pattern/kathrein/741785X2.msi', 'azimuth': 30 - 3, 'label': 'hbw 30°(az27°)'},
     {'file': 'radiation_pattern/kathrein/741785X2.msi', 'azimuth': 60 + 43, 'label': 'hbw 30°(az103°)'},
 ]}

commscope_hbw40_metrics2 = {"density_map": metrics2,
 "sector_configs": [
     {'file': 'radiation_pattern/commscope/2NPX210R-V1_Port 2 - -45_08DT_1805.msi', 'azimuth': 32 - 82,
      'label': 'hbw40° (az278°)'},
     {'file': 'radiation_pattern/commscope/2NPX210R-V1_Port 2 - -45_08DT_1805.msi', 'azimuth': 32 + 107,
      'label': 'hbw40° (az107°)'},
     {'file': 'radiation_pattern/commscope/2NPX210R-V1_Port 2 - -45_08DT_1805.msi', 'azimuth': 32 + 225,
      'label': 'hbw40° (az225°)'},
 ]}

commscope_hbw40_metrics3 = {"density_map": metrics3,
 "sector_configs": [
     {'file': 'radiation_pattern/commscope/2NPX210R-V1_Port 2 - -45_08DT_1805.msi', 'azimuth': 32 - 70,
      'label': 'hbw40° (az322°)'},
     {'file': 'radiation_pattern/commscope/2NPX210R-V1_Port 2 - -45_08DT_1805.msi', 'azimuth': 32 + 40,
      'label': 'hbw40° (az72°)'},
     {'file': 'radiation_pattern/commscope/2NPX210R-V1_Port 2 - -45_08DT_1805.msi', 'azimuth': 32 + 80 + 20,
      'label': 'hbw40° (az132°)'},
 ]}


if __name__ == "__main__":
    """
    huawei_hbw60_metrics3, 
    huawei_hbw60_metrics1, 
    kathrein_hbw30_metrics1, 
    commscope_hbw40_metrics2, 
    commscope_hbw40_metrics3
    """

    sector_configs = huawei_hbw60_metrics3
    try:
        density_map = convert_to_decimal(sector_configs["density_map"])

        service = AntennaPatternService(density_map=density_map)
        service.process_sectors(
            sector_configs=sector_configs["sector_configs"],
            save_plot=True,
            plot_path='exact_patterns.png',
            min_ci_threshold=6.0,
            degradation_threshold_db=-10
        )
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()



