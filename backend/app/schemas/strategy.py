from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.strategy import StrategyKind


class StrategyConfigBase(BaseModel):
    name: str
    description: str | None = None
    kind: StrategyKind
    parameters: dict[str, Any] = {}


class StrategyConfigCreate(StrategyConfigBase):
    pass


class StrategyConfigUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    parameters: dict[str, Any] | None = None


class StrategyConfigOut(StrategyConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class StrategyParameterSpec(BaseModel):
    name: str
    type: str
    default: Any
    min: float | None = None
    max: float | None = None
    description: str


class StrategyKindInfo(BaseModel):
    kind: StrategyKind
    label: str
    description: str
    parameters: list[StrategyParameterSpec]
