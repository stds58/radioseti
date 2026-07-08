from abc import ABC, abstractmethod

from azimuth_aggregation.app.entity import Azimuth
from azimuth_aggregation.app.entity import Coordinates


class AzimuthRepository(ABC):
    @abstractmethod
    async def get_data(self, coordinates: Coordinates) -> Azimuth | None: ...

    @abstractmethod
    async def save_data(self, azimuth: Azimuth) -> None: ...


class InMemoryAzimuthRepository(AzimuthRepository):
    """
    Реализация AzimuthRepository
    """
    def __init__(self):
        self._data = []

    async def get_data(self, coordinates: Coordinates) -> list:
        result = []
        for row in self._data:
            if (row.nc_latitude <= coordinates.latitude2 and row.nc_longitude >= coordinates.longitude1 and
                row.nc_latitude <= coordinates.latitude2 and row.nc_longitude <= coordinates.longitude2 and
                row.nc_latitude >= coordinates.latitude1 and row.nc_longitude >= coordinates.longitude1 and
                row.nc_latitude >= coordinates.latitude1 and row.nc_longitude <= coordinates.longitude2
            ):
                result.append(row)
        return result


    async def save_data(self, azimuth: Azimuth) -> None:
        self._data.append(azimuth)
