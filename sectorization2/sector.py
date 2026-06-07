from decimal import Decimal
from functools import cached_property
from sectorization2.sector_zone import ZoneSector


class Sector():
    def __init__(self, sector_width: int, degradation_zone_width: int,):
        self._sector_width = sector_width
        self.left = degradation_zone_width
        self.center = sector_width - (2 * degradation_zone_width)
        self.right = degradation_zone_width

    @property
    def profile(self):
        return [self.left, self.center, self.right,]

    @cached_property
    def azimuth_interval_dic(self) -> dict:
        dic = {}
        for degree in range(0, 360):
            start = self._normalize_azimuth(degree)
            end = self._normalize_azimuth(degree+self.left-1)
            zone_sector_left = ZoneSector(start=start, end=end, zone_type="amplify")

            start = self._normalize_azimuth(degree+self.left)
            end = self._normalize_azimuth(degree+self.center+self.left-1)
            zone_sector_center = ZoneSector(start=start, end=end, zone_type="center")

            start = self._normalize_azimuth(degree+self.left+self.center)
            end = self._normalize_azimuth(degree+self.right+self.left+self.center-1)
            zone_sector_right = ZoneSector(start=start, end=end, zone_type="decay")

            L = [zone_sector_left, zone_sector_center, zone_sector_right]
            dic[degree] = L
        return dic

    @cached_property
    def sum_traffic(self) -> dict:
        dic = {}
        for azimuth, zone_sectors in self.azimuth_interval_dic.items():
            total_traffic = Decimal('0')
            for zone_sector in zone_sectors:
                total_traffic += zone_sector.sum_traffic
            dic[azimuth] = total_traffic
        return dic

    @cached_property
    def sum_degradation(self) -> dict:
        dic = {}
        for azimuth, zone_sectors in self.azimuth_interval_dic.items():
            total = Decimal('0')
            for zone_sector in zone_sectors:
                total += zone_sector.sum_degradation
            dic[azimuth] = total
        return dic

    @staticmethod
    def _normalize_azimuth(angle: int) -> int:
        """Приводит любой угол к диапазону [0, 359)."""
        return angle % 360

    def __repr__(self):
        return str(self.profile)
