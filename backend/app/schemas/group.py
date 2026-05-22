from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProxyGroupBase(BaseModel):
    name: str
    description: str | None = None
    default_strategy_id: int | None = None


class ProxyGroupCreate(ProxyGroupBase):
    proxy_ids: list[int] = Field(default_factory=list)


class ProxyGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    default_strategy_id: int | None = None
    proxy_ids: list[int] | None = None


class ProxyGroupOut(ProxyGroupBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    proxy_count: int = 0
    robot_count: int = 0
