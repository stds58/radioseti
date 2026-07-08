from azimuth_aggregation.app.repository import AzimuthRepository
from azimuth_aggregation.app.entity import Coordinates, Azimuth
from azimuth_aggregation.app.read_data import read_csv, group_by_avtocod_enodebid


class AzimuthService:
    def __init__(self, repository: AzimuthRepository, coordinates: Coordinates):
        self._repo = repository
        self._coordinates = coordinates

    async def create_dataset(self):
        df = await read_csv()
        df = await group_by_avtocod_enodebid(df)
        rows = df.to_dicts()
        for row in rows:
            azimuth_obj = self._create_azimuth_obj(row)
            await self._repo.save_data(azimuth=azimuth_obj)


    async def get_azimuth(self) -> list[dict]:
        data_raw = await self._repo.get_data(self._coordinates)
        data = self._to_dict(data_raw)
        return data


    def _create_azimuth_obj(self, dic: dict) -> Azimuth:
        azimuth_obj = Azimuth(
            avtocod=dic['avtocod'],
            enodebid=dic['enodebid'],
            azimuth=dic['azimuth'],
            nc_latitude=dic['nc_latitude'],
            nc_longitude=dic['nc_longitude'],
            cells=dic['cells'],
            uniq_count=dic['uniq_count']
        )
        return azimuth_obj

    def _to_dict(self, objs: list) -> list[dict]:
        data_new = list()
        for obj in objs:
            dic = {
                'avtocod': obj.avtocod,
                'enodebid': obj.enodebid,
                'azimuth': obj.azimuth,
                'nc_latitude': obj.nc_latitude,
                'nc_longitude': obj.nc_longitude,
                'cells': obj.cells,
                'uniq_count': obj.uniq_count
            }
            data_new.append(dic)
        return data_new
