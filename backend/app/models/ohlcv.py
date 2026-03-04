from __future__ import annotations

import uuid

from sqlalchemy import DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OhlcvBar(Base):
    __tablename__ = "ohlcv_bars"
    __table_args__ = (
        UniqueConstraint("ticker", "asset_class", "resolution", "ts"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(16), nullable=False)
    resolution: Mapped[str] = mapped_column(String(8), nullable=False)
    ts: Mapped[str] = mapped_column(DateTime(timezone=False), nullable=False)
    open: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(24, 6), nullable=False)
