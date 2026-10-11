from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TariffModel


class TariffService:
    @classmethod
    async def get(cls, session: AsyncSession) -> list[TariffModel]:
        stmt = select(TariffModel)
        tariffs = await session.scalars(stmt)
        return list(tariffs)
