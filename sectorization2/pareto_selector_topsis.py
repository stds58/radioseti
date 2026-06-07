"""
    Выбор лучшего решения методом TOPSIS (Technique for Order of Preference
    by Similarity to Ideal Solution).

    СМЫСЛ МЕТОДА:
    TOPSIS основан на идее, что лучшее решение должно быть одновременно:
    1. Максимально близко к идеальному решению (ideal solution)
    2. Максимально далеко от анти-идеального решения (anti-ideal solution)

    В отличие от простого евклидова расстояния, TOPSIS учитывает не только
    близость к идеалу, но и удалённость от худшего варианта. Это делает
    метод более устойчивым и сбалансированным.

    АЛГОРИТМ:
    1. Нормализация матрицы решений (векторная нормализация)
    2. Определение идеального решения A+ (лучшие значения по каждому критерию)
    3. Определение анти-идеального решения A- (худшие значения)
    4. Вычисление евклидова расстояния до A+ (d+) и до A- (d-)
    5. Расчёт относительной близости: C = d- / (d+ + d-)
    6. Ранжирование по убыванию C (чем ближе к 1, тем лучше)

    ДЛЯ НАШЕЙ ЗАДАЧИ:
    - Imbalance: cost criterion (минимизируем) → идеал = min, анти-идеал = max
    - Degradation: cost criterion (минимизируем) → идеал = min, анти-идеал = max
    - Traffic: benefit criterion (максимизируем) → идеал = max, анти-идеал = min

    ПРЕИМУЩЕСТВА:
    - Учитывает как близость к идеалу, так и удалённость от худшего
    - Даёт более сбалансированный выбор
    - Устойчив к выбросам
    - Позволяет добавлять веса критериев (если нужно)
    """
from typing import List, Optional
from sectorization2.pareto_interface import ParetoPoint
import numpy as np


class TopsisSelector:

    def select(self, points: List[ParetoPoint]) -> Optional[ParetoPoint]:
        if not points:
            return None

        # Шаг 1: Извлекаем матрицу решений
        # Строки = точки, столбцы = критерии [imbalance, degradation, traffic]
        n = len(points)
        matrix = np.zeros((n, 3))

        for i, point in enumerate(points):
            matrix[i, 0] = point.imbalance
            matrix[i, 1] = point.degradation
            matrix[i, 2] = point.traffic

        # Шаг 2: Векторная нормализация
        # r_ij = x_ij / sqrt(sum(x_ij^2)) для каждого столбца
        norms = np.sqrt(np.sum(matrix ** 2, axis=0))
        # Защита от деления на ноль
        norms[norms == 0] = 1
        normalized = matrix / norms

        # Шаг 3: Определяем идеальное и анти-идеальное решения
        # Для cost критериев (imbalance, degradation): идеал = min, анти-идеал = max
        # Для benefit критерия (traffic): идеал = max, анти-идеал = min
        ideal = np.array([
            np.min(normalized[:, 0]),  # min imbalance (cost)
            np.min(normalized[:, 1]),  # min degradation (cost)
            np.max(normalized[:, 2])  # max traffic (benefit)
        ])

        anti_ideal = np.array([
            np.max(normalized[:, 0]),  # max imbalance (cost)
            np.max(normalized[:, 1]),  # max degradation (cost)
            np.min(normalized[:, 2])  # min traffic (benefit)
        ])

        # Шаг 4: Вычисляем расстояния до идеального и анти-идеального решений
        d_plus = np.sqrt(np.sum((normalized - ideal) ** 2, axis=1))
        d_minus = np.sqrt(np.sum((normalized - anti_ideal) ** 2, axis=1))

        # Шаг 5: Рассчитываем относительную близость к идеальному решению
        # C_i = d_minus / (d_plus + d_minus)
        # Если обе дистанции = 0, то точка одновременно идеальна и анти-идеальна
        # (все точки одинаковы), ставим C = 0.5
        denominator = d_plus + d_minus
        denominator[denominator == 0] = 1  # Защита от деления на ноль
        closeness = d_minus / denominator

        # Шаг 6: Выбираем точку с максимальной близостью к идеалу
        best_idx = np.argmax(closeness)

        return points[best_idx]

