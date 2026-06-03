"""
Возможные конфигурации секторов:
1)	120°(2x60°)
2)	60°(2x30°)
3)	40°(2x20°)
4)	120°(3x40°)
5)	60°(3x20°)

"""
from decimal import Decimal
from sectorization.data import density_map
from decay import linear_decay, decay_then_amplify

SECTOR_OVERLAP = 12
DEGRADATION_ZONE_WIDTH = SECTOR_OVERLAP // 2
DEGRADATION_MIN_COEFFICIENT = 0.3
DEGRADATION_MAX_COEFFICIENT = 1

#SECTOR_WIDTH = (20,)
#SECTOR_WIDTH = (50, 50, 50, 50, 50, 50, 50,)
SECTOR_WIDTH = (60,40,60,)
#SECTOR_WIDTH = (30,30,)
#SECTOR_WIDTH = (20,20,)
#SECTOR_WIDTH = (40, 40, 40,)
#SECTOR_WIDTH = (20, 20, 20,)

def calculate_sector_profile(sector_widths: tuple, degradation_zone_width: int) -> list:
    """
    создаёт список с секторами и зонами деградации
    например из (120, 60, 40, 60) получится [4, 112, 4, 4, 52, 4, 4, 32, 8, 52, 4]
    [4, 112, 8, 52, 8, 32, 8, 52, 4]
    :param sector_widths:
    :param degradation_zone_width:
    :return:
    """
    profile = []
    for sector_width, i in zip(sector_widths, range(1, len(sector_widths)+1)):
        profile.append(degradation_zone_width)
        width = sector_width - (2 * degradation_zone_width)
        profile.append(width)
        profile.append(degradation_zone_width)
    return profile

sector_profile = calculate_sector_profile(SECTOR_WIDTH, DEGRADATION_ZONE_WIDTH)
print(f"sector_profile {sector_profile}")


def normalize_azimuth(angle: int) -> int:
    """Приводит любой угол к диапазону [0, 359)."""
    return angle % 360


def build_sector_interval_map(sector_profile: list) -> dict:
    """
    Строит карту интервалов покрытия секторов для всех начальных азимутов.
    от каждого сектора отрезает интервал деградации.
    sector_profile = [6, 48, 6, 6, 48, 6]
    Правило «Левый включен, Правый исключен»
    Точка начала сектора входит в сектор.
    Точка конца сектора не входит в сектор (она принадлежит следующему).
    """
    dic = {}
    for degree in range(0, 360):
        step = degree
        L = []
        for item in sector_profile:
            angle_start = normalize_azimuth(step)
            angle_end = normalize_azimuth(step+item-1)
            m = [angle_start, angle_end]
            L.append(m)
            step += item
        dic[degree] = L
    return dic

sector_interval_map = build_sector_interval_map(sector_profile)
print(f"sector_interval_map {sector_interval_map}")
#print(density_map)


def calculate_azimuth_traffic(
        density_map: dict,
        sector_interval_map: dict,
        degradation_zone_width: int,
        degradation_min_coeff: float,
        degradation_max_coeff: float
) -> dict:
    """
    sector_type_idx
        порядковый номер интервала внутри интервала.
        нужен только для того, чтобы понять, интервал, это левая граница, центр или правая граница сектора
    offset
        считает позицию внутри конкретного интервала деградации (от 1 до ширины зоны)
    total_traffic
        сумма траффика в интервале

    :param density_map:
    :param sector_interval_map:
    :param degradation_zone_width:
    :param degradation_min_coeff:
    :param degradation_max_coeff:
    :return:
    """
    azimuth_traffic_map = {}
    total_sector_traffic_map = {}
    for azimuth, interval_map in sector_interval_map.items():

        total_traffic = Decimal('0')
        sector_traffic = Decimal('0')
        sector_type_idx = 1

        for interval in interval_map:
            sector_traffic_map = {}
            start = interval[0]
            end = interval[1]

            offset = 1

            for i in range(start, end + 1):
                if sector_type_idx % 3 == 1:
                    # левая часть сектора, уменьшение деградации
                    decay = decay_then_amplify(
                        step=offset,
                        min_coeff=degradation_min_coeff,
                        max_coeff=degradation_max_coeff,
                        total_steps=degradation_zone_width,
                        type="amplify"
                    )
                    coefficient = density_map[i] * decay
                    total_traffic += coefficient
                    sector_traffic += coefficient
                    offset += 1
                elif sector_type_idx % 3 == 0:
                    # правая часть сектора, увеличение деградации
                    decay = decay_then_amplify(
                        step=offset,
                        min_coeff=degradation_min_coeff,
                        max_coeff=degradation_max_coeff,
                        total_steps=degradation_zone_width,
                        type="decay"
                    )
                    coefficient = density_map[i] * decay
                    total_traffic += coefficient
                    sector_traffic += coefficient
                    offset += 1
                else:
                    # центральная часть сетора, нет деградауии
                    total_traffic += density_map[i]
                    sector_traffic += density_map[i]
            sector_type_idx += 1

            sector_traffic_map[f"{interval}"] = sector_traffic
            if total_sector_traffic_map.get(azimuth) is None:
                total_sector_traffic_map[azimuth] = [sector_traffic_map]
            else:
                total_sector_traffic_map[azimuth].append(sector_traffic_map)

        azimuth_traffic_map[azimuth] = total_traffic
    #print(f"total_sector_traffic_map {total_sector_traffic_map}")
    #print(f"azimuth_traffic_map {azimuth_traffic_map}")
    return azimuth_traffic_map

azimuth_traffic = calculate_azimuth_traffic(
    density_map,
    sector_interval_map,
    DEGRADATION_ZONE_WIDTH,
    DEGRADATION_MIN_COEFFICIENT,
    DEGRADATION_MAX_COEFFICIENT
)
#print(f"azimuth_traffic {azimuth_traffic}")


def get_best_position(azimuth_traffic: dict) -> dict:
    best_core = 0
    for azimuth, traffic in azimuth_traffic.items():
        if round(traffic,0) > best_core:
            best_core = round(traffic,0)

    dic = {}
    for azimuth, traffic in azimuth_traffic.items():
        if round(traffic,0) == best_core:
            if dic.get(best_core) is None:
                dic[best_core] = [azimuth]
            else:
                dic[best_core].append(azimuth)

    return dic

best_traffic_azimuth = get_best_position(azimuth_traffic)
print(best_traffic_azimuth)

def get_list_azimuths(sector_width: tuple, best_azimuth: int, degradation_zone_width: int) -> list:
    list_azimuths = []
    azimuth = best_azimuth
    for sector in sector_width:
        azimuth += sector / 2
        list_azimuths.append(azimuth)
        azimuth += (sector / 2) - degradation_zone_width
    return list_azimuths


best_azimuth = -1
for best_traffic, azimuth in best_traffic_azimuth.items():
    best_azimuth = azimuth[0]


list_azimuths = get_list_azimuths(SECTOR_WIDTH, best_azimuth, DEGRADATION_ZONE_WIDTH)
print(f"SECTOR_WIDTH {SECTOR_WIDTH}")
print(f"best_traffic_azimuth {best_traffic_azimuth}")
print(f"list_azimuths {list_azimuths}")
#print(azimuth_traffic)



