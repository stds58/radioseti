from fastapi import APIRouter, Depends, status
from azimuth_aggregation.app.azimuth_service import AzimuthService
from azimuth_aggregation.app.repository import InMemoryAzimuthRepository
from azimuth_aggregation.app.entity import Coordinates
from azimuth_aggregation.app.repository import AzimuthRepository

router = APIRouter()

def get_repository():
    return InMemoryAzimuthRepository()


def get_azimuth_service(
    coordinates: Coordinates,
    repository: AzimuthRepository = Depends(get_repository)
) -> AzimuthService:
    return AzimuthService(repository=repository, coordinates=coordinates)


@router.post(
    "/azimuth",
    name="get_azimuths",
)
async def get_azimuths(
    azimuth_service: AzimuthService = Depends(get_azimuth_service),
) -> list[dict]:
    await azimuth_service.create_dataset()
    data = await azimuth_service.get_azimuth()

    return data


@router.post(
    "/create_mock_dataset",
    name="create_mock_dataset",
    status_code=status.HTTP_201_CREATED,
)
async def create_mock_dataset(
    azimuth_service: AzimuthService = Depends(get_azimuth_service),
):
    await azimuth_service.create_dataset()
