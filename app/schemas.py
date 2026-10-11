from datetime import datetime
import uuid

from pydantic import BaseModel, EmailStr, model_validator, ConfigDict

from app.models.enums import PaymentMethod, PaymentStatus

class PaymentCreateSchema(BaseModel):
    tariff_id: str
    email: EmailStr
    method: PaymentMethod
    installment_months: int | None = None
    promo_code: str | None = None

    @model_validator(mode="after")
    def _validate_installment(self) -> "PaymentCreateSchema":
        if self.method is PaymentMethod.installment:
            if self.installment_months not in (3, 6, 12):
                raise ValueError("installment_months must be 3, 6 or 12")
        else:
            self.installment_months = None
        return self


class PaymentOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: PaymentStatus
    tariff_id: str
    amount: int
    discount: int
    method: PaymentMethod
    installment_months: int | None
    schedule: list[int] | None
    email: str
    created_at: datetime


class TariffOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    price: int


class WebhookBody(BaseModel):
    payment_id: uuid.UUID
    status: PaymentStatus
