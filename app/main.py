from contextlib import asynccontextmanager

import uvicorn
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import select

from app.api.routers import main_router
from app.core.config import settings
from app.core.database import async_session_factory
from app.models import TariffModel, PromoModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)

    async with async_session_factory() as session:
        for t in [
            {"id": "basic", "title": "Basic", "price": 990_000},
            {"id": "standard", "title": "Standard", "price": 1_990_000},
            {"id": "premium", "title": "Premium", "price": 2_990_000},
        ]:
            existing = await session.get(TariffModel, t["id"])
            if existing is None:
                session.add(TariffModel(**t))

        existing = await session.scalar(
            select(PromoModel).where(PromoModel.code == "KVITTO10")
        )
        if existing is None:
            session.add(PromoModel(code="KVITTO10", percent=10))

        await session.commit()
    yield

app = FastAPI(title="KvittoTest", lifespan=lifespan)
app.include_router(main_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.cors.CORS_METHODS,
    allow_headers=settings.cors.CORS_HEADERS,
)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", reload=True)
