from typing import Any
from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict


@dataclass(frozen=True)
class Azimuth:

    avtocod: int
    enodebid: int
    azimuth: int
    nc_latitude: float
    nc_longitude: float
    cells: list[dict]
    uniq_count: int


class Coordinates(BaseModel):

    longitude1: float
    latitude1: float
    longitude2: float
    latitude2: float

    model_config = ConfigDict(from_attributes=True)
