import uuid
from datetime import datetime

from sqlalchemy import String, Integer, ForeignKey, Enum, ARRAY, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.promos import PromoModel
from app.models.enums import PaymentStatus, PaymentMethod

class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, name="payment_status"), default=PaymentStatus.pending, nullable=False)
    tariff_id: Mapped[str] = mapped_column(
        ForeignKey("tariffs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    discount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, name="payment_method"), nullable=False)
    installment_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schedule: Mapped[list[int] | None] = mapped_column(ARRAY(Integer), nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    promo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("promos.id", ondelete="SET NULL"), nullable=True
    )
    promo: Mapped["PromoModel | None"] = relationship(lazy="selectin")