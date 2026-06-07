from sectorization2 import settings
from sectorization2.sector_cluster import SectorCluster
from sectorization2.sector import Sector
from sectorization2.pareto_analyzer2 import (
    StandardParetoFilter,
    ClusterParetoProvider,
    MultiClusterParetoAnalyzer,
    ParetoVisualizer
)
from sectorization2.pareto_selector_evklid import DistanceBasedSelector
from sectorization2.pareto_selector_topsis import TopsisSelector


degradation_zone_width = settings.DEGRADATION_ZONE_WIDTH
config = settings.CONFIGURATIONS

clusters_data = {}

for cluster_name, sector_config in config.items():
    cluster = SectorCluster()
    clusters_data[cluster_name] = cluster
    for sector_width in sector_config:
        sector = Sector(sector_width, degradation_zone_width, )
        cluster.add_sector(sector)

#print(clusters_data)

# 1. Создаем стратегии
filter_strategy = StandardParetoFilter()
#selector_strategy = DistanceBasedSelector()
selector_strategy = TopsisSelector()

# 2. Создаем провайдеров для каждого кластера (Dependency Injection)
providers = {
    name: ClusterParetoProvider(cluster_id=name, cluster=cluster, filter_strategy=filter_strategy)
    for name, cluster in clusters_data.items()
}

# 3. Создаем и запускаем анализатор
analyzer = MultiClusterParetoAnalyzer(
    providers=providers,
    global_filter=filter_strategy
)

analyzer.analyze()

# 5. Выбираем лучшее решение глобально
best_overall = selector_strategy.select(analyzer.global_front)

# 4. Визуализируем результаты
visualizer = ParetoVisualizer()
visualizer.plot_3d_global(analyzer.global_front, best_point=best_overall, save_path="html/global_pareto.html")

# 5. Выбираем лучшее решение глобально
#best_overall = selector_strategy.select(analyzer.global_front)
if best_overall:
    print(f"\n✅ Лучшее решение:")
    print(f"   Кластер: {best_overall.cluster_id}")
    print(f"   Азимут: {best_overall.azimuth}°")
    print(f"   Дисбаланс: {best_overall.imbalance:.2f}%")
    print(f"   Деградация: {best_overall.degradation:.2f}")
    print(f"   Трафик: {best_overall.traffic:.2f}")
else:
    print("\n⚠️ Не удалось найти лучшее решение.")



