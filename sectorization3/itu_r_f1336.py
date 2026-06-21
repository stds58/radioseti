import math

def itu_r_f1336_pattern(phi, HPBW, G0, FBR):
    """
    Расчёт усиления антенны по маске ITU-R F.1336.

    Параметры:
        phi   : угол отклонения от центра луча (градусы, 0..180)
        HPBW  : ПОЛНАЯ ширина луча по уровню -3 дБ (градусы)
                Для сектора 60° -> HPBW = 60
                Для сектора 40° -> HPBW = 40
                Для сектора 30° -> HPBW = 30
                Для сектора 20° -> HPBW = 20
        G0    : максимальное усиление в центре луча (dBi)
        FBR   : Front-to-Back Ratio (dB)
    """
    phi = abs(phi)
    theta_3db = HPBW / 2.0            # половинный угол для формулы
    phi_1 = 1.5 * theta_3db           # граница главного лепестка
    G_min = G0 - FBR

    if phi <= phi_1:
        G = G0 - 12.0 * (phi / HPBW) ** 2   # <-- ДЕЛИМ НА HPBW, а не на theta_3db
    else:
        G_transition = G0 - 12.0 * (phi_1 / HPBW) ** 2
        if phi <= 90:
            G = G_transition - 15.0 * math.log10(phi / phi_1)
        else:
            G_90 = G_transition - 15.0 * math.log10(90.0 / phi_1)
            if phi <= 120:
                G = G_90 + (G_min - G_90) * ((phi - 90.0) / 30.0)
            else:
                G = G_min
    return G


def generate_pattern_table(HPBW, G0, FBR, step=1.0):
    """Генерирует таблицу ДН от 0° до 180° с заданным шагом."""
    table = []
    phi = 0.0
    while phi <= 180.0:
        G = itu_r_f1336_pattern(phi, HPBW, G0, FBR)
        table.append((round(phi, 1), round(G, 2)))
        phi += step
    return table


# ============================================================
# КОНФИГУРАЦИИ (HPBW — ПОЛНАЯ ширина сектора)
# ============================================================

CONFIGS = {
    "Сектор 20° (2×20° или 3×20°)": {
        "HPBW": 20,
        "G0": 21.0,
        "FBR": 23.0,
    },
    "Сектор 30° (2×30° или 3×30°)": {
        "HPBW": 30,
        "G0": 20.0,
        "FBR": 25.0,
    },
    "Сектор 40° (3×40°)": {
        "HPBW": 40,
        "G0": 19.0,
        "FBR": 26.0,
    },
    "Сектор 60° (2×60°)": {
        "HPBW": 60,
        "G0": 18.0,
        "FBR": 27.0,
    },
}


if __name__ == "__main__":
    for name, params in CONFIGS.items():
        HPBW = params["HPBW"]
        G0 = params["G0"]
        FBR = params["FBR"]
        half_bw = HPBW / 2.0

        print(f"\n{'=' * 60}")
        print(f"  {name}")
        print(f"  G0 = {G0} dBi, FBR = {FBR} dB, HPBW = {HPBW}°")
        print(f"{'=' * 60}")
        print(f"{'Угол (°)':<12} {'Усиление (dBi)':<16}")
        print("-" * 28)

        table = generate_pattern_table(HPBW, G0, FBR, step=5)
        for phi, G in table:
            print(f"{phi:<12} {G:<16.1f}")

        print("\nКонтрольные точки:")
        print(f"  G(0°)    = {itu_r_f1336_pattern(0, HPBW, G0, FBR):.1f} dBi")
        print(f"  G(HPBW/2) = G({half_bw}°) = {itu_r_f1336_pattern(half_bw, HPBW, G0, FBR):.1f} dBi  (должно быть G0 - 3 = {G0 - 3:.1f})")
        print(f"  G(180°)  = {itu_r_f1336_pattern(180, HPBW, G0, FBR):.1f} dBi  (должно быть G0 - FBR = {G0 - FBR:.1f})")