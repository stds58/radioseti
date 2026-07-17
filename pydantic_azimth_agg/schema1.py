from typing import Dict, List, Any, Optional, ClassVar
from pydantic_azimth_agg.data_example import data
from pydantic import BaseModel, ConfigDict


class SingletonMixin(BaseModel):
    """Миксин для создания синглтонов с методами вложения и сериализации."""

    _singleton_instances: ClassVar[Dict[str, Any]] = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __new__(cls, *args, **kwargs):
        instance_key = cls._get_key(*args, **kwargs) if hasattr(cls, '_get_key') else id(cls)

        if instance_key not in cls._singleton_instances:
            instance = super().__new__(cls)
            cls._singleton_instances[instance_key] = instance
            object.__setattr__(instance, '_initialized', False)
        return cls._singleton_instances[instance_key]

    def __init__(self, **data):
        if hasattr(self, '_initialized') and self._initialized:
            return
        super().__init__(**data)
        object.__setattr__(self, '_initialized', True)
        object.__setattr__(self, 'children', {})
        object.__setattr__(self, 'children_key', None)

    def add_child(self, child: Any, key: str = None, children_key: str = None) -> None:
        """Добавляет дочерний объект."""
        if key is None:
            key = str(child.__class__.__name__)
        self.children[key] = child
        if children_key:
            object.__setattr__(self, 'children_key', children_key)

    def get_children(self) -> List[Any]:
        """Возвращает список всех дочерних объектов."""
        return list(self.children.values())

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь."""
        result = self.model_dump()

        if self.children and self.children_key:
            result[self.children_key] = [
                child.to_dict()
                for child in self.children.values()
            ]

        return result


class EnodeB(SingletonMixin):
    """Уровень 4."""
    avtocod: int
    nriid: str
    azimuth: int
    enodebid: int
    enodebname: str

    @classmethod
    def _get_key(cls, avtocod=None, nriid=None, azimuth=None, enodebid=None, **kwargs):
        if avtocod is None or nriid is None or azimuth is None or enodebid is None:
            return id(cls)
        return f"{avtocod}_{nriid}_{azimuth}_{enodebid}"


class Azimuth(SingletonMixin):
    """Уровень 3."""
    avtocod: int
    nriid: str
    azimuth: int

    @classmethod
    def _get_key(cls, avtocod=None, nriid=None, azimuth=None, **kwargs):
        if avtocod is None or nriid is None or azimuth is None:
            return id(cls)
        return f"{avtocod}_{nriid}_{azimuth}"


class Nri(SingletonMixin):
    """Уровень 2."""
    avtocod: int
    nriid: str
    nriname: str

    @classmethod
    def _get_key(cls, avtocod=None, nriid=None, **kwargs):
        if avtocod is None or nriid is None:
            return id(cls)
        return f"{avtocod}_{nriid}"


class Avtocod(SingletonMixin):
    """Уровень 1."""
    avtocod: int
    filial: str

    @classmethod
    def _get_key(cls, *args, **kwargs):
        return "avtocod"


def build_hierarchy(data_list: List[dict]) -> List[Avtocod]:
    """Строит иерархию объектов из списка словарей."""
    result = []

    for avtocod_data in data_list:
        avtocod = Avtocod(
            avtocod=avtocod_data['avtocod'],
            filial=avtocod_data['filial']
        )
        avtocod._children_key = 'nri'

        for nri_data in avtocod_data['nri']:
            nri = Nri(
                avtocod=nri_data['avtocod'],
                nriid=nri_data['nriid'],
                nriname=nri_data['nriname']
            )
            nri._children_key = 'azimuth'
            avtocod.add_child(nri, nri.nriid, 'nri')

            for azimuth_data in nri_data['azimuth']:
                azimuth = Azimuth(
                    avtocod=azimuth_data['avtocod'],
                    nriid=azimuth_data['nriid'],
                    azimuth=azimuth_data['azimuth']
                )
                azimuth._children_key = 'enodeb'
                nri.add_child(azimuth, str(azimuth.azimuth), 'azimuth')

                for enodeb_data in azimuth_data['enodeb']:
                    enodeb = EnodeB(
                        avtocod=enodeb_data['avtocod'],
                        nriid=enodeb_data['nriid'],
                        azimuth=enodeb_data['azimuth'],
                        enodebid=enodeb_data['enodebid'],
                        enodebname=enodeb_data['enodebname']
                    )
                    azimuth.add_child(enodeb, str(enodeb.enodebid), 'enodeb')

        result.append(avtocod)

    return result



if __name__ == '__main__':
    hierarchy = build_hierarchy(data)

    print("\n=== Проверка синглтона ===")
    avtocod1 = Avtocod()
    avtocod2 = Avtocod()
    print(f"avtocod1 is avtocod2: {avtocod1 is avtocod2}")
    print(f"avtocod2.avtocod: {avtocod2.avtocod}")

    print("\n=== Сериализация в словарь ===")
    import json

    dict_result = hierarchy[0].to_dict()
    print(json.dumps(dict_result, ensure_ascii=False, indent=2))





