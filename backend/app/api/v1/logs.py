from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.models import RequestLog
from app.schemas import RequestLogOut

router = APIRouter()


@router.get("", response_model=list[RequestLogOut])
def list_logs(
    _: CurrentUser,
    db: Session = Depends(get_db),
    robot_id: int | None = None,
    group_id: int | None = None,
    proxy_id: int | None = None,
    target_host: str | None = None,
    strategy_id: int | None = None,
    strategy_kind: str | None = None,
    success: bool | None = None,
    status_code_min: int | None = Query(default=None, ge=100, le=599),
    status_code_max: int | None = Query(default=None, ge=100, le=599),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
) -> list[RequestLog]:
    q = db.query(RequestLog)
    if robot_id is not None:
        q = q.filter(RequestLog.robot_id == robot_id)
    if group_id is not None:
        q = q.filter(RequestLog.group_id == group_id)
    if proxy_id is not None:
        q = q.filter(RequestLog.proxy_id == proxy_id)
    if target_host:
        q = q.filter(RequestLog.target_host == target_host)
    if strategy_id is not None:
        q = q.filter(RequestLog.strategy_id == strategy_id)
    if strategy_kind:
        q = q.filter(RequestLog.strategy_kind == strategy_kind)
    if success is not None:
        q = q.filter(RequestLog.success.is_(success))
    if status_code_min is not None:
        q = q.filter(RequestLog.status_code >= status_code_min)
    if status_code_max is not None:
        q = q.filter(RequestLog.status_code <= status_code_max)
    if since is not None:
        q = q.filter(RequestLog.created_at >= since)
    if until is not None:
        q = q.filter(RequestLog.created_at <= until)
    return q.order_by(RequestLog.created_at.desc()).offset(offset).limit(limit).all()
