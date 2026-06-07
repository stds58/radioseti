from dataclasses import dataclass
from typing import List, Optional, Dict, Protocol


# ==============================================================================
# 1. МОДЕЛИ ДАННЫХ (DTO)
# Используем dataclass для строгой типизации и иммутабельности (SRP)
# ==============================================================================
@dataclass(frozen=True)
class ParetoPoint:
    azimuth: int
    imbalance: float
    degradation: float
    traffic: float
    cluster_id: str  # Идентификатор источника (важно для мульти-кластерного анализа)


# ==============================================================================
# 2. ИНТЕРФЕЙСЫ (Protocols) - DIP и ISP
# ==============================================================================
class ParetoFilterStrategy(Protocol):
    """Стратегия фильтрации недоминируемых решений."""

    def filter(self, points: List[ParetoPoint]) -> List[ParetoPoint]:
        ...


class ParetoFrontProvider(Protocol):
    """Интерфейс для любого источника, который может выдать Парето-фронт."""

    @property
    def cluster_id(self) -> str: ...

    def get_front(self) -> List[ParetoPoint]: ...
