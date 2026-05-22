from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DomainBase(BaseModel):
    hostname: str
    notes: str | None = None
    is_blocked: bool = False
    rate_limit_per_minute: int | None = Field(default=None, ge=1)


class DomainCreate(DomainBase):
    pass


class DomainUpdate(BaseModel):
    notes: str | None = None
    is_blocked: bool | None = None
    rate_limit_per_minute: int | None = Field(default=None, ge=1)


class DomainOut(DomainBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
