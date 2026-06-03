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


def main(
        degradation_zone_width: int,
        degradation_min_coeficient: float,
        degradation_max_coefficient: float,
        sector_width: tuple,
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
        imbalance_weight=Decimal('1'),
        degradation_weight=Decimal('1'),
        traffic_weight=Decimal('0')
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

    #################################

    # visualizer = SectorVisualizer(density_map)
    #
    # all_configs = []
    # for result in all_results:
    #     all_configs.append({
    #         'name': result['name'],
    #         'best_start_azimuth': result['best_start_azimuth'],
    #         'intervals_at_best': result['intervals_at_best'],
    #         'best_traffic': result['best_traffic'],
    #         'metrics': result['balanced_metrics']
    #     })
    #
    # visualizer.plot_multiple_configurations(all_configs)


if __name__ == '__main__':
    # DEGRADATION_ZONE_WIDTH = 4
    # DEGRADATION_MIN_COEFFICIENT = 0.3
    # DEGRADATION_MAX_COEFFICIENT = 1
    #
    # SECTOR_WIDTH = (60, 40, 60,)
    # # SECTOR_WIDTH = (120, 120, 120,) будет 3 решения
    #
    # main(
    #     degradation_zone_width=DEGRADATION_ZONE_WIDTH,
    #     degradation_min_coeficient=DEGRADATION_MIN_COEFFICIENT,
    #     degradation_max_coefficient=DEGRADATION_MAX_COEFFICIENT,
    #     sector_width=SECTOR_WIDTH,
    # )

    DEGRADATION_ZONE_WIDTH = 6
    DEGRADATION_MIN_COEFFICIENT = 0.3
    DEGRADATION_MAX_COEFFICIENT = 1

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

    all_results = []

    for config_name, sector_width in CONFIGURATIONS.items():
        print(f"\n{'=' * 80}")
        print(f"КОНФИГУРАЦИЯ: {config_name} | Ширина секторов: {sector_width}")
        print(f"{'=' * 80}")

        try:
            result = main(
                degradation_zone_width=DEGRADATION_ZONE_WIDTH,
                degradation_min_coeficient=DEGRADATION_MIN_COEFFICIENT,
                degradation_max_coefficient=DEGRADATION_MAX_COEFFICIENT,
                sector_width=sector_width,
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





#sector_interval_map {0: [[0, 5], [6, 53], [54, 59], [60, 65], [66, 93], [94, 99], [100, 105], [106, 153], [154, 159]], 1: [[1, 6], [7, 54], [55, 60], [61, 66], [67, 94], [95, 100], [101, 106], [107, 154], [155, 160]], 2: [[2, 7], [8, 55], [56, 61], [62, 67], [68, 95], [96, 101], [102, 107], [108, 155], [156, 161]], 3: [[3, 8], [9, 56], [57, 62], [63, 68], [69, 96], [97, 102], [103, 108], [109, 156], [157, 162]], 4: [[4, 9], [10, 57], [58, 63], [64, 69], [70, 97], [98, 103], [104, 109], [110, 157], [158, 163]], 5: [[5, 10], [11, 58], [59, 64], [65, 70], [71, 98], [99, 104], [105, 110], [111, 158], [159, 164]], 6: [[6, 11], [12, 59], [60, 65], [66, 71], [72, 99], [100, 105], [106, 111], [112, 159], [160, 165]], 7: [[7, 12], [13, 60], [61, 66], [67, 72], [73, 100], [101, 106], [107, 112], [113, 160], [161, 166]], 8: [[8, 13], [14, 61], [62, 67], [68, 73], [74, 101], [102, 107], [108, 113], [114, 161], [162, 167]], 9: [[9, 14], [15, 62], [63, 68], [69, 74], [75, 102], [103, 108], [109, 114], [115, 162], [163, 168]], 10: [[10, 15], [16, 63], [64, 69], [70, 75], [76, 103], [104, 109], [110, 115], [116, 163], [164, 169]], 11: [[11, 16], [17, 64], [65, 70], [71, 76], [77, 104], [105, 110], [111, 116], [117, 164], [165, 170]], 12: [[12, 17], [18, 65], [66, 71], [72, 77], [78, 105], [106, 111], [112, 117], [118, 165], [166, 171]], 13: [[13, 18], [19, 66], [67, 72], [73, 78], [79, 106], [107, 112], [113, 118], [119, 166], [167, 172]], 14: [[14, 19], [20, 67], [68, 73], [74, 79], [80, 107], [108, 113], [114, 119], [120, 167], [168, 173]], 15: [[15, 20], [21, 68], [69, 74], [75, 80], [81, 108], [109, 114], [115, 120], [121, 168], [169, 174]], 16: [[16, 21], [22, 69], [70, 75], [76, 81], [82, 109], [110, 115], [116, 121], [122, 169], [170, 175]], 17: [[17, 22], [23, 70], [71, 76], [77, 82], [83, 110], [111, 116], [117, 122], [123, 170], [171, 176]], 18: [[18, 23], [24, 71], [72, 77], [78, 83], [84, 111], [112, 117], [118, 123], [124, 171], [172, 177]], 19: [[19, 24], [25, 72], [73, 78], [79, 84], [85, 112], [113, 118], [119, 124], [125, 172], [173, 178]], 20: [[20, 25], [26, 73], [74, 79], [80, 85], [86, 113], [114, 119], [120, 125], [126, 173], [174, 179]], 21: [[21, 26], [27, 74], [75, 80], [81, 86], [87, 114], [115, 120], [121, 126], [127, 174], [175, 180]], 22: [[22, 27], [28, 75], [76, 81], [82, 87], [88, 115], [116, 121], [122, 127], [128, 175], [176, 181]], 23: [[23, 28], [29, 76], [77, 82], [83, 88], [89, 116], [117, 122], [123, 128], [129, 176], [177, 182]], 24: [[24, 29], [30, 77], [78, 83], [84, 89], [90, 117], [118, 123], [124, 129], [130, 177], [178, 183]], 25: [[25, 30], [31, 78], [79, 84], [85, 90], [91, 118], [119, 124], [125, 130], [131, 178], [179, 184]], 26: [[26, 31], [32, 79], [80, 85], [86, 91], [92, 119], [120, 125], [126, 131], [132, 179], [180, 185]], 27: [[27, 32], [33, 80], [81, 86], [87, 92], [93, 120], [121, 126], [127, 132], [133, 180], [181, 186]], 28: [[28, 33], [34, 81], [82, 87], [88, 93], [94, 121], [122, 127], [128, 133], [134, 181], [182, 187]], 29: [[29, 34], [35, 82], [83, 88], [89, 94], [95, 122], [123, 128], [129, 134], [135, 182], [183, 188]], 30: [[30, 35], [36, 83], [84, 89], [90, 95], [96, 123], [124, 129], [130, 135], [136, 183], [184, 189]], 31: [[31, 36], [37, 84], [85, 90], [91, 96], [97, 124], [125, 130], [131, 136], [137, 184], [185, 190]], 32: [[32, 37], [38, 85], [86, 91], [92, 97], [98, 125], [126, 131], [132, 137], [138, 185], [186, 191]], 33: [[33, 38], [39, 86], [87, 92], [93, 98], [99, 126], [127, 132], [133, 138], [139, 186], [187, 192]], 34: [[34, 39], [40, 87], [88, 93], [94, 99], [100, 127], [128, 133], [134, 139], [140, 187], [188, 193]], 35: [[35, 40], [41, 88], [89, 94], [95, 100], [101, 128], [129, 134], [135, 140], [141, 188], [189, 194]], 36: [[36, 41], [42, 89], [90, 95], [96, 101], [102, 129], [130, 135], [136, 141], [142, 189], [190, 195]], 37: [[37, 42], [43, 90], [91, 96], [97, 102], [103, 130], [131, 136], [137, 142], [143, 190], [191, 196]], 38: [[38, 43], [44, 91], [92, 97], [98, 103], [104, 131], [132, 137], [138, 143], [144, 191], [192, 197]], 39: [[39, 44], [45, 92], [93, 98], [99, 104], [105, 132], [133, 138], [139, 144], [145, 192], [193, 198]], 40: [[40, 45], [46, 93], [94, 99], [100, 105], [106, 133], [134, 139], [140, 145], [146, 193], [194, 199]], 41: [[41, 46], [47, 94], [95, 100], [101, 106], [107, 134], [135, 140], [141, 146], [147, 194], [195, 200]], 42: [[42, 47], [48, 95], [96, 101], [102, 107], [108, 135], [136, 141], [142, 147], [148, 195], [196, 201]], 43: [[43, 48], [49, 96], [97, 102], [103, 108], [109, 136], [137, 142], [143, 148], [149, 196], [197, 202]], 44: [[44, 49], [50, 97], [98, 103], [104, 109], [110, 137], [138, 143], [144, 149], [150, 197], [198, 203]], 45: [[45, 50], [51, 98], [99, 104], [105, 110], [111, 138], [139, 144], [145, 150], [151, 198], [199, 204]], 46: [[46, 51], [52, 99], [100, 105], [106, 111], [112, 139], [140, 145], [146, 151], [152, 199], [200, 205]], 47: [[47, 52], [53, 100], [101, 106], [107, 112], [113, 140], [141, 146], [147, 152], [153, 200], [201, 206]], 48: [[48, 53], [54, 101], [102, 107], [108, 113], [114, 141], [142, 147], [148, 153], [154, 201], [202, 207]], 49: [[49, 54], [55, 102], [103, 108], [109, 114], [115, 142], [143, 148], [149, 154], [155, 202], [203, 208]], 50: [[50, 55], [56, 103], [104, 109], [110, 115], [116, 143], [144, 149], [150, 155], [156, 203], [204, 209]], 51: [[51, 56], [57, 104], [105, 110], [111, 116], [117, 144], [145, 150], [151, 156], [157, 204], [205, 210]], 52: [[52, 57], [58, 105], [106, 111], [112, 117], [118, 145], [146, 151], [152, 157], [158, 205], [206, 211]], 53: [[53, 58], [59, 106], [107, 112], [113, 118], [119, 146], [147, 152], [153, 158], [159, 206], [207, 212]], 54: [[54, 59], [60, 107], [108, 113], [114, 119], [120, 147], [148, 153], [154, 159], [160, 207], [208, 213]], 55: [[55, 60], [61, 108], [109, 114], [115, 120], [121, 148], [149, 154], [155, 160], [161, 208], [209, 214]], 56: [[56, 61], [62, 109], [110, 115], [116, 121], [122, 149], [150, 155], [156, 161], [162, 209], [210, 215]], 57: [[57, 62], [63, 110], [111, 116], [117, 122], [123, 150], [151, 156], [157, 162], [163, 210], [211, 216]], 58: [[58, 63], [64, 111], [112, 117], [118, 123], [124, 151], [152, 157], [158, 163], [164, 211], [212, 217]], 59: [[59, 64], [65, 112], [113, 118], [119, 124], [125, 152], [153, 158], [159, 164], [165, 212], [213, 218]], 60: [[60, 65], [66, 113], [114, 119], [120, 125], [126, 153], [154, 159], [160, 165], [166, 213], [214, 219]], 61: [[61, 66], [67, 114], [115, 120], [121, 126], [127, 154], [155, 160], [161, 166], [167, 214], [215, 220]], 62: [[62, 67], [68, 115], [116, 121], [122, 127], [128, 155], [156, 161], [162, 167], [168, 215], [216, 221]], 63: [[63, 68], [69, 116], [117, 122], [123, 128], [129, 156], [157, 162], [163, 168], [169, 216], [217, 222]], 64: [[64, 69], [70, 117], [118, 123], [124, 129], [130, 157], [158, 163], [164, 169], [170, 217], [218, 223]], 65: [[65, 70], [71, 118], [119, 124], [125, 130], [131, 158], [159, 164], [165, 170], [171, 218], [219, 224]], 66: [[66, 71], [72, 119], [120, 125], [126, 131], [132, 159], [160, 165], [166, 171], [172, 219], [220, 225]], 67: [[67, 72], [73, 120], [121, 126], [127, 132], [133, 160], [161, 166], [167, 172], [173, 220], [221, 226]], 68: [[68, 73], [74, 121], [122, 127], [128, 133], [134, 161], [162, 167], [168, 173], [174, 221], [222, 227]], 69: [[69, 74], [75, 122], [123, 128], [129, 134], [135, 162], [163, 168], [169, 174], [175, 222], [223, 228]], 70: [[70, 75], [76, 123], [124, 129], [130, 135], [136, 163], [164, 169], [170, 175], [176, 223], [224, 229]], 71: [[71, 76], [77, 124], [125, 130], [131, 136], [137, 164], [165, 170], [171, 176], [177, 224], [225, 230]], 72: [[72, 77], [78, 125], [126, 131], [132, 137], [138, 165], [166, 171], [172, 177], [178, 225], [226, 231]], 73: [[73, 78], [79, 126], [127, 132], [133, 138], [139, 166], [167, 172], [173, 178], [179, 226], [227, 232]], 74: [[74, 79], [80, 127], [128, 133], [134, 139], [140, 167], [168, 173], [174, 179], [180, 227], [228, 233]], 75: [[75, 80], [81, 128], [129, 134], [135, 140], [141, 168], [169, 174], [175, 180], [181, 228], [229, 234]], 76: [[76, 81], [82, 129], [130, 135], [136, 141], [142, 169], [170, 175], [176, 181], [182, 229], [230, 235]], 77: [[77, 82], [83, 130], [131, 136], [137, 142], [143, 170], [171, 176], [177, 182], [183, 230], [231, 236]], 78: [[78, 83], [84, 131], [132, 137], [138, 143], [144, 171], [172, 177], [178, 183], [184, 231], [232, 237]], 79: [[79, 84], [85, 132], [133, 138], [139, 144], [145, 172], [173, 178], [179, 184], [185, 232], [233, 238]], 80: [[80, 85], [86, 133], [134, 139], [140, 145], [146, 173], [174, 179], [180, 185], [186, 233], [234, 239]], 81: [[81, 86], [87, 134], [135, 140], [141, 146], [147, 174], [175, 180], [181, 186], [187, 234], [235, 240]], 82: [[82, 87], [88, 135], [136, 141], [142, 147], [148, 175], [176, 181], [182, 187], [188, 235], [236, 241]], 83: [[83, 88], [89, 136], [137, 142], [143, 148], [149, 176], [177, 182], [183, 188], [189, 236], [237, 242]], 84: [[84, 89], [90, 137], [138, 143], [144, 149], [150, 177], [178, 183], [184, 189], [190, 237], [238, 243]], 85: [[85, 90], [91, 138], [139, 144], [145, 150], [151, 178], [179, 184], [185, 190], [191, 238], [239, 244]], 86: [[86, 91], [92, 139], [140, 145], [146, 151], [152, 179], [180, 185], [186, 191], [192, 239], [240, 245]], 87: [[87, 92], [93, 140], [141, 146], [147, 152], [153, 180], [181, 186], [187, 192], [193, 240], [241, 246]], 88: [[88, 93], [94, 141], [142, 147], [148, 153], [154, 181], [182, 187], [188, 193], [194, 241], [242, 247]], 89: [[89, 94], [95, 142], [143, 148], [149, 154], [155, 182], [183, 188], [189, 194], [195, 242], [243, 248]], 90: [[90, 95], [96, 143], [144, 149], [150, 155], [156, 183], [184, 189], [190, 195], [196, 243], [244, 249]], 91: [[91, 96], [97, 144], [145, 150], [151, 156], [157, 184], [185, 190], [191, 196], [197, 244], [245, 250]], 92: [[92, 97], [98, 145], [146, 151], [152, 157], [158, 185], [186, 191], [192, 197], [198, 245], [246, 251]], 93: [[93, 98], [99, 146], [147, 152], [153, 158], [159, 186], [187, 192], [193, 198], [199, 246], [247, 252]], 94: [[94, 99], [100, 147], [148, 153], [154, 159], [160, 187], [188, 193], [194, 199], [200, 247], [248, 253]], 95: [[95, 100], [101, 148], [149, 154], [155, 160], [161, 188], [189, 194], [195, 200], [201, 248], [249, 254]], 96: [[96, 101], [102, 149], [150, 155], [156, 161], [162, 189], [190, 195], [196, 201], [202, 249], [250, 255]], 97: [[97, 102], [103, 150], [151, 156], [157, 162], [163, 190], [191, 196], [197, 202], [203, 250], [251, 256]], 98: [[98, 103], [104, 151], [152, 157], [158, 163], [164, 191], [192, 197], [198, 203], [204, 251], [252, 257]], 99: [[99, 104], [105, 152], [153, 158], [159, 164], [165, 192], [193, 198], [199, 204], [205, 252], [253, 258]], 100: [[100, 105], [106, 153], [154, 159], [160, 165], [166, 193], [194, 199], [200, 205], [206, 253], [254, 259]], 101: [[101, 106], [107, 154], [155, 160], [161, 166], [167, 194], [195, 200], [201, 206], [207, 254], [255, 260]], 102: [[102, 107], [108, 155], [156, 161], [162, 167], [168, 195], [196, 201], [202, 207], [208, 255], [256, 261]], 103: [[103, 108], [109, 156], [157, 162], [163, 168], [169, 196], [197, 202], [203, 208], [209, 256], [257, 262]], 104: [[104, 109], [110, 157], [158, 163], [164, 169], [170, 197], [198, 203], [204, 209], [210, 257], [258, 263]], 105: [[105, 110], [111, 158], [159, 164], [165, 170], [171, 198], [199, 204], [205, 210], [211, 258], [259, 264]], 106: [[106, 111], [112, 159], [160, 165], [166, 171], [172, 199], [200, 205], [206, 211], [212, 259], [260, 265]], 107: [[107, 112], [113, 160], [161, 166], [167, 172], [173, 200], [201, 206], [207, 212], [213, 260], [261, 266]], 108: [[108, 113], [114, 161], [162, 167], [168, 173], [174, 201], [202, 207], [208, 213], [214, 261], [262, 267]], 109: [[109, 114], [115, 162], [163, 168], [169, 174], [175, 202], [203, 208], [209, 214], [215, 262], [263, 268]], 110: [[110, 115], [116, 163], [164, 169], [170, 175], [176, 203], [204, 209], [210, 215], [216, 263], [264, 269]], 111: [[111, 116], [117, 164], [165, 170], [171, 176], [177, 204], [205, 210], [211, 216], [217, 264], [265, 270]], 112: [[112, 117], [118, 165], [166, 171], [172, 177], [178, 205], [206, 211], [212, 217], [218, 265], [266, 271]], 113: [[113, 118], [119, 166], [167, 172], [173, 178], [179, 206], [207, 212], [213, 218], [219, 266], [267, 272]], 114: [[114, 119], [120, 167], [168, 173], [174, 179], [180, 207], [208, 213], [214, 219], [220, 267], [268, 273]], 115: [[115, 120], [121, 168], [169, 174], [175, 180], [181, 208], [209, 214], [215, 220], [221, 268], [269, 274]], 116: [[116, 121], [122, 169], [170, 175], [176, 181], [182, 209], [210, 215], [216, 221], [222, 269], [270, 275]], 117: [[117, 122], [123, 170], [171, 176], [177, 182], [183, 210], [211, 216], [217, 222], [223, 270], [271, 276]], 118: [[118, 123], [124, 171], [172, 177], [178, 183], [184, 211], [212, 217], [218, 223], [224, 271], [272, 277]], 119: [[119, 124], [125, 172], [173, 178], [179, 184], [185, 212], [213, 218], [219, 224], [225, 272], [273, 278]], 120: [[120, 125], [126, 173], [174, 179], [180, 185], [186, 213], [214, 219], [220, 225], [226, 273], [274, 279]], 121: [[121, 126], [127, 174], [175, 180], [181, 186], [187, 214], [215, 220], [221, 226], [227, 274], [275, 280]], 122: [[122, 127], [128, 175], [176, 181], [182, 187], [188, 215], [216, 221], [222, 227], [228, 275], [276, 281]], 123: [[123, 128], [129, 176], [177, 182], [183, 188], [189, 216], [217, 222], [223, 228], [229, 276], [277, 282]], 124: [[124, 129], [130, 177], [178, 183], [184, 189], [190, 217], [218, 223], [224, 229], [230, 277], [278, 283]], 125: [[125, 130], [131, 178], [179, 184], [185, 190], [191, 218], [219, 224], [225, 230], [231, 278], [279, 284]], 126: [[126, 131], [132, 179], [180, 185], [186, 191], [192, 219], [220, 225], [226, 231], [232, 279], [280, 285]], 127: [[127, 132], [133, 180], [181, 186], [187, 192], [193, 220], [221, 226], [227, 232], [233, 280], [281, 286]], 128: [[128, 133], [134, 181], [182, 187], [188, 193], [194, 221], [222, 227], [228, 233], [234, 281], [282, 287]], 129: [[129, 134], [135, 182], [183, 188], [189, 194], [195, 222], [223, 228], [229, 234], [235, 282], [283, 288]], 130: [[130, 135], [136, 183], [184, 189], [190, 195], [196, 223], [224, 229], [230, 235], [236, 283], [284, 289]], 131: [[131, 136], [137, 184], [185, 190], [191, 196], [197, 224], [225, 230], [231, 236], [237, 284], [285, 290]], 132: [[132, 137], [138, 185], [186, 191], [192, 197], [198, 225], [226, 231], [232, 237], [238, 285], [286, 291]], 133: [[133, 138], [139, 186], [187, 192], [193, 198], [199, 226], [227, 232], [233, 238], [239, 286], [287, 292]], 134: [[134, 139], [140, 187], [188, 193], [194, 199], [200, 227], [228, 233], [234, 239], [240, 287], [288, 293]], 135: [[135, 140], [141, 188], [189, 194], [195, 200], [201, 228], [229, 234], [235, 240], [241, 288], [289, 294]], 136: [[136, 141], [142, 189], [190, 195], [196, 201], [202, 229], [230, 235], [236, 241], [242, 289], [290, 295]], 137: [[137, 142], [143, 190], [191, 196], [197, 202], [203, 230], [231, 236], [237, 242], [243, 290], [291, 296]], 138: [[138, 143], [144, 191], [192, 197], [198, 203], [204, 231], [232, 237], [238, 243], [244, 291], [292, 297]], 139: [[139, 144], [145, 192], [193, 198], [199, 204], [205, 232], [233, 238], [239, 244], [245, 292], [293, 298]], 140: [[140, 145], [146, 193], [194, 199], [200, 205], [206, 233], [234, 239], [240, 245], [246, 293], [294, 299]], 141: [[141, 146], [147, 194], [195, 200], [201, 206], [207, 234], [235, 240], [241, 246], [247, 294], [295, 300]], 142: [[142, 147], [148, 195], [196, 201], [202, 207], [208, 235], [236, 241], [242, 247], [248, 295], [296, 301]], 143: [[143, 148], [149, 196], [197, 202], [203, 208], [209, 236], [237, 242], [243, 248], [249, 296], [297, 302]], 144: [[144, 149], [150, 197], [198, 203], [204, 209], [210, 237], [238, 243], [244, 249], [250, 297], [298, 303]], 145: [[145, 150], [151, 198], [199, 204], [205, 210], [211, 238], [239, 244], [245, 250], [251, 298], [299, 304]], 146: [[146, 151], [152, 199], [200, 205], [206, 211], [212, 239], [240, 245], [246, 251], [252, 299], [300, 305]], 147: [[147, 152], [153, 200], [201, 206], [207, 212], [213, 240], [241, 246], [247, 252], [253, 300], [301, 306]], 148: [[148, 153], [154, 201], [202, 207], [208, 213], [214, 241], [242, 247], [248, 253], [254, 301], [302, 307]], 149: [[149, 154], [155, 202], [203, 208], [209, 214], [215, 242], [243, 248], [249, 254], [255, 302], [303, 308]], 150: [[150, 155], [156, 203], [204, 209], [210, 215], [216, 243], [244, 249], [250, 255], [256, 303], [304, 309]], 151: [[151, 156], [157, 204], [205, 210], [211, 216], [217, 244], [245, 250], [251, 256], [257, 304], [305, 310]], 152: [[152, 157], [158, 205], [206, 211], [212, 217], [218, 245], [246, 251], [252, 257], [258, 305], [306, 311]], 153: [[153, 158], [159, 206], [207, 212], [213, 218], [219, 246], [247, 252], [253, 258], [259, 306], [307, 312]], 154: [[154, 159], [160, 207], [208, 213], [214, 219], [220, 247], [248, 253], [254, 259], [260, 307], [308, 313]], 155: [[155, 160], [161, 208], [209, 214], [215, 220], [221, 248], [249, 254], [255, 260], [261, 308], [309, 314]], 156: [[156, 161], [162, 209], [210, 215], [216, 221], [222, 249], [250, 255], [256, 261], [262, 309], [310, 315]], 157: [[157, 162], [163, 210], [211, 216], [217, 222], [223, 250], [251, 256], [257, 262], [263, 310], [311, 316]], 158: [[158, 163], [164, 211], [212, 217], [218, 223], [224, 251], [252, 257], [258, 263], [264, 311], [312, 317]], 159: [[159, 164], [165, 212], [213, 218], [219, 224], [225, 252], [253, 258], [259, 264], [265, 312], [313, 318]], 160: [[160, 165], [166, 213], [214, 219], [220, 225], [226, 253], [254, 259], [260, 265], [266, 313], [314, 319]], 161: [[161, 166], [167, 214], [215, 220], [221, 226], [227, 254], [255, 260], [261, 266], [267, 314], [315, 320]], 162: [[162, 167], [168, 215], [216, 221], [222, 227], [228, 255], [256, 261], [262, 267], [268, 315], [316, 321]], 163: [[163, 168], [169, 216], [217, 222], [223, 228], [229, 256], [257, 262], [263, 268], [269, 316], [317, 322]], 164: [[164, 169], [170, 217], [218, 223], [224, 229], [230, 257], [258, 263], [264, 269], [270, 317], [318, 323]], 165: [[165, 170], [171, 218], [219, 224], [225, 230], [231, 258], [259, 264], [265, 270], [271, 318], [319, 324]], 166: [[166, 171], [172, 219], [220, 225], [226, 231], [232, 259], [260, 265], [266, 271], [272, 319], [320, 325]], 167: [[167, 172], [173, 220], [221, 226], [227, 232], [233, 260], [261, 266], [267, 272], [273, 320], [321, 326]], 168: [[168, 173], [174, 221], [222, 227], [228, 233], [234, 261], [262, 267], [268, 273], [274, 321], [322, 327]], 169: [[169, 174], [175, 222], [223, 228], [229, 234], [235, 262], [263, 268], [269, 274], [275, 322], [323, 328]], 170: [[170, 175], [176, 223], [224, 229], [230, 235], [236, 263], [264, 269], [270, 275], [276, 323], [324, 329]], 171: [[171, 176], [177, 224], [225, 230], [231, 236], [237, 264], [265, 270], [271, 276], [277, 324], [325, 330]], 172: [[172, 177], [178, 225], [226, 231], [232, 237], [238, 265], [266, 271], [272, 277], [278, 325], [326, 331]], 173: [[173, 178], [179, 226], [227, 232], [233, 238], [239, 266], [267, 272], [273, 278], [279, 326], [327, 332]], 174: [[174, 179], [180, 227], [228, 233], [234, 239], [240, 267], [268, 273], [274, 279], [280, 327], [328, 333]], 175: [[175, 180], [181, 228], [229, 234], [235, 240], [241, 268], [269, 274], [275, 280], [281, 328], [329, 334]], 176: [[176, 181], [182, 229], [230, 235], [236, 241], [242, 269], [270, 275], [276, 281], [282, 329], [330, 335]], 177: [[177, 182], [183, 230], [231, 236], [237, 242], [243, 270], [271, 276], [277, 282], [283, 330], [331, 336]], 178: [[178, 183], [184, 231], [232, 237], [238, 243], [244, 271], [272, 277], [278, 283], [284, 331], [332, 337]], 179: [[179, 184], [185, 232], [233, 238], [239, 244], [245, 272], [273, 278], [279, 284], [285, 332], [333, 338]], 180: [[180, 185], [186, 233], [234, 239], [240, 245], [246, 273], [274, 279], [280, 285], [286, 333], [334, 339]], 181: [[181, 186], [187, 234], [235, 240], [241, 246], [247, 274], [275, 280], [281, 286], [287, 334], [335, 340]], 182: [[182, 187], [188, 235], [236, 241], [242, 247], [248, 275], [276, 281], [282, 287], [288, 335], [336, 341]], 183: [[183, 188], [189, 236], [237, 242], [243, 248], [249, 276], [277, 282], [283, 288], [289, 336], [337, 342]], 184: [[184, 189], [190, 237], [238, 243], [244, 249], [250, 277], [278, 283], [284, 289], [290, 337], [338, 343]], 185: [[185, 190], [191, 238], [239, 244], [245, 250], [251, 278], [279, 284], [285, 290], [291, 338], [339, 344]], 186: [[186, 191], [192, 239], [240, 245], [246, 251], [252, 279], [280, 285], [286, 291], [292, 339], [340, 345]], 187: [[187, 192], [193, 240], [241, 246], [247, 252], [253, 280], [281, 286], [287, 292], [293, 340], [341, 346]], 188: [[188, 193], [194, 241], [242, 247], [248, 253], [254, 281], [282, 287], [288, 293], [294, 341], [342, 347]], 189: [[189, 194], [195, 242], [243, 248], [249, 254], [255, 282], [283, 288], [289, 294], [295, 342], [343, 348]], 190: [[190, 195], [196, 243], [244, 249], [250, 255], [256, 283], [284, 289], [290, 295], [296, 343], [344, 349]], 191: [[191, 196], [197, 244], [245, 250], [251, 256], [257, 284], [285, 290], [291, 296], [297, 344], [345, 350]], 192: [[192, 197], [198, 245], [246, 251], [252, 257], [258, 285], [286, 291], [292, 297], [298, 345], [346, 351]], 193: [[193, 198], [199, 246], [247, 252], [253, 258], [259, 286], [287, 292], [293, 298], [299, 346], [347, 352]], 194: [[194, 199], [200, 247], [248, 253], [254, 259], [260, 287], [288, 293], [294, 299], [300, 347], [348, 353]], 195: [[195, 200], [201, 248], [249, 254], [255, 260], [261, 288], [289, 294], [295, 300], [301, 348], [349, 354]], 196: [[196, 201], [202, 249], [250, 255], [256, 261], [262, 289], [290, 295], [296, 301], [302, 349], [350, 355]], 197: [[197, 202], [203, 250], [251, 256], [257, 262], [263, 290], [291, 296], [297, 302], [303, 350], [351, 356]], 198: [[198, 203], [204, 251], [252, 257], [258, 263], [264, 291], [292, 297], [298, 303], [304, 351], [352, 357]], 199: [[199, 204], [205, 252], [253, 258], [259, 264], [265, 292], [293, 298], [299, 304], [305, 352], [353, 358]], 200: [[200, 205], [206, 253], [254, 259], [260, 265], [266, 293], [294, 299], [300, 305], [306, 353], [354, 359]], 201: [[201, 206], [207, 254], [255, 260], [261, 266], [267, 294], [295, 300], [301, 306], [307, 354], [355, 0]], 202: [[202, 207], [208, 255], [256, 261], [262, 267], [268, 295], [296, 301], [302, 307], [308, 355], [356, 1]], 203: [[203, 208], [209, 256], [257, 262], [263, 268], [269, 296], [297, 302], [303, 308], [309, 356], [357, 2]], 204: [[204, 209], [210, 257], [258, 263], [264, 269], [270, 297], [298, 303], [304, 309], [310, 357], [358, 3]], 205: [[205, 210], [211, 258], [259, 264], [265, 270], [271, 298], [299, 304], [305, 310], [311, 358], [359, 4]], 206: [[206, 211], [212, 259], [260, 265], [266, 271], [272, 299], [300, 305], [306, 311], [312, 359], [0, 5]], 207: [[207, 212], [213, 260], [261, 266], [267, 272], [273, 300], [301, 306], [307, 312], [313, 0], [1, 6]], 208: [[208, 213], [214, 261], [262, 267], [268, 273], [274, 301], [302, 307], [308, 313], [314, 1], [2, 7]], 209: [[209, 214], [215, 262], [263, 268], [269, 274], [275, 302], [303, 308], [309, 314], [315, 2], [3, 8]], 210: [[210, 215], [216, 263], [264, 269], [270, 275], [276, 303], [304, 309], [310, 315], [316, 3], [4, 9]], 211: [[211, 216], [217, 264], [265, 270], [271, 276], [277, 304], [305, 310], [311, 316], [317, 4], [5, 10]], 212: [[212, 217], [218, 265], [266, 271], [272, 277], [278, 305], [306, 311], [312, 317], [318, 5], [6, 11]], 213: [[213, 218], [219, 266], [267, 272], [273, 278], [279, 306], [307, 312], [313, 318], [319, 6], [7, 12]], 214: [[214, 219], [220, 267], [268, 273], [274, 279], [280, 307], [308, 313], [314, 319], [320, 7], [8, 13]], 215: [[215, 220], [221, 268], [269, 274], [275, 280], [281, 308], [309, 314], [315, 320], [321, 8], [9, 14]], 216: [[216, 221], [222, 269], [270, 275], [276, 281], [282, 309], [310, 315], [316, 321], [322, 9], [10, 15]], 217: [[217, 222], [223, 270], [271, 276], [277, 282], [283, 310], [311, 316], [317, 322], [323, 10], [11, 16]], 218: [[218, 223], [224, 271], [272, 277], [278, 283], [284, 311], [312, 317], [318, 323], [324, 11], [12, 17]], 219: [[219, 224], [225, 272], [273, 278], [279, 284], [285, 312], [313, 318], [319, 324], [325, 12], [13, 18]], 220: [[220, 225], [226, 273], [274, 279], [280, 285], [286, 313], [314, 319], [320, 325], [326, 13], [14, 19]], 221: [[221, 226], [227, 274], [275, 280], [281, 286], [287, 314], [315, 320], [321, 326], [327, 14], [15, 20]], 222: [[222, 227], [228, 275], [276, 281], [282, 287], [288, 315], [316, 321], [322, 327], [328, 15], [16, 21]], 223: [[223, 228], [229, 276], [277, 282], [283, 288], [289, 316], [317, 322], [323, 328], [329, 16], [17, 22]], 224: [[224, 229], [230, 277], [278, 283], [284, 289], [290, 317], [318, 323], [324, 329], [330, 17], [18, 23]], 225: [[225, 230], [231, 278], [279, 284], [285, 290], [291, 318], [319, 324], [325, 330], [331, 18], [19, 24]], 226: [[226, 231], [232, 279], [280, 285], [286, 291], [292, 319], [320, 325], [326, 331], [332, 19], [20, 25]], 227: [[227, 232], [233, 280], [281, 286], [287, 292], [293, 320], [321, 326], [327, 332], [333, 20], [21, 26]], 228: [[228, 233], [234, 281], [282, 287], [288, 293], [294, 321], [322, 327], [328, 333], [334, 21], [22, 27]], 229: [[229, 234], [235, 282], [283, 288], [289, 294], [295, 322], [323, 328], [329, 334], [335, 22], [23, 28]], 230: [[230, 235], [236, 283], [284, 289], [290, 295], [296, 323], [324, 329], [330, 335], [336, 23], [24, 29]], 231: [[231, 236], [237, 284], [285, 290], [291, 296], [297, 324], [325, 330], [331, 336], [337, 24], [25, 30]], 232: [[232, 237], [238, 285], [286, 291], [292, 297], [298, 325], [326, 331], [332, 337], [338, 25], [26, 31]], 233: [[233, 238], [239, 286], [287, 292], [293, 298], [299, 326], [327, 332], [333, 338], [339, 26], [27, 32]], 234: [[234, 239], [240, 287], [288, 293], [294, 299], [300, 327], [328, 333], [334, 339], [340, 27], [28, 33]], 235: [[235, 240], [241, 288], [289, 294], [295, 300], [301, 328], [329, 334], [335, 340], [341, 28], [29, 34]], 236: [[236, 241], [242, 289], [290, 295], [296, 301], [302, 329], [330, 335], [336, 341], [342, 29], [30, 35]], 237: [[237, 242], [243, 290], [291, 296], [297, 302], [303, 330], [331, 336], [337, 342], [343, 30], [31, 36]], 238: [[238, 243], [244, 291], [292, 297], [298, 303], [304, 331], [332, 337], [338, 343], [344, 31], [32, 37]], 239: [[239, 244], [245, 292], [293, 298], [299, 304], [305, 332], [333, 338], [339, 344], [345, 32], [33, 38]], 240: [[240, 245], [246, 293], [294, 299], [300, 305], [306, 333], [334, 339], [340, 345], [346, 33], [34, 39]], 241: [[241, 246], [247, 294], [295, 300], [301, 306], [307, 334], [335, 340], [341, 346], [347, 34], [35, 40]], 242: [[242, 247], [248, 295], [296, 301], [302, 307], [308, 335], [336, 341], [342, 347], [348, 35], [36, 41]], 243: [[243, 248], [249, 296], [297, 302], [303, 308], [309, 336], [337, 342], [343, 348], [349, 36], [37, 42]], 244: [[244, 249], [250, 297], [298, 303], [304, 309], [310, 337], [338, 343], [344, 349], [350, 37], [38, 43]], 245: [[245, 250], [251, 298], [299, 304], [305, 310], [311, 338], [339, 344], [345, 350], [351, 38], [39, 44]], 246: [[246, 251], [252, 299], [300, 305], [306, 311], [312, 339], [340, 345], [346, 351], [352, 39], [40, 45]], 247: [[247, 252], [253, 300], [301, 306], [307, 312], [313, 340], [341, 346], [347, 352], [353, 40], [41, 46]], 248: [[248, 253], [254, 301], [302, 307], [308, 313], [314, 341], [342, 347], [348, 353], [354, 41], [42, 47]], 249: [[249, 254], [255, 302], [303, 308], [309, 314], [315, 342], [343, 348], [349, 354], [355, 42], [43, 48]], 250: [[250, 255], [256, 303], [304, 309], [310, 315], [316, 343], [344, 349], [350, 355], [356, 43], [44, 49]], 251: [[251, 256], [257, 304], [305, 310], [311, 316], [317, 344], [345, 350], [351, 356], [357, 44], [45, 50]], 252: [[252, 257], [258, 305], [306, 311], [312, 317], [318, 345], [346, 351], [352, 357], [358, 45], [46, 51]], 253: [[253, 258], [259, 306], [307, 312], [313, 318], [319, 346], [347, 352], [353, 358], [359, 46], [47, 52]], 254: [[254, 259], [260, 307], [308, 313], [314, 319], [320, 347], [348, 353], [354, 359], [0, 47], [48, 53]], 255: [[255, 260], [261, 308], [309, 314], [315, 320], [321, 348], [349, 354], [355, 0], [1, 48], [49, 54]], 256: [[256, 261], [262, 309], [310, 315], [316, 321], [322, 349], [350, 355], [356, 1], [2, 49], [50, 55]], 257: [[257, 262], [263, 310], [311, 316], [317, 322], [323, 350], [351, 356], [357, 2], [3, 50], [51, 56]], 258: [[258, 263], [264, 311], [312, 317], [318, 323], [324, 351], [352, 357], [358, 3], [4, 51], [52, 57]], 259: [[259, 264], [265, 312], [313, 318], [319, 324], [325, 352], [353, 358], [359, 4], [5, 52], [53, 58]], 260: [[260, 265], [266, 313], [314, 319], [320, 325], [326, 353], [354, 359], [0, 5], [6, 53], [54, 59]], 261: [[261, 266], [267, 314], [315, 320], [321, 326], [327, 354], [355, 0], [1, 6], [7, 54], [55, 60]], 262: [[262, 267], [268, 315], [316, 321], [322, 327], [328, 355], [356, 1], [2, 7], [8, 55], [56, 61]], 263: [[263, 268], [269, 316], [317, 322], [323, 328], [329, 356], [357, 2], [3, 8], [9, 56], [57, 62]], 264: [[264, 269], [270, 317], [318, 323], [324, 329], [330, 357], [358, 3], [4, 9], [10, 57], [58, 63]], 265: [[265, 270], [271, 318], [319, 324], [325, 330], [331, 358], [359, 4], [5, 10], [11, 58], [59, 64]], 266: [[266, 271], [272, 319], [320, 325], [326, 331], [332, 359], [0, 5], [6, 11], [12, 59], [60, 65]], 267: [[267, 272], [273, 320], [321, 326], [327, 332], [333, 0], [1, 6], [7, 12], [13, 60], [61, 66]], 268: [[268, 273], [274, 321], [322, 327], [328, 333], [334, 1], [2, 7], [8, 13], [14, 61], [62, 67]], 269: [[269, 274], [275, 322], [323, 328], [329, 334], [335, 2], [3, 8], [9, 14], [15, 62], [63, 68]], 270: [[270, 275], [276, 323], [324, 329], [330, 335], [336, 3], [4, 9], [10, 15], [16, 63], [64, 69]], 271: [[271, 276], [277, 324], [325, 330], [331, 336], [337, 4], [5, 10], [11, 16], [17, 64], [65, 70]], 272: [[272, 277], [278, 325], [326, 331], [332, 337], [338, 5], [6, 11], [12, 17], [18, 65], [66, 71]], 273: [[273, 278], [279, 326], [327, 332], [333, 338], [339, 6], [7, 12], [13, 18], [19, 66], [67, 72]], 274: [[274, 279], [280, 327], [328, 333], [334, 339], [340, 7], [8, 13], [14, 19], [20, 67], [68, 73]], 275: [[275, 280], [281, 328], [329, 334], [335, 340], [341, 8], [9, 14], [15, 20], [21, 68], [69, 74]], 276: [[276, 281], [282, 329], [330, 335], [336, 341], [342, 9], [10, 15], [16, 21], [22, 69], [70, 75]], 277: [[277, 282], [283, 330], [331, 336], [337, 342], [343, 10], [11, 16], [17, 22], [23, 70], [71, 76]], 278: [[278, 283], [284, 331], [332, 337], [338, 343], [344, 11], [12, 17], [18, 23], [24, 71], [72, 77]], 279: [[279, 284], [285, 332], [333, 338], [339, 344], [345, 12], [13, 18], [19, 24], [25, 72], [73, 78]], 280: [[280, 285], [286, 333], [334, 339], [340, 345], [346, 13], [14, 19], [20, 25], [26, 73], [74, 79]], 281: [[281, 286], [287, 334], [335, 340], [341, 346], [347, 14], [15, 20], [21, 26], [27, 74], [75, 80]], 282: [[282, 287], [288, 335], [336, 341], [342, 347], [348, 15], [16, 21], [22, 27], [28, 75], [76, 81]], 283: [[283, 288], [289, 336], [337, 342], [343, 348], [349, 16], [17, 22], [23, 28], [29, 76], [77, 82]], 284: [[284, 289], [290, 337], [338, 343], [344, 349], [350, 17], [18, 23], [24, 29], [30, 77], [78, 83]], 285: [[285, 290], [291, 338], [339, 344], [345, 350], [351, 18], [19, 24], [25, 30], [31, 78], [79, 84]], 286: [[286, 291], [292, 339], [340, 345], [346, 351], [352, 19], [20, 25], [26, 31], [32, 79], [80, 85]], 287: [[287, 292], [293, 340], [341, 346], [347, 352], [353, 20], [21, 26], [27, 32], [33, 80], [81, 86]], 288: [[288, 293], [294, 341], [342, 347], [348, 353], [354, 21], [22, 27], [28, 33], [34, 81], [82, 87]], 289: [[289, 294], [295, 342], [343, 348], [349, 354], [355, 22], [23, 28], [29, 34], [35, 82], [83, 88]], 290: [[290, 295], [296, 343], [344, 349], [350, 355], [356, 23], [24, 29], [30, 35], [36, 83], [84, 89]], 291: [[291, 296], [297, 344], [345, 350], [351, 356], [357, 24], [25, 30], [31, 36], [37, 84], [85, 90]], 292: [[292, 297], [298, 345], [346, 351], [352, 357], [358, 25], [26, 31], [32, 37], [38, 85], [86, 91]], 293: [[293, 298], [299, 346], [347, 352], [353, 358], [359, 26], [27, 32], [33, 38], [39, 86], [87, 92]], 294: [[294, 299], [300, 347], [348, 353], [354, 359], [0, 27], [28, 33], [34, 39], [40, 87], [88, 93]], 295: [[295, 300], [301, 348], [349, 354], [355, 0], [1, 28], [29, 34], [35, 40], [41, 88], [89, 94]], 296: [[296, 301], [302, 349], [350, 355], [356, 1], [2, 29], [30, 35], [36, 41], [42, 89], [90, 95]], 297: [[297, 302], [303, 350], [351, 356], [357, 2], [3, 30], [31, 36], [37, 42], [43, 90], [91, 96]], 298: [[298, 303], [304, 351], [352, 357], [358, 3], [4, 31], [32, 37], [38, 43], [44, 91], [92, 97]], 299: [[299, 304], [305, 352], [353, 358], [359, 4], [5, 32], [33, 38], [39, 44], [45, 92], [93, 98]], 300: [[300, 305], [306, 353], [354, 359], [0, 5], [6, 33], [34, 39], [40, 45], [46, 93], [94, 99]], 301: [[301, 306], [307, 354], [355, 0], [1, 6], [7, 34], [35, 40], [41, 46], [47, 94], [95, 100]], 302: [[302, 307], [308, 355], [356, 1], [2, 7], [8, 35], [36, 41], [42, 47], [48, 95], [96, 101]], 303: [[303, 308], [309, 356], [357, 2], [3, 8], [9, 36], [37, 42], [43, 48], [49, 96], [97, 102]], 304: [[304, 309], [310, 357], [358, 3], [4, 9], [10, 37], [38, 43], [44, 49], [50, 97], [98, 103]], 305: [[305, 310], [311, 358], [359, 4], [5, 10], [11, 38], [39, 44], [45, 50], [51, 98], [99, 104]], 306: [[306, 311], [312, 359], [0, 5], [6, 11], [12, 39], [40, 45], [46, 51], [52, 99], [100, 105]], 307: [[307, 312], [313, 0], [1, 6], [7, 12], [13, 40], [41, 46], [47, 52], [53, 100], [101, 106]], 308: [[308, 313], [314, 1], [2, 7], [8, 13], [14, 41], [42, 47], [48, 53], [54, 101], [102, 107]], 309: [[309, 314], [315, 2], [3, 8], [9, 14], [15, 42], [43, 48], [49, 54], [55, 102], [103, 108]], 310: [[310, 315], [316, 3], [4, 9], [10, 15], [16, 43], [44, 49], [50, 55], [56, 103], [104, 109]], 311: [[311, 316], [317, 4], [5, 10], [11, 16], [17, 44], [45, 50], [51, 56], [57, 104], [105, 110]], 312: [[312, 317], [318, 5], [6, 11], [12, 17], [18, 45], [46, 51], [52, 57], [58, 105], [106, 111]], 313: [[313, 318], [319, 6], [7, 12], [13, 18], [19, 46], [47, 52], [53, 58], [59, 106], [107, 112]], 314: [[314, 319], [320, 7], [8, 13], [14, 19], [20, 47], [48, 53], [54, 59], [60, 107], [108, 113]], 315: [[315, 320], [321, 8], [9, 14], [15, 20], [21, 48], [49, 54], [55, 60], [61, 108], [109, 114]], 316: [[316, 321], [322, 9], [10, 15], [16, 21], [22, 49], [50, 55], [56, 61], [62, 109], [110, 115]], 317: [[317, 322], [323, 10], [11, 16], [17, 22], [23, 50], [51, 56], [57, 62], [63, 110], [111, 116]], 318: [[318, 323], [324, 11], [12, 17], [18, 23], [24, 51], [52, 57], [58, 63], [64, 111], [112, 117]], 319: [[319, 324], [325, 12], [13, 18], [19, 24], [25, 52], [53, 58], [59, 64], [65, 112], [113, 118]], 320: [[320, 325], [326, 13], [14, 19], [20, 25], [26, 53], [54, 59], [60, 65], [66, 113], [114, 119]], 321: [[321, 326], [327, 14], [15, 20], [21, 26], [27, 54], [55, 60], [61, 66], [67, 114], [115, 120]], 322: [[322, 327], [328, 15], [16, 21], [22, 27], [28, 55], [56, 61], [62, 67], [68, 115], [116, 121]], 323: [[323, 328], [329, 16], [17, 22], [23, 28], [29, 56], [57, 62], [63, 68], [69, 116], [117, 122]], 324: [[324, 329], [330, 17], [18, 23], [24, 29], [30, 57], [58, 63], [64, 69], [70, 117], [118, 123]], 325: [[325, 330], [331, 18], [19, 24], [25, 30], [31, 58], [59, 64], [65, 70], [71, 118], [119, 124]], 326: [[326, 331], [332, 19], [20, 25], [26, 31], [32, 59], [60, 65], [66, 71], [72, 119], [120, 125]], 327: [[327, 332], [333, 20], [21, 26], [27, 32], [33, 60], [61, 66], [67, 72], [73, 120], [121, 126]], 328: [[328, 333], [334, 21], [22, 27], [28, 33], [34, 61], [62, 67], [68, 73], [74, 121], [122, 127]], 329: [[329, 334], [335, 22], [23, 28], [29, 34], [35, 62], [63, 68], [69, 74], [75, 122], [123, 128]], 330: [[330, 335], [336, 23], [24, 29], [30, 35], [36, 63], [64, 69], [70, 75], [76, 123], [124, 129]], 331: [[331, 336], [337, 24], [25, 30], [31, 36], [37, 64], [65, 70], [71, 76], [77, 124], [125, 130]], 332: [[332, 337], [338, 25], [26, 31], [32, 37], [38, 65], [66, 71], [72, 77], [78, 125], [126, 131]], 333: [[333, 338], [339, 26], [27, 32], [33, 38], [39, 66], [67, 72], [73, 78], [79, 126], [127, 132]], 334: [[334, 339], [340, 27], [28, 33], [34, 39], [40, 67], [68, 73], [74, 79], [80, 127], [128, 133]], 335: [[335, 340], [341, 28], [29, 34], [35, 40], [41, 68], [69, 74], [75, 80], [81, 128], [129, 134]], 336: [[336, 341], [342, 29], [30, 35], [36, 41], [42, 69], [70, 75], [76, 81], [82, 129], [130, 135]], 337: [[337, 342], [343, 30], [31, 36], [37, 42], [43, 70], [71, 76], [77, 82], [83, 130], [131, 136]], 338: [[338, 343], [344, 31], [32, 37], [38, 43], [44, 71], [72, 77], [78, 83], [84, 131], [132, 137]], 339: [[339, 344], [345, 32], [33, 38], [39, 44], [45, 72], [73, 78], [79, 84], [85, 132], [133, 138]], 340: [[340, 345], [346, 33], [34, 39], [40, 45], [46, 73], [74, 79], [80, 85], [86, 133], [134, 139]], 341: [[341, 346], [347, 34], [35, 40], [41, 46], [47, 74], [75, 80], [81, 86], [87, 134], [135, 140]], 342: [[342, 347], [348, 35], [36, 41], [42, 47], [48, 75], [76, 81], [82, 87], [88, 135], [136, 141]], 343: [[343, 348], [349, 36], [37, 42], [43, 48], [49, 76], [77, 82], [83, 88], [89, 136], [137, 142]], 344: [[344, 349], [350, 37], [38, 43], [44, 49], [50, 77], [78, 83], [84, 89], [90, 137], [138, 143]], 345: [[345, 350], [351, 38], [39, 44], [45, 50], [51, 78], [79, 84], [85, 90], [91, 138], [139, 144]], 346: [[346, 351], [352, 39], [40, 45], [46, 51], [52, 79], [80, 85], [86, 91], [92, 139], [140, 145]], 347: [[347, 352], [353, 40], [41, 46], [47, 52], [53, 80], [81, 86], [87, 92], [93, 140], [141, 146]], 348: [[348, 353], [354, 41], [42, 47], [48, 53], [54, 81], [82, 87], [88, 93], [94, 141], [142, 147]], 349: [[349, 354], [355, 42], [43, 48], [49, 54], [55, 82], [83, 88], [89, 94], [95, 142], [143, 148]], 350: [[350, 355], [356, 43], [44, 49], [50, 55], [56, 83], [84, 89], [90, 95], [96, 143], [144, 149]], 351: [[351, 356], [357, 44], [45, 50], [51, 56], [57, 84], [85, 90], [91, 96], [97, 144], [145, 150]], 352: [[352, 357], [358, 45], [46, 51], [52, 57], [58, 85], [86, 91], [92, 97], [98, 145], [146, 151]], 353: [[353, 358], [359, 46], [47, 52], [53, 58], [59, 86], [87, 92], [93, 98], [99, 146], [147, 152]], 354: [[354, 359], [0, 47], [48, 53], [54, 59], [60, 87], [88, 93], [94, 99], [100, 147], [148, 153]], 355: [[355, 0], [1, 48], [49, 54], [55, 60], [61, 88], [89, 94], [95, 100], [101, 148], [149, 154]], 356: [[356, 1], [2, 49], [50, 55], [56, 61], [62, 89], [90, 95], [96, 101], [102, 149], [150, 155]], 357: [[357, 2], [3, 50], [51, 56], [57, 62], [63, 90], [91, 96], [97, 102], [103, 150], [151, 156]], 358: [[358, 3], [4, 51], [52, 57], [58, 63], [64, 91], [92, 97], [98, 103], [104, 151], [152, 157]], 359: [[359, 4], [5, 52], [53, 58], [59, 64], [65, 92], [93, 98], [99, 104], [105, 152], [153, 158]]}


# dict1 = {0: Decimal('49396.30744020849439780000000'), 1: Decimal('49580.18236160569914860000000'), 2: Decimal('49875.07454410608069700000000'), 3: Decimal('50246.83111116522512400000000'), 4: Decimal('50681.63284795826135180000000'), 5: Decimal('51184.64315391097609020000000'), 6: Decimal('51777.27099379944888060000000'), 7: Decimal('52429.59881827522352180000000'), 8: Decimal('53126.61203640146324660000000'), 9: Decimal('53868.15525872594473140000000'), 10: Decimal('54657.16940821712850260000000'), 11: Decimal('55462.38006426388678000000000'), 12: Decimal('56283.54902914640441880000000'), 13: Decimal('57108.92532253370304560000000'), 14: Decimal('57966.08706208139236960000000'), 15: Decimal('58817.80936202978315620000000'), 16: Decimal('59645.79154843603140360000000'), 17: Decimal('60486.87796073462356140000000'), 18: Decimal('61309.49850921913596600000000'), 19: Decimal('62117.37546150445864380000000'), 20: Decimal('62919.17231655772587640000000'), 21: Decimal('63684.15195547301470320000000'), 22: Decimal('64449.63432797895731300000000'), 23: Decimal('65179.33011042071016460000000'), 24: Decimal('65869.39047376077290600000000'), 25: Decimal('66529.93517594102943160000000'), 26: Decimal('67146.51538091034922860000000'), 27: Decimal('67738.89422482762924580000000'), 28: Decimal('68304.46934683813713140000000'), 29: Decimal('68847.66575632592544440000000'), 30: Decimal('69369.86763600978480120000000'), 31: Decimal('69870.52981562945549200000000'), 32: Decimal('70341.47471310314571720000000'), 33: Decimal('70798.05327084577357200000000'), 34: Decimal('71213.66939963244089600000000'), 35: Decimal('71601.64320814181217680000000'), 36: Decimal('71957.71793404286613440000000'), 37: Decimal('72290.86916068832622520000000'), 38: Decimal('72588.57863776782177800000000'), 39: Decimal('72857.78445684077314160000000'), 40: Decimal('73096.40709483899633060000000'), 41: Decimal('73309.72131000632281540000000'), 42: Decimal('73481.82602381194406040000000'), 43: Decimal('73615.93574776199722780000000'), 44: Decimal('73731.08454834982344240000000'), 45: Decimal('73793.46984878496497660000000'), 46: Decimal('73823.42095843862478040000000'), 47: Decimal('73804.02867063969710220000000'), 48: Decimal('73736.99653248909531580000000'), 49: Decimal('73622.78439140041696440000000'), 50: Decimal('73461.99719642737626980000000'), 51: Decimal('73250.51248251635999800000000'), 52: Decimal('72974.63232770918247520000000'), 53: Decimal('72639.72545437776702600000000'), 54: Decimal('72262.78679559279610380000000'), 55: Decimal('71833.42792362632140360000000'), 56: Decimal('71334.70987479380014420000000'), 57: Decimal('70803.04087172376568700000000'), 58: Decimal('70255.59523361016958940000000'), 59: Decimal('69696.52060642387770800000000'), 60: Decimal('69115.79594602407222180000000'), 61: Decimal('68534.30591837990366640000000'), 62: Decimal('67949.05449794195687080000000'), 63: Decimal('67395.40394827246902060000000'), 64: Decimal('66837.86359893721057300000000'), 65: Decimal('66287.41338356127046120000000'), 66: Decimal('65766.67944428792058560000000'), 67: Decimal('65271.39807494492536080000000'), 68: Decimal('64823.03694656365489040000000'), 69: Decimal('64404.02793126871991140000000'), 70: Decimal('64021.36681655258603500000000'), 71: Decimal('63700.04641648727330420000000'), 72: Decimal('63413.52736228997840780000000'), 73: Decimal('63167.66365766897785120000000'), 74: Decimal('62958.25221301911440800000000'), 75: Decimal('62771.16934938638152080000000'), 76: Decimal('62635.35272869593241220000000'), 77: Decimal('62521.35596963736301120000000'), 78: Decimal('62433.86203189326118960000000'), 79: Decimal('62360.46820378772005680000000'), 80: Decimal('62296.31583671210241800000000'), 81: Decimal('62235.99884763770170920000000'), 82: Decimal('62170.33628355084025100000000'), 83: Decimal('62108.15406070499990180000000'), 84: Decimal('62033.31582806614665760000000'), 85: Decimal('61949.22273115140264280000000'), 86: Decimal('61848.01750596438891500000000'), 87: Decimal('61744.85667906532554040000000'), 88: Decimal('61626.54587207151819260000000'), 89: Decimal('61488.61711306560786080000000'), 90: Decimal('61343.63424839503273400000000'), 91: Decimal('61179.09438324229819060000000'), 92: Decimal('60985.52039897664192040000000'), 93: Decimal('60775.63428530488083100000000'), 94: Decimal('60544.62281177031140740000000'), 95: Decimal('60295.96693152234764500000000'), 96: Decimal('60014.45493561313034560000000'), 97: Decimal('59713.91433464091281680000000'), 98: Decimal('59406.34209349250467200000000'), 99: Decimal('59093.95992475354246160000000'), 100: Decimal('58794.88068349923960180000000'), 101: Decimal('58491.59466523855358960000000'), 102: Decimal('58208.55479973817013220000000'), 103: Decimal('57945.90808866499665920000000'), 104: Decimal('57701.83166183840220720000000'), 105: Decimal('57471.47810727689016920000000'), 106: Decimal('57275.34721518863043740000000'), 107: Decimal('57111.35906531585725080000000'), 108: Decimal('56985.15893678816547540000000'), 109: Decimal('56906.80725764487451740000000'), 110: Decimal('56876.21907024457169420000000'), 111: Decimal('56898.71593501498451500000000'), 112: Decimal('56949.31575367630275640000000'), 113: Decimal('57027.10647688143099120000000'), 114: Decimal('57152.19880666525847040000000'), 115: Decimal('57305.99960655795322040000000'), 116: Decimal('57481.83835199155956400000000'), 117: Decimal('57694.53558603941503460000000'), 118: Decimal('57950.02846384420017000000000'), 119: Decimal('58252.20540521862768840000000'), 120: Decimal('58567.49627892486123580000000'), 121: Decimal('58905.49258564948823300000000'), 122: Decimal('59277.79081269728387440000000'), 123: Decimal('59670.21956750713155540000000'), 124: Decimal('60071.88584102474338600000000'), 125: Decimal('60488.05597350313351320000000'), 126: Decimal('60917.95753527684558100000000'), 127: Decimal('61364.32666627772740520000000'), 128: Decimal('61828.55683837565611980000000'), 129: Decimal('62306.36065024515794420000000'), 130: Decimal('62795.87354586787803960000000'), 131: Decimal('63305.51501680843346780000000'), 132: Decimal('63825.02610362867240000000000'), 133: Decimal('64360.96508858482107860000000'), 134: Decimal('64892.89033738023022300000000'), 135: Decimal('65416.04866555641976340000000'), 136: Decimal('65943.52320916837268060000000'), 137: Decimal('66465.70041619108481960000000'), 138: Decimal('66994.40753452839243700000000'), 139: Decimal('67504.35617568679558560000000'), 140: Decimal('68010.25820866907198800000000'), 141: Decimal('68506.05304622345195020000000'), 142: Decimal('68988.92635275918961800000000'), 143: Decimal('69458.59573494529788740000000'), 144: Decimal('69912.15896082183315440000000'), 145: Decimal('70343.08164227583939400000000'), 146: Decimal('70768.52239752910917000000000'), 147: Decimal('71171.28385626550059980000000'), 148: Decimal('71575.00246824955089260000000'), 149: Decimal('71947.69700839954702420000000'), 150: Decimal('72303.32089929009497480000000'), 151: Decimal('72645.54371553846227020000000'), 152: Decimal('72975.76775035864474320000000'), 153: Decimal('73274.42317583752592540000000'), 154: Decimal('73526.58211459427100400000000'), 155: Decimal('73764.63439494537024140000000'), 156: Decimal('73955.51658924389254300000000'), 157: Decimal('74119.21178348458131560000000'), 158: Decimal('74237.26256453132386140000000'), 159: Decimal('74327.51110780105223080000000'), 160: Decimal('74384.37382140187096300000000'), 161: Decimal('74408.73119488328752640000000'), 162: Decimal('74405.23980675015269380000000'), 163: Decimal('74363.42361405563990300000000'), 164: Decimal('74295.36704158176385800000000'), 165: Decimal('74180.19648504744057280000000'), 166: Decimal('74034.60397865151395580000000'), 167: Decimal('73860.58967962426619940000000'), 168: Decimal('73647.63841441458277340000000'), 169: Decimal('73398.62315944626159640000000'), 170: Decimal('73127.94875170073514320000000'), 171: Decimal('72837.46646723861014200000000'), 172: Decimal('72503.94463855043697540000000'), 173: Decimal('72128.93048710844286700000000'), 174: Decimal('71732.48374676852408100000000'), 175: Decimal('71318.89154934290410560000000'), 176: Decimal('70901.09325998352912860000000'), 177: Decimal('70462.85785013705229900000000'), 178: Decimal('70031.45853117639266500000000'), 179: Decimal('69608.81368226317623260000000'), 180: Decimal('69188.13846895146371200000000'), 181: Decimal('68770.88292689174395700000000'), 182: Decimal('68333.94694967406420140000000'), 183: Decimal('67899.84027641391007460000000'), 184: Decimal('67452.81126851778404420000000'), 185: Decimal('67011.18608252136578220000000'), 186: Decimal('66572.23112020395229020000000'), 187: Decimal('66144.39486443056715000000000'), 188: Decimal('65726.60194621506776700000000'), 189: Decimal('65327.70291097619284700000000'), 190: Decimal('64965.42597881241094200000000'), 191: Decimal('64616.89821892664923520000000'), 192: Decimal('64308.20802177585256580000000'), 193: Decimal('64009.80996066398461820000000'), 194: Decimal('63741.00539291603573440000000'), 195: Decimal('63495.54994894967829560000000'), 196: Decimal('63277.21658612702342900000000'), 197: Decimal('63075.81684093375574720000000'), 198: Decimal('62882.93269248300211540000000'), 199: Decimal('62707.86481754467751100000000'), 200: Decimal('62562.16986521694636920000000'), 201: Decimal('62413.99946467688523560000000'), 202: Decimal('62247.40909883662663240000000'), 203: Decimal('62077.41563742532119500000000'), 204: Decimal('61903.44431479925175780000000'), 205: Decimal('61729.54350205547441880000000'), 206: Decimal('61544.83781011206146740000000'), 207: Decimal('61363.72969772704088560000000'), 208: Decimal('61194.04309379915762340000000'), 209: Decimal('61035.38410739076891940000000'), 210: Decimal('60886.74010307877518420000000'), 211: Decimal('60761.60967218012731240000000'), 212: Decimal('60638.68663523755005300000000'), 213: Decimal('60541.40309077561331720000000'), 214: Decimal('60428.98342401888116240000000'), 215: Decimal('60335.26489440812214880000000'), 216: Decimal('60240.71369564307712560000000'), 217: Decimal('60144.98422235852975140000000'), 218: Decimal('60059.43934746039772020000000'), 219: Decimal('59972.92004793777397000000000'), 220: Decimal('59895.97589006539909640000000'), 221: Decimal('59818.71189458268183860000000'), 222: Decimal('59740.27132477424449440000000'), 223: Decimal('59654.79387576767362720000000'), 224: Decimal('59565.37340607883884560000000'), 225: Decimal('59475.89591221909608740000000'), 226: Decimal('59390.22368984457682940000000'), 227: Decimal('59305.73237913496747480000000'), 228: Decimal('59225.34316647253784380000000'), 229: Decimal('59149.27460592290491720000000'), 230: Decimal('59074.40823338411464840000000'), 231: Decimal('59002.23720488080958080000000'), 232: Decimal('58920.94751504247468200000000'), 233: Decimal('58837.32560836578606360000000'), 234: Decimal('58747.13908778806378900000000'), 235: Decimal('58647.88633551453103520000000'), 236: Decimal('58554.77167501979723500000000'), 237: Decimal('58459.31250491394202100000000'), 238: Decimal('58363.95392943509765120000000'), 239: Decimal('58288.44497192680387200000000'), 240: Decimal('58220.45282137198441580000000'), 241: Decimal('58165.35597605566208900000000'), 242: Decimal('58115.78883860145306520000000'), 243: Decimal('58074.03965092555441360000000'), 244: Decimal('58054.26574107087527360000000'), 245: Decimal('58030.02334154490381720000000'), 246: Decimal('58028.06774117332562860000000'), 247: Decimal('58044.67815525657395540000000'), 248: Decimal('58082.86408911954843640000000'), 249: Decimal('58149.21215416734861420000000'), 250: Decimal('58249.78742989817271420000000'), 251: Decimal('58392.11955801412530440000000'), 252: Decimal('58571.66439431238075400000000'), 253: Decimal('58791.91506543177023220000000'), 254: Decimal('59035.60174061085397280000000'), 255: Decimal('59307.40344689649472040000000'), 256: Decimal('59618.24082879763499500000000'), 257: Decimal('59977.87439185579700280000000'), 258: Decimal('60367.24908932909824260000000'), 259: Decimal('60783.34779057859136660000000'), 260: Decimal('61220.09271112862006120000000'), 261: Decimal('61682.50017540001483960000000'), 262: Decimal('62143.49011050736021580000000'), 263: Decimal('62567.31798636644701700000000'), 264: Decimal('62969.64003538902164720000000'), 265: Decimal('63347.97358947249149200000000'), 266: Decimal('63691.48506530627856620000000'), 267: Decimal('64000.79125817872038980000000'), 268: Decimal('64275.83644962093160000000000'), 269: Decimal('64523.01671119159745080000000'), 270: Decimal('64725.53984584384559180000000'), 271: Decimal('64882.75559798263539740000000'), 272: Decimal('64996.41770516343616500000000'), 273: Decimal('65051.49819861100567500000000'), 274: Decimal('65065.14689865649460680000000'), 275: Decimal('65045.51163025886446940000000'), 276: Decimal('64972.71743474748062460000000'), 277: Decimal('64871.92068983553438040000000'), 278: Decimal('64735.53950149270583660000000'), 279: Decimal('64586.20796878811779300000000'), 280: Decimal('64428.26224468864914140000000'), 281: Decimal('64244.75680348444949500000000'), 282: Decimal('64063.14236153450787520000000'), 283: Decimal('63858.86060126813623800000000'), 284: Decimal('63633.17483678398328300000000'), 285: Decimal('63402.80082929149182360000000'), 286: Decimal('63161.89646005997287940000000'), 287: Decimal('62922.83840811712764120000000'), 288: Decimal('62709.34055628020863560000000'), 289: Decimal('62511.06787471500515580000000'), 290: Decimal('62360.81779257598846540000000'), 291: Decimal('62225.88165268765157480000000'), 292: Decimal('62127.51414496370027140000000'), 293: Decimal('62046.57462836643359100000000'), 294: Decimal('61984.27528968887922220000000'), 295: Decimal('61937.02021559627538080000000'), 296: Decimal('61919.07654282609260140000000'), 297: Decimal('61944.88828932971142820000000'), 298: Decimal('61994.94528764135380200000000'), 299: Decimal('62079.20121339341213820000000'), 300: Decimal('62184.27178977300379020000000'), 301: Decimal('62324.36244911209494140000000'), 302: Decimal('62446.29612648837493720000000'), 303: Decimal('62527.27906696124053840000000'), 304: Decimal('62583.01877288538952040000000'), 305: Decimal('62603.25805428764063380000000'), 306: Decimal('62580.90413498474146860000000'), 307: Decimal('62514.79244282000456980000000'), 308: Decimal('62407.04826096704873060000000'), 309: Decimal('62276.79127458609502380000000'), 310: Decimal('62123.47299898314948460000000'), 311: Decimal('61934.44259759818834640000000'), 312: Decimal('61717.85021659102181120000000'), 313: Decimal('61494.16093400468861200000000'), 314: Decimal('61255.66820214490405480000000'), 315: Decimal('60997.12598750776493620000000'), 316: Decimal('60736.07857691194571420000000'), 317: Decimal('60460.17543082899352180000000'), 318: Decimal('60193.38546731193404860000000'), 319: Decimal('59911.37398464355051380000000'), 320: Decimal('59643.33935467222093320000000'), 321: Decimal('59372.41393953098475720000000'), 322: Decimal('59103.65876134033648780000000'), 323: Decimal('58847.08207686593849480000000'), 324: Decimal('58589.50354071118282520000000'), 325: Decimal('58351.49026646326465940000000'), 326: Decimal('58139.55536028531931160000000'), 327: Decimal('57943.18111000219007800000000'), 328: Decimal('57761.41459810724842080000000'), 329: Decimal('57600.45261273763063240000000'), 330: Decimal('57438.50728103744359280000000'), 331: Decimal('57280.47429554335602940000000'), 332: Decimal('57110.79372937395386320000000'), 333: Decimal('56936.03651531478922420000000'), 334: Decimal('56745.34665773657575000000000'), 335: Decimal('56536.87214387348916660000000'), 336: Decimal('56316.94043045718298380000000'), 337: Decimal('56082.36472834333326700000000'), 338: Decimal('55819.28309907116977640000000'), 339: Decimal('55562.94631953840603400000000'), 340: Decimal('55277.98060359753962900000000'), 341: Decimal('54974.09743466285604720000000'), 342: Decimal('54653.24719822802260460000000'), 343: Decimal('54309.29446198455503440000000'), 344: Decimal('53953.99162072289136380000000'), 345: Decimal('53561.39028273039631360000000'), 346: Decimal('53141.25628418163044320000000'), 347: Decimal('52709.56413844391888280000000'), 348: Decimal('52273.26437197531186540000000'), 349: Decimal('51840.14419162332296680000000'), 350: Decimal('51435.30740504840735040000000'), 351: Decimal('51037.48678974401546360000000'), 352: Decimal('50654.70034346234517060000000'), 353: Decimal('50313.65058075000431080000000'), 354: Decimal('50003.03313051234354680000000'), 355: Decimal('49726.22446323712512200000000'), 356: Decimal('49493.03432457031070700000000'), 357: Decimal('49339.63621335479281860000000'), 358: Decimal('49277.54107911897974620000000'), 359: Decimal('49303.98987772024276820000000')}
# dict2 = {0: Decimal('49396.3074402084943978'), 1: Decimal('49580.1823616056991486'), 2: Decimal('49875.0745441060806970'), 3: Decimal('50246.8311111652251240'), 4: Decimal('50681.6328479582613518'), 5: Decimal('51184.6431539109760902'), 6: Decimal('51777.2709937994488806'), 7: Decimal('52429.5988182752235218'), 8: Decimal('53126.6120364014632466'), 9: Decimal('53868.1552587259447314'), 10: Decimal('54657.1694082171285026'), 11: Decimal('55462.3800642638867800'), 12: Decimal('56283.5490291464044188'), 13: Decimal('57108.9253225337030456'), 14: Decimal('57966.0870620813923696'), 15: Decimal('58817.8093620297831562'), 16: Decimal('59645.7915484360314036'), 17: Decimal('60486.8779607346235614'), 18: Decimal('61309.4985092191359660'), 19: Decimal('62117.3754615044586438'), 20: Decimal('62919.1723165577258764'), 21: Decimal('63684.1519554730147032'), 22: Decimal('64449.6343279789573130'), 23: Decimal('65179.3301104207101646'), 24: Decimal('65869.3904737607729060'), 25: Decimal('66529.9351759410294316'), 26: Decimal('67146.5153809103492286'), 27: Decimal('67738.8942248276292458'), 28: Decimal('68304.4693468381371314'), 29: Decimal('68847.6657563259254444'), 30: Decimal('69369.8676360097848012'), 31: Decimal('69870.5298156294554920'), 32: Decimal('70341.4747131031457172'), 33: Decimal('70798.0532708457735720'), 34: Decimal('71213.6693996324408960'), 35: Decimal('71601.6432081418121768'), 36: Decimal('71957.7179340428661344'), 37: Decimal('72290.8691606883262252'), 38: Decimal('72588.5786377678217780'), 39: Decimal('72857.7844568407731416'), 40: Decimal('73096.4070948389963306'), 41: Decimal('73309.7213100063228154'), 42: Decimal('73481.8260238119440604'), 43: Decimal('73615.9357477619972278'), 44: Decimal('73731.0845483498234424'), 45: Decimal('73793.4698487849649766'), 46: Decimal('73823.4209584386247804'), 47: Decimal('73804.0286706396971022'), 48: Decimal('73736.9965324890953158'), 49: Decimal('73622.7843914004169644'), 50: Decimal('73461.9971964273762698'), 51: Decimal('73250.5124825163599980'), 52: Decimal('72974.6323277091824752'), 53: Decimal('72639.7254543777670260'), 54: Decimal('72262.7867955927961038'), 55: Decimal('71833.4279236263214036'), 56: Decimal('71334.7098747938001442'), 57: Decimal('70803.0408717237656870'), 58: Decimal('70255.5952336101695894'), 59: Decimal('69696.5206064238777080'), 60: Decimal('69115.7959460240722218'), 61: Decimal('68534.3059183799036664'), 62: Decimal('67949.0544979419568708'), 63: Decimal('67395.4039482724690206'), 64: Decimal('66837.8635989372105730'), 65: Decimal('66287.4133835612704612'), 66: Decimal('65766.6794442879205856'), 67: Decimal('65271.3980749449253608'), 68: Decimal('64823.0369465636548904'), 69: Decimal('64404.0279312687199114'), 70: Decimal('64021.3668165525860350'), 71: Decimal('63700.0464164872733042'), 72: Decimal('63413.5273622899784078'), 73: Decimal('63167.6636576689778512'), 74: Decimal('62958.2522130191144080'), 75: Decimal('62771.1693493863815208'), 76: Decimal('62635.3527286959324122'), 77: Decimal('62521.3559696373630112'), 78: Decimal('62433.8620318932611896'), 79: Decimal('62360.4682037877200568'), 80: Decimal('62296.3158367121024180'), 81: Decimal('62235.9988476377017092'), 82: Decimal('62170.3362835508402510'), 83: Decimal('62108.1540607049999018'), 84: Decimal('62033.3158280661466576'), 85: Decimal('61949.2227311514026428'), 86: Decimal('61848.0175059643889150'), 87: Decimal('61744.8566790653255404'), 88: Decimal('61626.5458720715181926'), 89: Decimal('61488.6171130656078608'), 90: Decimal('61343.6342483950327340'), 91: Decimal('61179.0943832422981906'), 92: Decimal('60985.5203989766419204'), 93: Decimal('60775.6342853048808310'), 94: Decimal('60544.6228117703114074'), 95: Decimal('60295.9669315223476450'), 96: Decimal('60014.4549356131303456'), 97: Decimal('59713.9143346409128168'), 98: Decimal('59406.3420934925046720'), 99: Decimal('59093.9599247535424616'), 100: Decimal('58794.8806834992396018'), 101: Decimal('58491.5946652385535896'), 102: Decimal('58208.5547997381701322'), 103: Decimal('57945.9080886649966592'), 104: Decimal('57701.8316618384022072'), 105: Decimal('57471.4781072768901692'), 106: Decimal('57275.3472151886304374'), 107: Decimal('57111.3590653158572508'), 108: Decimal('56985.1589367881654754'), 109: Decimal('56906.8072576448745174'), 110: Decimal('56876.2190702445716942'), 111: Decimal('56898.7159350149845150'), 112: Decimal('56949.3157536763027564'), 113: Decimal('57027.1064768814309912'), 114: Decimal('57152.1988066652584704'), 115: Decimal('57305.9996065579532204'), 116: Decimal('57481.8383519915595640'), 117: Decimal('57694.5355860394150346'), 118: Decimal('57950.0284638442001700'), 119: Decimal('58252.2054052186276884'), 120: Decimal('58567.4962789248612358'), 121: Decimal('58905.4925856494882330'), 122: Decimal('59277.7908126972838744'), 123: Decimal('59670.2195675071315554'), 124: Decimal('60071.8858410247433860'), 125: Decimal('60488.0559735031335132'), 126: Decimal('60917.9575352768455810'), 127: Decimal('61364.3266662777274052'), 128: Decimal('61828.5568383756561198'), 129: Decimal('62306.3606502451579442'), 130: Decimal('62795.8735458678780396'), 131: Decimal('63305.5150168084334678'), 132: Decimal('63825.0261036286724000'), 133: Decimal('64360.9650885848210786'), 134: Decimal('64892.8903373802302230'), 135: Decimal('65416.0486655564197634'), 136: Decimal('65943.5232091683726806'), 137: Decimal('66465.7004161910848196'), 138: Decimal('66994.4075345283924370'), 139: Decimal('67504.3561756867955856'), 140: Decimal('68010.2582086690719880'), 141: Decimal('68506.0530462234519502'), 142: Decimal('68988.9263527591896180'), 143: Decimal('69458.5957349452978874'), 144: Decimal('69912.1589608218331544'), 145: Decimal('70343.0816422758393940'), 146: Decimal('70768.5223975291091700'), 147: Decimal('71171.2838562655005998'), 148: Decimal('71575.0024682495508926'), 149: Decimal('71947.6970083995470242'), 150: Decimal('72303.3208992900949748'), 151: Decimal('72645.5437155384622702'), 152: Decimal('72975.7677503586447432'), 153: Decimal('73274.4231758375259254'), 154: Decimal('73526.5821145942710040'), 155: Decimal('73764.6343949453702414'), 156: Decimal('73955.5165892438925430'), 157: Decimal('74119.2117834845813156'), 158: Decimal('74237.2625645313238614'), 159: Decimal('74327.5111078010522308'), 160: Decimal('74384.3738214018709630'), 161: Decimal('74408.7311948832875264'), 162: Decimal('74405.2398067501526938'), 163: Decimal('74363.4236140556399030'), 164: Decimal('74295.3670415817638580'), 165: Decimal('74180.1964850474405728'), 166: Decimal('74034.6039786515139558'), 167: Decimal('73860.5896796242661994'), 168: Decimal('73647.6384144145827734'), 169: Decimal('73398.6231594462615964'), 170: Decimal('73127.9487517007351432'), 171: Decimal('72837.4664672386101420'), 172: Decimal('72503.9446385504369754'), 173: Decimal('72128.9304871084428670'), 174: Decimal('71732.4837467685240810'), 175: Decimal('71318.8915493429041056'), 176: Decimal('70901.0932599835291286'), 177: Decimal('70462.8578501370522990'), 178: Decimal('70031.4585311763926650'), 179: Decimal('69608.8136822631762326'), 180: Decimal('69188.1384689514637120'), 181: Decimal('68770.8829268917439570'), 182: Decimal('68333.9469496740642014'), 183: Decimal('67899.8402764139100746'), 184: Decimal('67452.8112685177840442'), 185: Decimal('67011.1860825213657822'), 186: Decimal('66572.2311202039522902'), 187: Decimal('66144.3948644305671500'), 188: Decimal('65726.6019462150677670'), 189: Decimal('65327.7029109761928470'), 190: Decimal('64965.4259788124109420'), 191: Decimal('64616.8982189266492352'), 192: Decimal('64308.2080217758525658'), 193: Decimal('64009.8099606639846182'), 194: Decimal('63741.0053929160357344'), 195: Decimal('63495.5499489496782956'), 196: Decimal('63277.2165861270234290'), 197: Decimal('63075.8168409337557472'), 198: Decimal('62882.9326924830021154'), 199: Decimal('62707.8648175446775110'), 200: Decimal('62562.1698652169463692'), 201: Decimal('61181.7519303601955626'), 202: Decimal('61094.2008008546345722'), 203: Decimal('61010.0519618967514548'), 204: Decimal('60909.6747097742245638'), 205: Decimal('60843.3461148027988538'), 206: Decimal('61544.8378101120614674'), 207: Decimal('40038.7026829068596056'), 208: Decimal('40295.6360501580555734'), 209: Decimal('40565.8077355206069494'), 210: Decimal('40810.5013557744826842'), 211: Decimal('41092.1645518794108924'), 212: Decimal('41380.8092640530321330'), 213: Decimal('41688.2588822905621172'), 214: Decimal('41956.3972724496993224'), 215: Decimal('42247.9564146838241488'), 216: Decimal('42569.1383665510450156'), 217: Decimal('42842.0580867612927814'), 218: Decimal('43152.1373706566259502'), 219: Decimal('43397.1233444109608900'), 220: Decimal('43719.8192968233017164'), 221: Decimal('44037.5423208055658586'), 222: Decimal('44320.8952834092660144'), 223: Decimal('44593.0241165191986472'), 224: Decimal('44842.8102005505838356'), 225: Decimal('45102.7521882166705074'), 226: Decimal('45354.0057569866263794'), 227: Decimal('45536.7313350742709248'), 228: Decimal('45787.7951328947613538'), 229: Decimal('46040.3507074795224372'), 230: Decimal('46296.5944326125150984'), 231: Decimal('46538.7691619543264808'), 232: Decimal('46732.2993370852241020'), 233: Decimal('46903.2649484779550236'), 234: Decimal('47123.1922965725017890'), 235: Decimal('47312.6029347346713952'), 236: Decimal('47481.2219460249961550'), 237: Decimal('47635.1382177470714910'), 238: Decimal('47764.7772214300574912'), 239: Decimal('47915.3535747062406820'), 240: Decimal('48078.6072543262126458'), 241: Decimal('48239.1731351103819690'), 242: Decimal('48369.6531748698995152'), 243: Decimal('48522.8611667510574636'), 244: Decimal('48704.1917587747526936'), 245: Decimal('48836.3067003802253672'), 246: Decimal('48966.2648328678065786'), 247: Decimal('49079.6484237099098054'), 248: Decimal('49194.8750411194343264'), 249: Decimal('49302.7647071861628042'), 250: Decimal('49446.1872118632564642'), 251: Decimal('49590.0765938245386544'), 252: Decimal('49700.2955873796583540'), 253: Decimal('49836.4201752293899322'), 254: Decimal('59035.6017406108539728'), 255: Decimal('58110.9314216540512544'), 256: Decimal('58585.8369928939920552'), 257: Decimal('59074.3052540122070670'), 258: Decimal('59571.7362941303647216'), 259: Decimal('60065.6996243816152506'), 260: Decimal('61220.0927111286200612'), 261: Decimal('60450.2526410833251666'), 262: Decimal('60990.2818125253681556'), 263: Decimal('61499.9543108378772768'), 264: Decimal('61975.8704303639944532'), 265: Decimal('62461.7762022198159270'), 266: Decimal('63691.4850653062785662'), 267: Decimal('53308.2922279342061098'), 268: Decimal('53902.1330244546246800'), 269: Decimal('54459.4831759493617708'), 270: Decimal('54970.9867870932355418'), 271: Decimal('55418.1053089318747274'), 272: Decimal('55820.9569187792084950'), 273: Decimal('56128.1327163866563250'), 274: Decimal('56473.8208694390948568'), 275: Decimal('56730.3366142891107294'), 276: Decimal('56945.6135133368867746'), 277: Decimal('57102.4574331246636204'), 278: Decimal('57189.4309754218365466'), 279: Decimal('57223.2220590697156930'), 280: Decimal('57329.0191122874690014'), 281: Decimal('57377.0361218007178850'), 282: Decimal('57417.7217943914661052'), 283: Decimal('57457.8522833456006680'), 284: Decimal('57454.1779516174576830'), 285: Decimal('57437.9921080470311536'), 286: Decimal('57414.4796980007381394'), 287: Decimal('57323.6778866414004412'), 288: Decimal('57300.3126832041027056'), 289: Decimal('57287.4696425730657358'), 290: Decimal('57347.3694227623778154'), 291: Decimal('57396.4316720875277748'), 292: Decimal('57420.5568868228071914'), 293: Decimal('57494.4658515785686510'), 294: Decimal('61984.2752896888792222'), 295: Decimal('60740.5481903538319148'), 296: Decimal('60886.6727069224496616'), 297: Decimal('61041.3191514861214924'), 298: Decimal('61199.4324924426202810'), 299: Decimal('61361.5530471964360222'), 300: Decimal('62184.2717897730037902'), 301: Decimal('61092.1149147954052684'), 302: Decimal('61293.0878285063828770'), 303: Decimal('61459.9153914326707982'), 304: Decimal('61589.2491678603623264'), 305: Decimal('61717.0606670349650688'), 306: Decimal('62580.9041349847414686'), 307: Decimal('41189.7654279998232898'), 308: Decimal('41508.6412173259466806'), 309: Decimal('41807.2149027159330538'), 310: Decimal('42047.2342516788569846'), 311: Decimal('42264.9974772974719264'), 312: Decimal('42459.9728454065038912'), 313: Decimal('42641.0167255196374120'), 314: Decimal('42783.0820505757222148'), 315: Decimal('42909.8175077834669362'), 316: Decimal('43064.5032478199136042'), 317: Decimal('43157.2492952317565518'), 318: Decimal('43286.0834905081622786'), 319: Decimal('43335.5772811167374338'), 320: Decimal('43467.1827614301235532'), 321: Decimal('43591.2443657538687772'), 322: Decimal('43684.2827199753580078'), 323: Decimal('43785.3123176174635148'), 324: Decimal('43866.9403351829278152'), 325: Decimal('43978.3465424608390794'), 326: Decimal('44103.3374274273688616'), 327: Decimal('44174.1800659414935280'), 328: Decimal('44323.8665645294719308'), 329: Decimal('44491.5287142942481524'), 330: Decimal('44660.6934802658440428'), 331: Decimal('44817.0062526168729294'), 332: Decimal('44922.1455514167032832'), 333: Decimal('45001.9758554269581842'), 334: Decimal('45121.3998665210137500'), 335: Decimal('45201.5887430936295266'), 336: Decimal('45243.3907014623819038'), 337: Decimal('45258.1904411764627370'), 338: Decimal('45220.1063910661296164'), 339: Decimal('45189.8549223178428440'), 340: Decimal('45136.1350365517678590'), 341: Decimal('45047.9145937175759272'), 342: Decimal('44907.1115344964690546'), 343: Decimal('44758.1159778100580844'), 344: Decimal('44603.9176384267687838'), 345: Decimal('44367.6736415657178636'), 346: Decimal('44079.4533758761113932'), 347: Decimal('43744.5344068972547328'), 348: Decimal('43385.2753239751977554'), 349: Decimal('42993.6967446421371568'), 350: Decimal('42631.7071870134911004'), 351: Decimal('42235.4438255544288136'), 352: Decimal('41783.3315365296227706'), 353: Decimal('41358.1556905476240108'), 354: Decimal('50003.0331305123435468'), 355: Decimal('48529.7524379946816560'), 356: Decimal('48460.6304886666677672'), 357: Decimal('48436.0670755112028828'), 358: Decimal('48482.0282839202462252'), 359: Decimal('48586.3417115232666522')}
#
#
# import math
#
# # rel_tol=1e-9 означает, что мы допускаем расхождение в 9 знаках после запятой
# if math.isclose(dict1[0], dict2[0], rel_tol=1e-25):
#     print("Числа практически равны")



