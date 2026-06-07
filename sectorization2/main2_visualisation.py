from sectorization2.visualizer2 import SectorVisualizer, VizPoint
from sectorization2.data.data import density_map
from sectorization2 import settings
from sectorization2.sector_cluster import SectorCluster
from sectorization2.sector import Sector
from sectorization2.pareto_analyzer2 import (
    StandardParetoFilter,
    DistanceBasedSelector,
    ClusterParetoProvider,
    MultiClusterParetoAnalyzer,
)


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
selector_strategy = DistanceBasedSelector()

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

viz = SectorVisualizer(density_map=density_map)

# Преобразуем ParetoPoint в VizPoint (или используй свой класс)
points_for_viz = [
    VizPoint(
        azimuth=p.azimuth,
        imbalance=p.imbalance,
        degradation=p.degradation,
        traffic=p.traffic,
        cluster_id=p.cluster_id
    )
    for p in analyzer.global_front
]


viz.plot_interactive(
    points=points_for_viz,
    clusters=clusters_data,
    save_path=None,
    show=True
)

