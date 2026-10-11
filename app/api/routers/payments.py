from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.deps import PaymentServiceDep
from app.schemas import PaymentCreateSchema, PaymentOutSchema
from app.exceptions import TariffNotFoundError, PromoNotFoundError


payment_router = APIRouter(prefix="/payments", tags=["payments"])


@payment_router.post(
    "",
    response_model=PaymentOutSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_payment(
    data: PaymentCreateSchema,
    service: PaymentServiceDep,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    try:
        payment, created = await service.create(
            tariff_id=data.tariff_id,
            email=data.email,
            method=data.method,
            installment_months=data.installment_months,
            promo_code=data.promo_code,
            idempotency_key=idempotency_key,
        )
    except TariffNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"unknown tariff_id: {e.tariff_id}"
        )
    except PromoNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"unknown promo_code: {e.code}"
        )

    if not created:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=PaymentOutSchema.model_validate(payment).model_dump(mode="json"),
        )

    return payment


@payment_router.get("/{payment_id}", response_model=PaymentOutSchema)
async def get_payment(payment_id: UUID, service: PaymentServiceDep):
    payment = await service.get(payment_id)
    if payment is None:
        raise HTTPException(404, "payment not found")

    return payment
