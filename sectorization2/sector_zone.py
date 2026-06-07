from functools import cached_property
from decimal import Decimal
from sectorization2.data.data import density_map
from sectorization2.decay import decay_then_amplify
from sectorization2 import settings


class ZoneSector():
    """zone_type in ['amplify', 'center', 'decay"',]"""
    def __init__(self, start: int, end: int, zone_type: str ):
        self.angle_start = start
        self.angle_end = end
        self._zone_type = zone_type
        self.min_coeff = settings.DEGRADATION_MIN_COEFFICIENT
        self.max_coeff = settings.DEGRADATION_MAX_COEFFICIENT

    @property
    def total_steps(self) -> int:
        if self.angle_start < self.angle_end:
            return self.angle_end - self.angle_start + 1
        if self.angle_start > self.angle_end:
            return self.angle_end + 360 - self.angle_start + 1

    @property
    def sum_traffic(self) -> Decimal:
        total_traffic = Decimal('0')
        if self.angle_start < self.angle_end:
            step = 0
            for degree in range(self.angle_start, self.angle_end+1):
                decay = self._list_decay[step]
                coef = density_map[degree] * decay
                total_traffic += coef
                step += 1
        else:
            step = 0
            for degree in range(self.angle_start, 360):
                decay = self._list_decay[step]
                coef = density_map[degree] * decay
                total_traffic += coef
                step += 1

            for degree in range(0, self.angle_end + 1):
                decay = self._list_decay[step]
                coef = density_map[degree] * decay
                total_traffic += coef
                step += 1

        return total_traffic

    @property
    def sum_degradation(self) -> Decimal:
        if self._zone_type in ['amplify', 'decay']:
            return self.sum_traffic
        return Decimal('0')

    @cached_property
    def _list_decay(self) -> list:
        list_decay = []
        for step in range(1, self.total_steps + 1):
            coeff = decay_then_amplify(step, self.min_coeff, self.max_coeff, self.total_steps, self._zone_type)
            list_decay.append(coeff)
        return list_decay

    def __repr__(self):
        return f"{self.total_steps} azimuths: {self.angle_start}°-{self.angle_end}°"

