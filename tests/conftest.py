import os

os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "kvitto_test"
os.environ["POSTGRES_USER"] = "delfin"
os.environ["POSTGRES_PASSWORD"] = "1234"

import asyncpg
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_session
from app.main import app as fastapi_app
from app.models import PromoModel, TariffModel

ADMIN_DATABASE = "db"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _ensure_test_database() -> None:
    admin = await asyncpg.connect(
        host=settings.pg_database.POSTGRES_HOST,
        port=settings.pg_database.POSTGRES_PORT,
        user=settings.pg_database.POSTGRES_USER,
        password=settings.pg_database.POSTGRES_PASSWORD,
        database=ADMIN_DATABASE,
    )
    try:
        exists = await admin.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            settings.pg_database.POSTGRES_DB,
        )
        if not exists:
            await admin.execute(f'CREATE DATABASE "{settings.pg_database.POSTGRES_DB}"')
    finally:
        await admin.close()


@pytest_asyncio.fixture(scope="session")
async def engine(_ensure_test_database):
    engine = create_async_engine(str(settings.pg_database.POSTGRES_URL_ASYNC))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        await session.execute(
            text("TRUNCATE payments, promos, tariffs RESTART IDENTITY CASCADE")
        )
        session.add_all(
            [
                TariffModel(id="basic", title="Basic", price=990_000),
                TariffModel(id="standard", title="Standard", price=1_990_000),
                TariffModel(id="premium", title="Premium", price=2_990_000),
                PromoModel(code="KVITTO10", percent=10),
            ]
        )
        await session.commit()
        yield session


@pytest_asyncio.fixture
async def client(session):
    async def _override_get_session():
        yield session

    fastapi_app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()
