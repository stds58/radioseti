from decimal import Decimal
from itertools import combinations
from sectorization2.sector import Sector
from sectorization2 import settings
from sectorization2.data.data import control_sum as all_traffic


class SectorCluster():
    def __init__(self):
        self.sectors: list[Sector] = []

    def add_sector(self, sector: Sector):
        self.sectors.append(sector)

    def get_sector(self, index: int) -> Sector:
        """Возвращает сектора строго в том порядке, в котором они были добавлены"""
        return self.sectors[index]

    @property
    def sum_traffic(self) -> dict:
        dic = {}
        for degree in range(0, 360):
            total_traffic = Decimal('0')
            step = degree
            for sector in self.sectors:
                total_traffic += sector.sum_traffic[self._normalize_azimuth(step)]
                step += sector._sector_width
            dic[degree] = total_traffic
        return dic

    @property
    def sum_degradation(self) -> dict:
        dic = {}
        for degree in range(0, 360):
            total_traffic = Decimal('0')
            step = degree
            for sector in self.sectors:
                total_traffic += sector.sum_degradation[self._normalize_azimuth(step)]
                step += sector._sector_width
            dic[degree] = total_traffic
        return dic

    def get_max_pairwise_imbalance(self) -> dict:
        """
        Считает максимальный дисбаланс среди всех возможных пар секторов.
        """
        dic = {}

        sector_order = {}
        start_angle = 0
        for sector in self.sectors:
            sector_order[sector] = start_angle
            start_angle += sector._sector_width

        # Создаем все уникальные пары
        pairs = list(combinations(sector_order, 2))

        for degree in range(0, 360):
            max_imbalance = Decimal('0')

            for pair in pairs:
                sector0 = pair[0]
                sector1 = pair[1]
                start0 = self._normalize_azimuth(degree + sector_order[sector0])
                start1 = self._normalize_azimuth(degree + sector_order[sector1])

                s1 = sector0.sum_traffic[start0]
                s2 = sector1.sum_traffic[start1]
                avg = s1 + s2
                imbalance = abs(s1 - s2) / avg * 100
                if imbalance > max_imbalance:
                    max_imbalance = imbalance

            dic[degree] = max_imbalance

        return dic

    def azimuths_more_than_treshhold(self, ) -> list:
        """возвращает список азимутов по которым сумма трафика сектора >= 80% от трафика по всем азимутам"""
        dic = self.sum_traffic
        L = []
        for degree, data in dic.items():
            if data*Decimal(100)/all_traffic >= settings.TRAFFIC_TRESHOLD:
                L.append(degree)
        return L

    @staticmethod
    def _normalize_azimuth(angle: int) -> int:
        """Приводит любой угол к диапазону [0, 359)."""
        return angle % 360

    def __iter__(self):
        return iter(self.sectors)

    def __len__(self):
        return len(self.sectors)

    def __repr__(self):
        return str(self.sectors)
