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
    logic: str
    conditions: list[ConditionCreate]


class StrategyCreate(BaseModel):
    name: str
    description: str | None = None
    indicators: list[IndicatorCreate] = Field(default_factory=list)
    entry: ConditionGroupCreate
    exit: ConditionGroupCreate


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
    logic: str
    conditions: list[ConditionOut]


class StrategyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    indicators: list[IndicatorOut]
    condition_groups: list[ConditionGroupOut]
