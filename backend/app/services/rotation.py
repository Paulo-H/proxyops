"""Rotation orchestration: pick a proxy, lock it, record a lease, finalize on release."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Proxy, ProxyGroup, ProxyLease, RequestLog, Robot, StrategyConfig
from app.models.strategy import StrategyKind
from app.services.strategies import build_strategy
from app.services.strategies.base import ProxySelectionStrategy


def extract_host(target_url: str) -> str:
    parsed = urlparse(target_url if "://" in target_url else f"http://{target_url}")
    return (parsed.hostname or target_url).lower()


def resolve_strategy(
    db: Session,
    robot: Robot,
    group: Optional[ProxyGroup],
    strategy_id: Optional[int],
) -> tuple[ProxySelectionStrategy, str, Optional[int]]:
    """Pick the strategy: explicit > group default > fallback to round_robin.

    Returns (strategy_instance, kind_label, strategy_config_id).
    """
    config: StrategyConfig | None = None
    if strategy_id is not None:
        config = db.get(StrategyConfig, strategy_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"strategy_id {strategy_id} not found",
            )
    elif group and group.default_strategy_id is not None:
        config = db.get(StrategyConfig, group.default_strategy_id)

    if config is None:
        return build_strategy(StrategyKind.round_robin), StrategyKind.round_robin.value, None

    return build_strategy(config.kind, config.parameters), config.kind.value, config.id


def resolve_group(
    db: Session,
    robot: Robot,
    requested_group_id: Optional[int],
) -> Optional[ProxyGroup]:
    """Validate that the robot may consume from the requested group.

    If the robot has bound groups, only those are allowed. If none are bound, the robot
    can consume any group (no scoping).
    """
    if not robot.groups:
        if requested_group_id is None:
            return None
        group = db.get(ProxyGroup, requested_group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        return group

    allowed_ids = {g.id for g in robot.groups}

    if requested_group_id is None:
        if len(allowed_ids) == 1:
            return robot.groups[0]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This robot is bound to multiple groups; pass `group_id` explicitly."
            ),
        )

    if requested_group_id not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Robot is not bound to the requested group.",
        )
    return next(g for g in robot.groups if g.id == requested_group_id)


def acquire_proxy(
    db: Session,
    robot: Robot,
    target_url: str,
    requested_group_id: Optional[int],
    strategy_id: Optional[int],
    lease_minutes: Optional[int],
) -> tuple[Proxy, ProxyLease, str]:
    group = resolve_group(db, robot, requested_group_id)
    strategy, kind_label, config_id = resolve_strategy(db, robot, group, strategy_id)
    target_host = extract_host(target_url)

    proxy = strategy.select(
        db=db,
        robot_name=robot.name,
        target_url=target_url,
        target_host=target_host,
        group_id=group.id if group else None,
    )
    if proxy is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No proxy available for the requested group / target.",
        )

    minutes = lease_minutes or robot.default_lease_minutes
    if not proxy.lock_for(robot.name, lease_minutes=minutes):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Proxy was claimed by another worker — retry.",
        )

    lease = ProxyLease(
        proxy_id=proxy.id,
        group_id=group.id if group else None,
        robot_id=robot.id,
        target_url=target_url,
        target_host=target_host,
        strategy_id=config_id,
        strategy_kind=kind_label,
    )
    db.add(lease)
    db.flush()
    db.commit()
    db.refresh(lease)
    db.refresh(proxy)
    return proxy, lease, kind_label


def release_proxy(
    db: Session,
    robot: Robot,
    lease_id: int,
    success: bool,
    status_code: Optional[int],
    duration_ms: Optional[float],
    error_message: Optional[str],
) -> RequestLog:
    lease = db.get(ProxyLease, lease_id)
    if not lease or lease.robot_id != robot.id:
        raise HTTPException(status_code=404, detail="Lease not found")
    if lease.released_at is not None:
        raise HTTPException(status_code=409, detail="Lease already released")

    proxy = db.get(Proxy, lease.proxy_id)
    if proxy:
        proxy.unlock(robot.name)
        if success:
            proxy.success_count += 1
        else:
            proxy.failure_count += 1
        if duration_ms is not None:
            n = proxy.success_count + proxy.failure_count
            if n > 1:
                proxy.avg_response_time_ms = (
                    proxy.avg_response_time_ms * (n - 1) + duration_ms
                ) / n
            else:
                proxy.avg_response_time_ms = duration_ms

    log = RequestLog(
        proxy_id=lease.proxy_id,
        group_id=lease.group_id,
        robot_id=robot.id,
        robot_name=robot.name,
        target_url=lease.target_url,
        target_host=lease.target_host,
        strategy_id=lease.strategy_id,
        strategy_kind=lease.strategy_kind,
        status_code=status_code,
        success=success,
        duration_ms=duration_ms,
        error_message=error_message,
    )
    db.add(log)
    lease.released_at = datetime.utcnow()
    db.commit()
    db.refresh(log)
    return log
