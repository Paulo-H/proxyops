from pydantic import BaseModel, Field

from app.models.proxy import ProxyProtocol


class AcquireRequest(BaseModel):
    target_url: str = Field(min_length=1)
    group_id: int | None = None
    strategy_id: int | None = Field(
        default=None,
        description="Override the group's default strategy by id of a StrategyConfig.",
    )
    lease_minutes: int | None = Field(default=None, ge=1, le=240)


class ProxyCredentials(BaseModel):
    id: int
    host: str
    port: int
    protocol: ProxyProtocol
    username: str | None = None
    password: str | None = None


class AcquireResponse(BaseModel):
    lease_id: int
    proxy: ProxyCredentials
    strategy: str
    group_id: int | None = None


class ReleaseRequest(BaseModel):
    lease_id: int
    success: bool
    status_code: int | None = Field(default=None, ge=100, le=599)
    duration_ms: float | None = Field(default=None, ge=0)
    error_message: str | None = None


class ReleaseResponse(BaseModel):
    ok: bool = True
    log_id: int
