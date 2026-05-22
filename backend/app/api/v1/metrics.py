from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, literal
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.models import Proxy, ProxyGroup, RequestLog, Robot, StrategyConfig
from app.schemas import MetricsSummary, StatusCodeBucket, TimeseriesPoint, TopItem

router = APIRouter()


def _apply_filters(q, **filters):
    if filters.get("robot_id") is not None:
        q = q.filter(RequestLog.robot_id == filters["robot_id"])
    if filters.get("group_id") is not None:
        q = q.filter(RequestLog.group_id == filters["group_id"])
    if filters.get("proxy_id") is not None:
        q = q.filter(RequestLog.proxy_id == filters["proxy_id"])
    if filters.get("target_host"):
        q = q.filter(RequestLog.target_host == filters["target_host"])
    if filters.get("strategy_id") is not None:
        q = q.filter(RequestLog.strategy_id == filters["strategy_id"])
    if filters.get("strategy_kind"):
        q = q.filter(RequestLog.strategy_kind == filters["strategy_kind"])
    if filters.get("since") is not None:
        q = q.filter(RequestLog.created_at >= filters["since"])
    if filters.get("until") is not None:
        q = q.filter(RequestLog.created_at <= filters["until"])
    return q


def _common_filters(
    robot_id: int | None = None,
    group_id: int | None = None,
    proxy_id: int | None = None,
    target_host: str | None = None,
    strategy_id: int | None = None,
    strategy_kind: str | None = None,
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
) -> dict:
    if since is None:
        since = datetime.utcnow() - timedelta(days=1)
    return dict(
        robot_id=robot_id,
        group_id=group_id,
        proxy_id=proxy_id,
        target_host=target_host,
        strategy_id=strategy_id,
        strategy_kind=strategy_kind,
        since=since,
        until=until,
    )


@router.get("/summary", response_model=MetricsSummary)
def summary(
    _: CurrentUser,
    db: Session = Depends(get_db),
    filters: dict = Depends(_common_filters),
) -> MetricsSummary:
    q = _apply_filters(db.query(RequestLog), **filters)
    total, success, avg_ms = (
        q.with_entities(
            func.count(RequestLog.id),
            func.sum(case((RequestLog.success.is_(True), 1), else_=0)),
            func.avg(RequestLog.duration_ms),
        ).one()
    )
    total = total or 0
    success = success or 0
    avg_ms = float(avg_ms or 0.0)
    active_proxies = db.query(func.count(Proxy.id)).filter(Proxy.is_active.is_(True)).scalar() or 0
    active_robots = db.query(func.count(Robot.id)).filter(Robot.is_active.is_(True)).scalar() or 0
    return MetricsSummary(
        total_requests=total,
        successful_requests=success,
        failed_requests=total - success,
        success_rate=(success / total) if total else 0.0,
        average_duration_ms=avg_ms,
        active_proxies=active_proxies,
        active_robots=active_robots,
    )


@router.get("/timeseries", response_model=list[TimeseriesPoint])
def timeseries(
    _: CurrentUser,
    db: Session = Depends(get_db),
    interval: str = Query(default="hour", pattern="^(minute|hour|day)$"),
    filters: dict = Depends(_common_filters),
) -> list[TimeseriesPoint]:
    trunc = func.date_trunc(literal(interval), RequestLog.created_at).label("bucket")
    q = _apply_filters(
        db.query(
            trunc,
            func.count(RequestLog.id).label("total"),
            func.sum(case((RequestLog.success.is_(True), 1), else_=0)).label("success"),
        ),
        **filters,
    )
    rows = q.group_by("bucket").order_by("bucket").all()
    points: list[TimeseriesPoint] = []
    for bucket, total, success in rows:
        total = total or 0
        success = success or 0
        points.append(
            TimeseriesPoint(
                bucket=bucket,
                total=total,
                success=success,
                failure=total - success,
                success_rate=(success / total) if total else 0.0,
            )
        )
    return points


@router.get("/status-codes", response_model=list[StatusCodeBucket])
def status_codes(
    _: CurrentUser,
    db: Session = Depends(get_db),
    filters: dict = Depends(_common_filters),
) -> list[StatusCodeBucket]:
    q = _apply_filters(db.query(RequestLog.status_code, func.count(RequestLog.id)), **filters)
    rows = q.group_by(RequestLog.status_code).order_by(RequestLog.status_code).all()
    return [StatusCodeBucket(status_code=sc, count=c) for sc, c in rows]


def _top(
    db: Session,
    group_column,
    label_join,
    filters: dict,
    limit: int,
    *,
    extra_join=None,
    keep_null: bool = False,
) -> list[TopItem]:
    base = db.query(
        group_column.label("key"),
        func.count(RequestLog.id).label("total"),
        func.sum(case((RequestLog.success.is_(True), 1), else_=0)).label("success"),
        func.avg(RequestLog.duration_ms).label("avg_ms"),
    )
    if extra_join is not None:
        base = base.join(*extra_join)
    q = _apply_filters(base, **filters)
    rows = q.group_by(group_column).order_by(func.count(RequestLog.id).desc()).limit(limit).all()
    items: list[TopItem] = []
    for key, total, success, avg_ms in rows:
        if key is None and not keep_null:
            continue
        total = total or 0
        success = success or 0
        label = label_join(key) if label_join else None
        items.append(
            TopItem(
                key=str(key) if key is not None else "—",
                label=label,
                total=total,
                success=success,
                failure=total - success,
                success_rate=(success / total) if total else 0.0,
                avg_duration_ms=float(avg_ms or 0.0),
            )
        )
    return items


@router.get("/top/robots", response_model=list[TopItem])
def top_robots(
    _: CurrentUser,
    db: Session = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=100),
    filters: dict = Depends(_common_filters),
) -> list[TopItem]:
    return _top(db, RequestLog.robot_name, None, filters, limit)


@router.get("/top/proxies", response_model=list[TopItem])
def top_proxies(
    _: CurrentUser,
    db: Session = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=100),
    filters: dict = Depends(_common_filters),
) -> list[TopItem]:
    items = _top(db, RequestLog.proxy_id, None, filters, limit)
    ids = [int(i.key) for i in items]
    if ids:
        labels = dict(db.query(Proxy.id, Proxy.host).filter(Proxy.id.in_(ids)).all())
        for item in items:
            item.label = labels.get(int(item.key))
    return items


@router.get("/top/hosts", response_model=list[TopItem])
def top_hosts(
    _: CurrentUser,
    db: Session = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=100),
    filters: dict = Depends(_common_filters),
) -> list[TopItem]:
    return _top(db, RequestLog.target_host, None, filters, limit)


@router.get(
    "/breakdown",
    response_model=list[TopItem],
    summary="Compare a metric across a dimension",
    description=(
        "Groups request logs by `dimension` and returns total / success / "
        "success-rate / average latency per group. Use it to compare strategies, "
        "robots, providers, groups or target hosts side by side. All the usual "
        "filters apply (so you can, e.g., compare strategies *within one group*)."
    ),
)
def breakdown(
    _: CurrentUser,
    db: Session = Depends(get_db),
    dimension: str = Query(pattern="^(strategy|robot|provider|group|host|proxy)$"),
    limit: int = Query(default=20, ge=1, le=200),
    filters: dict = Depends(_common_filters),
) -> list[TopItem]:
    if dimension == "strategy":
        # Group by the algorithm kind; null/empty means the fallback round-robin.
        items = _top(db, RequestLog.strategy_kind, None, filters, limit, keep_null=True)
        for item in items:
            if item.key == "—":
                item.label = "round_robin (fallback)"
            else:
                item.label = item.key
        return items

    if dimension == "robot":
        return _top(db, RequestLog.robot_name, None, filters, limit)

    if dimension == "host":
        return _top(db, RequestLog.target_host, None, filters, limit)

    if dimension == "proxy":
        items = _top(db, RequestLog.proxy_id, None, filters, limit)
        ids = [int(i.key) for i in items if i.key != "—"]
        if ids:
            labels = dict(db.query(Proxy.id, Proxy.host).filter(Proxy.id.in_(ids)).all())
            for item in items:
                if item.key != "—":
                    item.label = labels.get(int(item.key))
        return items

    if dimension == "group":
        items = _top(db, RequestLog.group_id, None, filters, limit, keep_null=True)
        ids = [int(i.key) for i in items if i.key != "—"]
        labels = dict(db.query(ProxyGroup.id, ProxyGroup.name).filter(ProxyGroup.id.in_(ids)).all()) if ids else {}
        for item in items:
            item.label = labels.get(int(item.key)) if item.key != "—" else "(no group)"
        return items

    if dimension == "provider":
        # Join through the proxy to reach its provider.
        items = _top(
            db,
            Proxy.provider_id,
            None,
            filters,
            limit,
            extra_join=(Proxy, Proxy.id == RequestLog.proxy_id),
            keep_null=True,
        )
        from app.models import Provider

        ids = [int(i.key) for i in items if i.key != "—"]
        labels = dict(db.query(Provider.id, Provider.name).filter(Provider.id.in_(ids)).all()) if ids else {}
        for item in items:
            item.label = labels.get(int(item.key)) if item.key != "—" else "(no provider)"
        return items

    return []
