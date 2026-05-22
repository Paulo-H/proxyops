from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.proxy import ProxyProtocol


class ProxyBase(BaseModel):
    host: str
    port: int = Field(ge=1, le=65535)
    protocol: ProxyProtocol = ProxyProtocol.http
    username: str | None = None
    is_active: bool = True
    expires_at: datetime | None = None
    extra_metadata: dict[str, Any] | None = None
    provider_id: int | None = None


class ProxyCreate(ProxyBase):
    password: str | None = None
    group_ids: list[int] = Field(default_factory=list)


class ProxyUpdate(BaseModel):
    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    protocol: ProxyProtocol | None = None
    username: str | None = None
    password: str | None = None
    is_active: bool | None = None
    expires_at: datetime | None = None
    extra_metadata: dict[str, Any] | None = None
    provider_id: int | None = None
    group_ids: list[int] | None = None


class ProxyOut(ProxyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    success_count: int
    failure_count: int
    avg_response_time_ms: float
    is_in_use: bool
    last_used: datetime | None
    created_at: datetime
    group_ids: list[int] = Field(default_factory=list)
    provider_name: str | None = None
    success_rate: float = 0.0


class ProxyOutWithSecret(ProxyOut):
    password: str | None = None


class ProxyBulkRow(BaseModel):
    host: str
    port: int
    protocol: ProxyProtocol = ProxyProtocol.http
    username: str | None = None
    password: str | None = None
    expires_at: datetime | None = None


class ProxyBulkCreate(BaseModel):
    provider_id: int | None = None
    group_ids: list[int] = Field(default_factory=list)
    proxies: list[ProxyBulkRow]
