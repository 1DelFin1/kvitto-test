from fastapi import APIRouter
from app.api.routers.payments import payment_router
from app.api.routers.tariffs import tariff_router
from app.api.routers.webhooks import webhook_router
main_router = APIRouter()
main_router.include_router(payment_router)
main_router.include_router(tariff_router)
main_router.include_router(webhook_router)

__all__ = [
    "main_router",
]
