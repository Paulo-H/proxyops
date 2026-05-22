from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RequestLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    proxy_id: int
    group_id: int | None
    robot_id: int | None
    robot_name: str
    target_url: str
    target_host: str | None
    strategy_id: int | None
    strategy_kind: str | None
    status_code: int | None
    success: bool
    duration_ms: float | None
    error_message: str | None
    created_at: datetime
