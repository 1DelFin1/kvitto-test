import uuid

from sqlalchemy import String, Integer, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class PromoModel(Base, TimestampMixin):
    __tablename__ = "promos"
    __table_args__ = (
        CheckConstraint("percent BETWEEN 0 AND 100", name="ck_promos_percent"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    percent: Mapped[int] = mapped_column(Integer, nullable=False)