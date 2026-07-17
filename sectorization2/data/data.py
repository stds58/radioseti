"""
числа переводятся в Decimal
данные конвертитруются в словарь для быстрого доступа
"""
from decimal import Decimal
from typing import List

from sectorization2.data.data_raw1 import raw_data as metrics1
from sectorization2.data.data_raw2 import raw_data as metrics2
from sectorization2.data.data_raw3 import raw_data as metrics3


metrics = metrics3


def convert_to_decimal(metrics:List[tuple]) -> dict:
    data_new = {}
    for item_tuple in metrics:
        degree, density = item_tuple
        if degree == 360:
            degree = 0
        data_new[degree] = Decimal(f"{density}")
    return data_new

density_map = convert_to_decimal(metrics)


def calculate_control_sum(data:dict) -> Decimal:
    """
    control_sum = 153233.19553721372012
    :param data:
    :return:
    """
    control_sum = Decimal('0')
    for degree, density in data.items():
        control_sum += density
    return control_sum

control_sum = calculate_control_sum(density_map)


if __name__ == "__main__":
    print(f"control_sum {control_sum}")
