from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IndicatorCreate(BaseModel):
    indicator_type: str
    alias: str
    params: dict[str, Any] = Field(default_factory=dict)
    display_order: int = 0


class ConditionCreate(BaseModel):
    left_operand_type: str
    left_operand_value: str
    operator: str
    right_operand_type: str
    right_operand_value: str
    display_order: int = 0


class ConditionGroupCreate(BaseModel):
    group_name: str | None = None  # Optional name for expression-based groups
    logic: str
    conditions: list[ConditionCreate]


class StrategyCreate(BaseModel):
    name: str
    description: str | None = None
    indicators: list[IndicatorCreate] = Field(default_factory=list)

    # Legacy: single entry/exit groups (backward compatible)
    entry: ConditionGroupCreate | None = None
    exit: ConditionGroupCreate | None = None

    # New: named groups with expressions
    entry_groups: dict[str, ConditionGroupCreate] | None = None
    exit_groups: dict[str, ConditionGroupCreate] | None = None
    entry_expression: str | None = None
    exit_expression: str | None = None


class StrategyUpdate(StrategyCreate):
    pass


class IndicatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    alias: str
    indicator_type: str
    params: dict[str, Any]
    display_order: int


class ConditionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    left_operand_type: str
    left_operand_value: str
    operator: str
    right_operand_type: str
    right_operand_value: str
    display_order: int


class ConditionGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_type: str
    group_name: str | None  # NEW: group name for expressions
    logic: str
    conditions: list[ConditionOut]


class StrategyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    entry_expression: str | None  # NEW
    exit_expression: str | None   # NEW
    indicators: list[IndicatorOut]
    condition_groups: list[ConditionGroupOut]
