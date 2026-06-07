from decimal import Decimal
from sectorization2 import settings
from sectorization2.sector_cluster import SectorCluster
from sectorization2.sector import Sector
from sectorization2.pareto_analyzer import ParetoAnalyzer
from sectorization2.visualizer import SectorVisualizer
from sectorization2.data.data import density_map



# CONFIGURATIONS = {
#     "1) 120°(2x60°)": (60, 60,),
#     "2) 60°(2x30°)": (30, 30),
#     "3) 40°(2x20°)": (20, 20),
#     "4) 120°(3x40°)": (40, 40, 40),
#     "5) 60°(3x20°)": (20, 20, 20),
#     "60+40+60": (60, 40, 60),
#     "360°(3x120°)": (120, 120, 120),
#     "30": (10, 10, 10),
#     "120": (120,),
# }

degradation_zone_width = settings.DEGRADATION_ZONE_WIDTH
config = settings.CONFIGURATIONS.get('1) 120°(2x60°)')
print(f"config {config}")
cluster = SectorCluster()
az = 203
for sector_width in config:
    sector = Sector(sector_width, degradation_zone_width, )
    cluster.add_sector(sector)
    # print(f"sector_width {sector_width}")
    # print(f"sector {sector}")
    # print(f"sector.azimuth_interval_dic {sector.azimuth_interval_dic}")
    #print(f"sector.sum_traffic {sector.sum_traffic[az]}")
    #print(f"sector.sum_degradation {sector.sum_degradation}")
    az += 20

#print(f"cluster.sectors {cluster.sectors}")
#print(f"cluster.sum_traffic {cluster.sum_traffic}")
#print(f"cluster.get_max_pairwise_imbalance {cluster.get_max_pairwise_imbalance()}")

analyzer = ParetoAnalyzer(cluster)

# Получаем Парето-фронт
pareto_front = analyzer.get_pareto_front()

print(f"Найдено {len(pareto_front)} недоминируемых решений:")
for p in pareto_front:  # показываем первые 10 [:10]
    print(f"  Azimuth {p['azimuth']}°: Imbalance={p['imbalance']:.2f}%, "
            f"Degradation={p['degradation']:.2f}, Traffic={p['traffic']:.2f}")

# Визуализация
analyzer.visualize_2d_projections(pareto_front, save_path="img/pareto_2d.png")
analyzer.visualize_3d(pareto_front, save_path="img/pareto_3d.html")

# # Выбор лучшего решения
# best_by_distance = analyzer.select_best_by_distance(pareto_front)
# print(f"\nЛучшее по расстоянию: Azimuth {best_by_distance['azimuth']}°")
# Выбор лучшего решения С УЧЕТОМ ПОРОГА ТРАФИКА
# min_traffic_threshold=0.85 означает, что мы рассматриваем только те решения,
# где трафик составляет не менее 85% от максимального на Парето-фронте
best_with_traffic = analyzer.select_by_traffic_constraint(
    pareto_front,
    min_traffic_threshold=Decimal(0.85)
)

if best_with_traffic:
    print(f"\n✅ Лучшее решение (трафик >= 85%): Azimuth {best_with_traffic['azimuth']}°")
    print(f"   Дисбаланс: {best_with_traffic['imbalance']:.2f}%")
    print(f"   Деградация: {best_with_traffic['degradation']:.2f}")
    print(f"   Трафик: {best_with_traffic['traffic']:.2f}")
else:
    print("\n Не удалось найти решение, удовлетворяющее порогу трафика.")

# Выбор по ограничению
constrained = analyzer.select_by_constraints(pareto_front, max_imbalance=10.0)
print(f"\nРешений с дисбалансом трафика <= 10%: {len(constrained)}")

# === ВЫЗОВ ВИЗУАЛИЗАЦИИ ===
start_azimuth = best_with_traffic['azimuth']
viz = SectorVisualizer(density_map=density_map)
viz.draw_cluster_with_traffic(
    azimuth=start_azimuth,
    cluster=cluster,
    save_path="img/cluster_with_traffic.png",
    show=True
)

