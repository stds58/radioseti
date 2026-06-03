"""
считает линейное затухание

Шаг 1: коэффициент = 0.3000
Шаг 2: коэффициент = 0.2400
Шаг 3: коэффициент = 0.1800
Шаг 4: коэффициент = 0.1200
Шаг 5: коэффициент = 0.0600
Шаг 6: коэффициент = 0.0000
"""

from decimal import Decimal

def linear_decay2(step: int, max_coeff: float, total_steps: int) -> Decimal:
    """
    Возвращает коэффициент линейного затухания для данного шага.

    :param step: текущий шаг (начинается с 1)
    :param max_coeff: максимальный коэффициент на первом шаге
    :param total_steps: общее количество шагов
    :return: коэффициент затухания для текущего шага
    """
    step = Decimal(f"{step}")
    max_coeff = Decimal(f"{max_coeff}")
    total_steps = Decimal(f"{total_steps}")
    d1 = Decimal("1")
    if step < d1 or step > total_steps:
        raise ValueError(f"Ваш шаг = {step} .Шаг должен быть в диапазоне от 1 до total_steps")

    # Линейное затухание: от max_coeff на шаге 1 до 0 на шаге total_steps
    coefficient = max_coeff * (d1 - (step - d1) / (total_steps - d1)) if total_steps > d1 else Decimal("0")

    return coefficient


def linear_decay(step: int, min_coeff: float, max_coeff: float, total_steps: int) -> Decimal:
    """
    Возвращает коэффициент линейного затухания для данного шага.

    :param step: текущий шаг (начинается с 1)
    :param max_coeff: максимальный коэффициент на первом шаге
    :param total_steps: общее количество шагов
    :param min_coeff: минимальный коэффициент на последнем шаге (по умолчанию 0)
    :return: коэффициент затухания для текущего шага
    """
    step = Decimal(f"{step}")
    max_coeff = Decimal(f"{max_coeff}")
    total_steps = Decimal(f"{total_steps}")
    min_coeff = Decimal(f"{min_coeff}")
    d1 = Decimal("1")

    if step < d1 or step > total_steps:
        raise ValueError(f"Ваш шаг = {step}. Шаг должен быть в диапазоне от 1 до total_steps = {total_steps}")

    # Линейное затухание: от max_coeff на шаге 1 до min_coeff на шаге total_steps
    if total_steps > d1:
        # t изменяется от 0 (step=1) до 1 (step=total_steps)
        t = (step - d1) / (total_steps - d1)
        coefficient = max_coeff - (max_coeff - min_coeff) * t
    else:
        # Если всего один шаг, возвращаем max_coeff (это первый шаг)
        coefficient = max_coeff

    return coefficient


def decay_then_amplify(step: int, min_coeff: float, max_coeff: float, total_steps: int, type: str) -> Decimal:
    """сначала затухание, потом усиление"""
    if type =="decay" :
        return linear_decay(step, min_coeff, max_coeff, total_steps)
    if type =="amplify":
        start = total_steps-step+1
        return linear_decay(start, min_coeff, max_coeff, total_steps)
    if type == "center":
        return linear_decay(step, max_coeff, max_coeff, total_steps)
    raise ValueError(f"Invalid type: {type}. Must be 'decay' or 'amplify' or 'center'")



if __name__ == "__main__":
    # Параметры
    max_coeff = 1
    min_coeff = 0.3
    total_steps = 8

    #decay_then_amplify(min_coeff, max_coeff, total_steps)
    steps = total_steps // 2
    for step in range(1, steps + 1):
        coeff = decay_then_amplify(step, min_coeff, max_coeff, steps, "amplify")
        print(f"Шаг {step}: коэффициент = {coeff}")

    for step in range(1, steps + 1):
        coeff = decay_then_amplify(step, min_coeff, max_coeff, steps, "decay")
        print(f"Шаг {step}: коэффициент = {coeff}")

    print("\n")
    for step in range(1, total_steps + 1):
        coeff = decay_then_amplify(step, min_coeff, max_coeff, total_steps, "center")
        print(f"Шаг {step}: коэффициент = {coeff}")
