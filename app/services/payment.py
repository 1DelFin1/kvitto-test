from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaymentMethod, PaymentStatus
from app.models import PaymentModel, PromoModel, TariffModel
from app.exceptions import (
    InvalidTransitionError,
    TariffNotFoundError,
    PromoNotFoundError,
)


ALLOWED_TRANSITIONS: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.pending:   {PaymentStatus.succeeded, PaymentStatus.failed},
    PaymentStatus.succeeded: {PaymentStatus.refunded},
    PaymentStatus.failed:    set(),
    PaymentStatus.refunded:  set(),
}


def build_schedule(amount: int, months: int) -> list[int]:
    """Сумма платежей ровно равна amount, лишние копейки — в первые платежи."""
    base, extra = divmod(amount, months)
    return [base + 1] * extra + [base] * (months - extra)


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        tariff_id: str,
        email: str,
        method: PaymentMethod,
        installment_months: int | None,
        promo_code: str | None,
        idempotency_key: str | None,
    ) -> tuple[PaymentModel, bool]:
        if idempotency_key is not None:
            existing = await self._get_by_idempotency_key(idempotency_key)
            if existing is not None:
                return existing, False

        tariff: TariffModel | None = await self.session.get(TariffModel, tariff_id)
        if tariff is None:
            raise TariffNotFoundError(tariff_id)

        discount = 0
        promo: PromoModel | None = None
        if promo_code is not None:
            promo = await self._get_promo(promo_code)
            if promo is None:
                raise PromoNotFoundError(promo_code)
            discount = tariff.price * promo.percent // 100

        amount = tariff.price - discount

        schedule: list[int] | None = None
        months: int | None = None
        if method == PaymentMethod.installment:
            assert installment_months is not None  # гарантировано схемой
            months = installment_months
            schedule = build_schedule(amount, months)

        payment = PaymentModel(
            tariff_id=tariff.id,
            email=email,
            method=method,
            installment_months=months,
            schedule=schedule,
            amount=amount,
            discount=discount,
            promo_id=promo.id if promo else None,
            idempotency_key=idempotency_key,
        )
        self.session.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)
        return payment, True

    async def get(self, payment_id: UUID) -> PaymentModel | None:
        return await self.session.get(PaymentModel, payment_id)

    async def change_status(
        self,
        payment_id: UUID,
        new_status: PaymentStatus,
    ) -> PaymentModel | None:
        stmt = (
            select(PaymentModel)
            .where(PaymentModel.id == payment_id)
            .with_for_update()
        )
        payment = await self.session.scalar(stmt)
        if payment is None:
            return None

        if new_status not in ALLOWED_TRANSITIONS[payment.status]:
            raise InvalidTransitionError(payment.status, new_status)

        payment.status = new_status
        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def _get_by_idempotency_key(self, key: str) -> PaymentModel | None:
        stmt = select(PaymentModel).where(PaymentModel.idempotency_key == key)
        return await self.session.scalar(stmt)

    async def _get_promo(self, code: str) -> PromoModel | None:
        stmt = select(PromoModel).where(PromoModel.code == code.upper())
        return await self.session.scalar(stmt)