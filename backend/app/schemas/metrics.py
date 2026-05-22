from datetime import datetime

from pydantic import BaseModel


class TimeseriesPoint(BaseModel):
    bucket: datetime
    total: int
    success: int
    failure: int
    success_rate: float


class StatusCodeBucket(BaseModel):
    status_code: int | None
    count: int


class TopItem(BaseModel):
    key: str
    label: str | None = None
    total: int
    success: int
    failure: int
    success_rate: float
    avg_duration_ms: float = 0.0


class MetricsSummary(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    average_duration_ms: float
    active_proxies: int
    active_robots: int
