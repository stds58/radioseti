import matplotlib
matplotlib.use('TkAgg')

import matplotlib.pyplot as plt
import numpy as np

from hw1.data import metrics
from sectorization.data import density_map

from sectorization.combinations_v1 import sector_interval_map, best_traffic_azimuth
#from sectorization.combinations2 import sector_interval_map, best_traffic_azimuth

##################################
best_traffic = list(best_traffic_azimuth.keys())[0]
best_start_azimuth = best_traffic_azimuth[best_traffic][0]
intervals_at_best = sector_interval_map[best_start_azimuth]
print(f"Интервалы для старта {best_start_azimuth}°:", intervals_at_best)

# Цвета для отрисовки 9 интервалов профиля (чередуем: деградация / основной луч)
# 4 (дег), 112 (осн), 8 (дег), 52 (осн)...
colors = ['#e5a491', '#e35327', '#e5a491', # к
          '#b0bda8', '#61e012', '#b0bda8', # з
          '#60d1af', '#138fd6', '#60d1af', # с
          '#808bc4', '#800080', '#808bc4', # ф
          '#c1c274', '#f6fa02', '#c1c274', # ж
          '#eddf5f', '#fcab08', '#eddf5f', # о
          '#c4b376', '#94938e', '#d6d5d2' # г
          ]
##################################


# Разделяем на градусы и плотность
list_degrees = []
list_densities = []

for degrees, densities in density_map.items():
    list_degrees.append(degrees)
    list_densities.append(float(densities))

# Сортируем данные по градусам
sorted_data = sorted(zip(list_degrees, list_densities), key=lambda x: x[0])
degrees = [x[0] for x in sorted_data]
densities = [x[1] for x in sorted_data]

# ЗАМЫКАЕМ КРУГ: добавляем первую точку в конец
degrees_closed = degrees + [degrees[0]]
densities_closed = densities + [densities[0]]

# Для полярного графика переводим в радианы
radians_closed = np.deg2rad(degrees_closed)

# Создаём фигуру с двумя подграфиками
fig = plt.figure(figsize=(12, 5))

# 1️⃣ Декартова система координат
ax_cart = fig.add_subplot(1, 2, 1)
ax_cart.plot(degrees, densities,
             marker='',
             linestyle='-',
             color='steelblue',
             linewidth=0.5)
ax_cart.set_xlabel('Градусы')
ax_cart.set_ylabel('Плотность трафика')
ax_cart.set_title('Декартова система координат')
ax_cart.grid(True)
ax_cart.set_xlim(0, 360)  # фиксируем диапазон от 0 до 360


##################################
# Рисуем интервалы секторов фоном
for i, (start, end) in enumerate(intervals_at_best):
    if start <= end:
        ax_cart.axvspan(start, end, alpha=0.6, color=colors[i])
    else:
        # Если интервал переходит через 360/0
        ax_cart.axvspan(start, 360, alpha=0.6, color=colors[i])
        ax_cart.axvspan(0, end, alpha=0.6, color=colors[i])

ax_cart.set_xlabel('Азимут (градусы)')
ax_cart.set_ylabel('Плотность трафика')
ax_cart.set_title(f'Декартова система (Сектора стартуют с {best_start_azimuth}°)')
ax_cart.set_xlim(0, 360)
ax_cart.grid(True, linestyle=':', alpha=0.5)
ax_cart.legend(loc='upper right')
##################################

# 2️⃣ Полярная система координат (с замыканием!)
ax_polar = fig.add_subplot(1, 2, 2, projection='polar')

##################################
max_val = max(densities)
# Рисуем сектора на полярном графике
for i, (start, end) in enumerate(intervals_at_best):
    if start <= end:
        theta = np.linspace(np.deg2rad(start), np.deg2rad(end), 50)
    else:
        # Переход через 0
        t1 = np.linspace(np.deg2rad(start), np.deg2rad(360), 25)
        t2 = np.linspace(0, np.deg2rad(end), 25)
        theta = np.concatenate([t1, t2])

    # Заполняем сектор от центра до края
    r = np.full_like(theta, max_val)
    ax_polar.fill_between(theta, 0, r, alpha=0.5, color=colors[i])
##################################

# Настраиваем "навигационную" систему: 0 сверху, по часовой стрелке
ax_polar.set_theta_zero_location('N')
ax_polar.set_theta_direction(-1)

ax_polar.plot(radians_closed, densities_closed,
              marker='',
              linestyle='-',
              color='crimson',
              linewidth=0.5)
ax_polar.set_title('Полярная система координат')
ax_polar.grid(True)

# # 🔹 Настраиваем деления и подписи
# # 1. Создаем все деления каждые 10 градусов (для сетки)
# all_ticks_deg = np.arange(0, 360, 10)
# all_ticks_rad = np.deg2rad(all_ticks_deg)
# ax_polar.set_xticks(all_ticks_rad)
#
# # 2. Оставляем подписи только для кратных 45 градусам
# labels = []
# for deg in all_ticks_deg:
#     if deg % 45 == 0:
#         labels.append(f'{deg}°')  # Подпись есть
#     else:
#         labels.append('')         # Подписи нет (пустая строка)
#
# ax_polar.set_xticklabels(labels)

plt.tight_layout()
plt.show()