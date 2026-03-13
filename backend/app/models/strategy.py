from __future__ import annotations

import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    strategies = relationship("Strategy", back_populates="user")


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Boolean expression support
    entry_expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    exit_expression: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="strategies")
    indicators = relationship("Indicator", back_populates="strategy", cascade="all, delete-orphan")
    condition_groups = relationship(
        "ConditionGroup", back_populates="strategy", cascade="all, delete-orphan"
    )
    backtest_runs = relationship(
        "BacktestRun",
        back_populates="strategy",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Indicator(Base):
    __tablename__ = "indicators"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("strategies.id"), nullable=False)
    alias: Mapped[str] = mapped_column(String(64), nullable=False)
    indicator_type: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    strategy = relationship("Strategy", back_populates="indicators")


class ConditionGroup(Base):
    __tablename__ = "condition_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("strategies.id"), nullable=False)
    group_type: Mapped[str] = mapped_column(String(16), nullable=False)  # 'ENTRY' or 'EXIT'
    group_name: Mapped[str | None] = mapped_column(String(64), nullable=True)  # e.g., 'oversold', 'trending'
    logic: Mapped[str] = mapped_column(String(8), nullable=False)  # 'AND' or 'OR'

    strategy = relationship("Strategy", back_populates="condition_groups")
    conditions = relationship("Condition", back_populates="group", cascade="all, delete-orphan")


class Condition(Base):
    __tablename__ = "conditions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("condition_groups.id"), nullable=False)
    left_operand_type: Mapped[str] = mapped_column(String(16), nullable=False)
    left_operand_value: Mapped[str] = mapped_column(String(128), nullable=False)
    operator: Mapped[str] = mapped_column(String(32), nullable=False)
    right_operand_type: Mapped[str] = mapped_column(String(16), nullable=False)
    right_operand_value: Mapped[str] = mapped_column(String(128), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    group = relationship("ConditionGroup", back_populates="conditions")
