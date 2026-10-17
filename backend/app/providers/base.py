from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from backend.app.schemas.schemas import EvidenceItemSchema


class WeatherProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        pass

    @abstractmethod
    async def get_observations(
        self,
        latitude: float,
        longitude: float,
        target_time: Optional[datetime] = None,
        district_id: Optional[str] = None
    ) -> List[EvidenceItemSchema]:
        pass

    @abstractmethod
    async def get_warnings(
        self,
        latitude: float,
        longitude: float,
        district_id: Optional[str] = None
    ) -> List[EvidenceItemSchema]:
        pass
