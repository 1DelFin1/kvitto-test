from fastapi import APIRouter

from app.api.deps import SessionDep
from app.schemas import TariffOutSchema
from app.services.tariff import TariffService

tariff_router = APIRouter(prefix="/tariffs", tags=["tariffs"])


@tariff_router.get("", response_model=list[TariffOutSchema])
async def list_tariffs(session: SessionDep):
    return await TariffService.get(session)