from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RobotBase(BaseModel):
    name: str
    description: str | None = None
    is_active: bool = True
    default_lease_minutes: int = Field(default=5, ge=1, le=240)


class RobotCreate(RobotBase):
    group_ids: list[int] = Field(default_factory=list)


class RobotUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    default_lease_minutes: int | None = Field(default=None, ge=1, le=240)
    group_ids: list[int] | None = None


class RobotOut(RobotBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    group_ids: list[int] = Field(default_factory=list)
    api_key_prefix: str = ""


class RobotOutWithKey(RobotOut):
    # The raw API key — returned only on creation and key rotation.
    api_key: str
