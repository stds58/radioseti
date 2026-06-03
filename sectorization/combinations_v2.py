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
from decay import decay_then_amplify
from sectorization.visualisation_v2 import SectorVisualizer


class Sector():
    """
    azimuth:
        угол поворота левой границы кластера секторов.
    left:
        левая часть сектора с возрастающей деградацией
    center:
        центральная часть сектора без деградации
    right:
        правая часть сектора с убывающей деградацией
    left(center,right)_interval_map:
        какие градусы занимает часть сектора в зависимости от азимута {"azimuth": [[0, 5], [6, 53], [54, 59]],}
    left(center,right)_traffic:
        сумма трафика части сектора в зависимости от азимута {"azimuth": "traffic",}
    """
    def __init__(self, sector_width: int, degradation_zone_width: int,):
        self.left = degradation_zone_width
        self.left_interval_map = {}
        self.left_traffic = {}
        self.center = sector_width - (2 * degradation_zone_width)
        self.center_interval_map = {}
        self.center_traffic = {}
        self.right = degradation_zone_width
        self.right_interval_map = {}
        self.right_traffic = {}
        self.azimuth_traffic = {}

    @property
    def profile(self):
        return [self.left, self.center, self.right,]

    def add_left_interval_map(self, azimuth: int, interval: list):
        self.left_interval_map[azimuth] = interval

    def add_center_interval_map(self, azimuth: int, interval: list):
        self.center_interval_map[azimuth] = interval

    def add_right_interval_map(self, azimuth: int, interval: list):
        self.right_interval_map[azimuth] = interval

    def add_left_traffic(self, azimuth: int, traffic: Decimal):
        self.left_traffic[azimuth] = traffic

    def add_center_traffic(self, azimuth: int, traffic: Decimal):
        self.center_traffic[azimuth] = traffic

    def add_right_traffic(self, azimuth: int, traffic: Decimal):
        self.right_traffic[azimuth] = traffic

    @property
    def calculate_azimuth_traffic(self) -> dict:
        dic = {}
        for degree in range(0, 360):
            total_traffic =  self.left_traffic[degree] + self.center_traffic[degree] + self.right_traffic[degree]
            dic[degree] = total_traffic
        return dic

    def __repr__(self):
        return str(self.profile)


class SectorCluster():
    def __init__(self,degradation_min_coeff, degradation_max_coeff,):
        self._degradation_min_coeff = degradation_min_coeff
        self._degradation_max_coeff = degradation_max_coeff
        self.sectors: list[Sector] = []

    def add_sector(self, sector: Sector):
        self.sectors.append(sector)

    def get_sector(self, index: int) -> Sector:
        """Возвращает сектора строго в том порядке, в котором они были добавлены"""
        return self.sectors[index]

    def calculate_density_map(self) -> dict:
        dic = {}
        for degree in range(0, 360):
            total_traffic = Decimal('0')
            dic[degree] = total_traffic
            for sector in self.sectors:
                total_traffic += sector.calculate_azimuth_traffic[degree]
            dic[degree] = total_traffic
        return dic

    def __iter__(self):
        return iter(self.sectors)

    def __len__(self):
        return len(self.sectors)


class SectorTrafficAnalyzer():
    def __init__(self, cluster: SectorCluster):
        self._cluster = cluster

    @staticmethod
    def _normalize_azimuth(angle: int) -> int:
        """Приводит любой угол к диапазону [0, 359)."""
        return angle % 360

    def build_interval_map(self) -> None:
        """Строит карту интервалов"""
        dic = {}

        for degree in range(0, 360):
            step = degree
            for sector in self._cluster:
                item0 = sector.profile[0]
                self._process_interval_map(sector.add_left_interval_map, item0, degree, step)
                step += item0

                item1 = sector.profile[1]
                self._process_interval_map(sector.add_center_interval_map, item1, degree, step)
                step += item1

                item2 = sector.profile[2]
                self._process_interval_map(sector.add_right_interval_map, item2, degree, step)
                step += item2
        return None

    def _process_interval_map(self, method_add_interval_map, item, azimuth, step ):
        angle_start = self._normalize_azimuth(step)
        angle_end = self._normalize_azimuth(step + item - 1)
        interval = [angle_start, angle_end]
        method_add_interval_map(azimuth=azimuth, interval=interval)

    def calculate_azimuth_traffic(self,) -> None:
        for sector in self._cluster:
            self._process_zone_traffic(
                method_interval_map=sector.left_interval_map,
                method_add_traffic=sector.add_left_traffic,
                min_coeff=self._cluster._degradation_min_coeff,
                max_coeff=self._cluster._degradation_max_coeff,
                total_steps=sector.left,
                type="amplify"
            )

            self._process_zone_traffic(
                method_interval_map=sector.center_interval_map,
                method_add_traffic=sector.add_center_traffic,
                min_coeff=self._cluster._degradation_max_coeff,
                max_coeff=self._cluster._degradation_max_coeff,
                total_steps=sector.center,
                type="center"
            )

            self._process_zone_traffic(
                method_interval_map=sector.right_interval_map,
                method_add_traffic=sector.add_right_traffic,
                min_coeff=self._cluster._degradation_min_coeff,
                max_coeff=self._cluster._degradation_max_coeff,
                total_steps=sector.right,
                type="decay"
            )

    def _process_zone_traffic(self, method_interval_map, method_add_traffic, min_coeff, max_coeff, total_steps, type):
        for azimuth, interval in method_interval_map.items():
            traffic = Decimal('0')
            start = interval[0]
            end = interval[1]
            offset = 1
            if start < end:
                for degree in range(start, end + 1):
                    decay = decay_then_amplify(offset, min_coeff, max_coeff, total_steps, type)
                    coefficient = density_map[degree] * decay
                    traffic += coefficient
                    offset += 1

                method_add_traffic(azimuth=azimuth, traffic=traffic)
            else:
                for degree in range(start, 360):
                    decay = decay_then_amplify(offset, min_coeff, max_coeff, total_steps, type)
                    coefficient = density_map[degree] * decay
                    traffic += coefficient
                    offset += 1

                for degree in range(0, end + 1):
                    decay = decay_then_amplify(offset, min_coeff, max_coeff, total_steps, type)
                    coefficient = density_map[degree] * decay
                    traffic += coefficient
                    offset += 1

                method_add_traffic(azimuth=azimuth, traffic=traffic)


    @property
    def get_interval_map(self) -> dict:
        """
        {
        0: [[0, 5], [6, 53], [54, 59], [60, 65], [66, 93], [94, 99], [100, 105], [106, 153], [154, 159]],
        1: [[1, 6], [7, 54], [55, 60], [61, 66], [67, 94], [95, 100], [101, 106], [107, 154], [155, 160]],
        ... }
        :return:
        """
        dic = {}
        for degree in range(0, 360):
            sector_list = []
            for sector in self._cluster:
                sector_list.append(sector.left_interval_map[degree])
                sector_list.append(sector.center_interval_map[degree])
                sector_list.append(sector.right_interval_map[degree])
            dic[degree] = sector_list
        return dic


class SectorOptimizer:
    def __init__(self, cluster: SectorCluster, degradation_zone_width: int):
        self._cluster = cluster
        self._degradation_zone_width = degradation_zone_width

    def find_best_positions(self, azimuth_traffic: dict) -> dict:
        """
        Находит азимуты с максимальным суммарным трафиком.
        Возвращает словарь вида: {максимальный_трафик: [список_подходящих_азимутов]}
        """
        best_score = Decimal('0')
        for traffic in azimuth_traffic.values():
            score = round(traffic, 0)
            if score > best_score:
                best_score = score

        best_azimuths = [
            az for az, traffic in azimuth_traffic.items()
            if round(traffic, 0) == best_score
        ]

        return {int(best_score): best_azimuths}

    def find_balanced_positions(
            self,
            imbalance_weight: Decimal = Decimal('1'),
            degradation_weight: Decimal = Decimal('1'),
            traffic_weight: Decimal = Decimal('0')
    ) -> dict:
        """
        Находит азимуты, при которых трафик в секторах максимально сбалансирован
        (стремится к равенству), а трафик в зонах деградации минимален (стремится к 0).

        :param imbalance_weight: Вес штрафа за неравномерность распределения трафика между секторами.
        :param degradation_weight: Вес штрафа за трафик в зонах деградации.
        :return: Словарь с лучшими азимутами и детальными метриками.
        """
        metrics = {}

        # 1. Сбор метрик для каждого азимута
        for az in range(360):
            totals = []
            degradations = []
            for sector in self._cluster:
                total = sector.calculate_azimuth_traffic[az]
                deg = sector.left_traffic[az] + sector.right_traffic[az]
                totals.append(total)
                degradations.append(deg)

            # Разница между самым загруженным и самым свободным сектором
            imbalance = max(totals) - min(totals)
            # Суммарный трафик в зонах деградации всех секторов
            total_degradation = sum(degradations)
            # Суммарный трафик кластера
            total_traffic_sum = sum(totals)

            metrics[az] = {
                'totals': totals,
                'degradations': degradations,
                'imbalance': imbalance,
                'total_degradation': total_degradation,
                'total_traffic': total_traffic_sum,
            }

        # 2. Нормализация метрик для корректного сравнения (избегаем проблем с разными масштабами)
        max_imbalance = max(m['imbalance'] for m in metrics.values())
        max_degradation = max(m['total_degradation'] for m in metrics.values())
        max_traffic = max(m['total_traffic'] for m in metrics.values()) or Decimal('1')

        scores = {}
        for az in range(360):
            # Нормируем от 0 до 1
            norm_imb = metrics[az]['imbalance'] / max_imbalance if max_imbalance > 0 else Decimal('0')
            norm_deg = metrics[az]['total_degradation'] / max_degradation if max_degradation > 0 else Decimal('0')
            # Если трафик максимален, norm_traffic = 1. Нам нужно, чтобы штраф был 0.
            # Формула: 1 - (текущий / макс)
            norm_traffic_penalty = Decimal('1') - (metrics[az]['total_traffic'] / max_traffic)

            # Чем меньше score, тем лучше (минимизируем штраф)
            score = (norm_imb * imbalance_weight) + \
                    (norm_deg * degradation_weight) + \
                    (norm_traffic_penalty * traffic_weight)
            scores[az] = score

        # 3. Поиск азимутов с минимальным штрафом
        min_score = min(scores.values())
        best_azimuths = [az for az, score in scores.items() if score == min_score]

        return {
            'best_score': min_score,
            'best_azimuths': best_azimuths,
            'metrics': metrics
        }

    def get_optimal_sector_azimuths(self, best_start_azimuth: int) -> list:
        """
        Рассчитывает центральные (или опорные) азимуты для каждого сектора
        в кластере, начиная с лучшего стартового азимута.
        """
        list_azimuths = []
        current_azimuth = best_start_azimuth

        for sector in self._cluster:
            sector_width = sum(sector.profile)  # Общая ширина сектора (left + center + right)

            # Смещаемся на половину сектора, чтобы найти его центр/опорную точку
            current_azimuth += sector_width // 2
            list_azimuths.append(current_azimuth % 360)

            # Смещаемся для начала следующего сектора
            # (оригинальная логика: + половина сектора - зона деградации)
            current_azimuth += (sector_width // 2) - self._degradation_zone_width

        return list_azimuths


def create_report(
        degradation_zone_width: int,
        degradation_min_coeficient: float,
        degradation_max_coefficient: float,
        sector_width: tuple,
        imbalance_weight: Decimal,
        degradation_weight: Decimal,
        traffic_weight: Decimal,
):
    cluster = SectorCluster(degradation_min_coeficient, degradation_max_coefficient)
    for item in sector_width:
        sector = Sector(item, degradation_zone_width, )
        cluster.add_sector(sector)

    print(f"cluster.sectors {cluster.sectors}")

    analyz = SectorTrafficAnalyzer(cluster)
    analyz.build_interval_map()
    sector_interval_map = analyz.get_interval_map
    print(f"sector_interval_map {sector_interval_map}")
    analyz.calculate_azimuth_traffic()

    azimuth_traffic = cluster.calculate_density_map()
    print(f"azimuth_traffic {azimuth_traffic}")

    optimizer = SectorOptimizer(cluster, degradation_zone_width)
    best_traffic_azimuth = optimizer.find_best_positions(azimuth_traffic)
    print(f"best_traffic_azimuth {best_traffic_azimuth}")

    best_azimuth = -1
    for best_traffic, azimuth in best_traffic_azimuth.items():
        best_azimuth = azimuth[0]
        break

    list_azimuths = optimizer.get_optimal_sector_azimuths(best_azimuth)
    print(f"list_azimuths {list_azimuths}")

    # 2. Поиск сбалансированной позиции (новая логика)
    # Если вам важнее убрать трафик из зон деградации, увеличьте degradation_weight (например, Decimal('2'))
    balanced_result = optimizer.find_balanced_positions(
        imbalance_weight=imbalance_weight,
        degradation_weight=degradation_weight,
        traffic_weight=traffic_weight
    )

    print(f"balanced_result['best_azimuths'] {balanced_result['best_azimuths']}")
    best_balanced_azimuth = balanced_result['best_azimuths'][0]
    print(f"\nЛучший сбалансированный азимут: {best_balanced_azimuth}")
    print(f"Детальные метрики для него: {balanced_result['metrics'][best_balanced_azimuth]}")

    # 3. Получение итоговых углов поворота секторов для сбалансированного варианта
    balanced_list_azimuths = optimizer.get_optimal_sector_azimuths(best_balanced_azimuth)
    print(f"Итоговые азимуты секторов (сбалансированные): {balanced_list_azimuths}")

    best_traffic = list(best_traffic_azimuth.keys())[0]

    return {
        'sector_width': sector_width,
        'best_traffic': best_traffic,
        'best_start_azimuth': best_balanced_azimuth,
        'intervals_at_best': sector_interval_map[best_balanced_azimuth],
        'balanced_list_azimuths': balanced_list_azimuths,
        #'metrics': balanced_result['metrics'][best_balanced_azimuth],
        'balanced_metrics': balanced_result['metrics'][best_balanced_azimuth],
        'optimizer': optimizer,
        'sector_interval_map': sector_interval_map,
        'best_traffic_azimuth': best_traffic_azimuth,
    }


def main(
        configurations: dict,
        degradation_zone_width: int,
        degradation_min_coeficient: float,
        degradation_max_coefficient: float,
        imbalance_weight: Decimal,
        degradation_weight: Decimal,
        traffic_weight: Decimal,
):
    all_results = []

    for config_name, sector_width in configurations.items():
        print(f"\n{'=' * 80}")
        print(f"КОНФИГУРАЦИЯ: {config_name} | Ширина секторов: {sector_width}")
        print(f"{'=' * 80}")

        try:
            result = create_report(
                degradation_zone_width=degradation_zone_width,
                degradation_min_coeficient=degradation_min_coeficient,
                degradation_max_coefficient=degradation_max_coefficient,
                sector_width=sector_width,
                imbalance_weight=imbalance_weight,
                degradation_weight=degradation_weight,
                traffic_weight=traffic_weight,
            )

            # === ОБРАБОТКА НЕСКОЛЬКИХ ЛУЧШИХ АЗИМУТОВ ===
            best_traffic_val = result['best_traffic']
            intervals_map = result['sector_interval_map']
            optimizer = result['optimizer']

            # Ищем все азимуты с максимальным трафиком
            all_best_azimuths = []
            for az, traffic in result['best_traffic_azimuth'].items():
                if isinstance(traffic, list):
                    all_best_azimuths.extend(traffic)
                elif round(result['best_traffic_azimuth'][list(result['best_traffic_azimuth'].keys())[0]][0],
                           0) == round(traffic, 0):
                    # Fallback если структура словаря другая, но обычно там список
                    pass

                    # Более надежный способ получить список лучших азимутов из результата main
            # Так как main возвращает best_traffic_azimuth, мы берем значения этого словаря
            actual_best_azimuths = []
            target_score = list(result['best_traffic_azimuth'].keys())[0]
            for az_list in result['best_traffic_azimuth'].values():
                if isinstance(az_list, list):
                    actual_best_azimuths.extend(az_list)
                else:
                    actual_best_azimuths.append(az_list)

            # Убираем дубликаты сохраняя порядок
            seen = set()
            unique_best_azimuths = []
            for az in actual_best_azimuths:
                if az not in seen:
                    seen.add(az)
                    unique_best_azimuths.append(az)

            print(f"🔍 Найдено лучших азимутов: {len(unique_best_azimuths)} -> {unique_best_azimuths}")

            # Создаем отдельную запись для визуализации КАЖДОГО лучшего азимута
            for idx, az in enumerate(unique_best_azimuths):
                viz_entry = {
                    'name': f"{config_name} (Вариант {idx + 1}: {az}°)",
                    'best_start_azimuth': az,
                    'intervals_at_best': intervals_map[az],
                    'best_traffic': float(best_traffic_val),
                    'metrics': result['balanced_metrics'],
                    'sector_azimuths': optimizer.get_optimal_sector_azimuths(az)
                }
                all_results.append(viz_entry)
                print(f"   ✅ Добавлен в визуализацию: Вариант {idx + 1} (Азимут {az}°)")
            # ==============================================

        except Exception as e:
            print(f"❌ Ошибка при анализе {config_name}: {e}")
            import traceback

            traceback.print_exc()

        # === ВИЗУАЛИЗАЦИЯ ВСЕХ КОНФИГУРАЦИЙ ===
    if all_results:
        print("\n" + "=" * 80)
        print("ПОСТРОЕНИЕ ГРАФИКОВ...")
        print("=" * 80)

        try:
            viz = SectorVisualizer(density_map)
            viz.plot_multiple_configurations(all_results, show=True)

        except ImportError as ie:
            print(f"⚠️ Не удалось импортировать визуализатор: {ie}")
            print("💡 Убедитесь, что файл 'visualisation_v2.py' лежит рядом с этим скриптом.")
    else:
        print("\nНет результатов для визуализации.")


if __name__ == '__main__':
    DEGRADATION_ZONE_WIDTH = 6
    DEGRADATION_MIN_COEFFICIENT = 0.3
    DEGRADATION_MAX_COEFFICIENT = 1
    IMBALANCE_WEIGHT = Decimal('1')
    DEGRADATION_WEIGHT = Decimal('1')
    TRAFFIC_WEIGHT = Decimal('0')

    # Все конфигурации для перебора
    CONFIGURATIONS = {
        "1) 120°(2x60°)": (60, 60,),
        "2) 60°(2x30°)": (30, 30),
        "3) 40°(2x20°)": (20, 20),
        "4) 120°(3x40°)": (40, 40, 40),
        "5) 60°(3x20°)": (20, 20, 20),
        "60+40+60": (60, 40, 60),
        "360°(3x120°)": (120, 120, 120),
    }
    main(
        configurations=CONFIGURATIONS,
        degradation_zone_width=DEGRADATION_ZONE_WIDTH,
        degradation_min_coeficient=DEGRADATION_MIN_COEFFICIENT,
        degradation_max_coefficient=DEGRADATION_MAX_COEFFICIENT,
        imbalance_weight=IMBALANCE_WEIGHT,
        degradation_weight=DEGRADATION_WEIGHT,
        traffic_weight=TRAFFIC_WEIGHT,
    )
