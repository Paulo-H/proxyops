"""Base interface and shared helpers for proxy selection strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import desc
from sqlalchemy.orm import Session, selectinload

from app.models import Proxy, ProxyGroup, RequestLog


def clean_expired_locks(db: Session) -> int:
    """Release proxies whose lease expired. Returns the number of rows touched."""
    now = datetime.utcnow()
    updated = (
        db.query(Proxy)
        .filter(Proxy.is_in_use.is_(True), Proxy.locked_until < now)
        .update(
            {"is_in_use": False, "locked_by_robot": None, "locked_until": None},
            synchronize_session=False,
        )
    )
    return updated


def fetch_candidate_proxies(
    db: Session,
    group_id: Optional[int],
    exclude_locked: bool = True,
) -> list[Proxy]:
    """Return active, unlocked, non-expired proxies belonging to ``group_id`` (if given)."""
    clean_expired_locks(db)

    query = db.query(Proxy).options(selectinload(Proxy.groups)).filter(Proxy.is_active.is_(True))

    if exclude_locked:
        query = query.filter(Proxy.is_in_use.is_(False))

    if group_id is not None:
        query = query.join(Proxy.groups).filter(ProxyGroup.id == group_id)

    now = datetime.utcnow()
    proxies = [
        p for p in query.order_by(Proxy.last_used.asc().nullsfirst()).all()
        if not p.expires_at or p.expires_at > now
    ]
    return proxies


def attach_recent_logs(
    db: Session,
    proxies: Sequence[Proxy],
    target_host: str,
    max_logs_per_proxy: int,
) -> None:
    """Attach `_recent_logs` to each proxy: the most recent N logs for ``target_host``."""
    for proxy in proxies:
        logs = (
            db.query(RequestLog)
            .filter(RequestLog.proxy_id == proxy.id, RequestLog.target_host == target_host)
            .order_by(desc(RequestLog.created_at))
            .limit(max_logs_per_proxy)
            .all()
        )
        proxy._recent_logs = logs  # type: ignore[attr-defined]


class ProxySelectionStrategy(ABC):
    """Strategy contract used by the rotation service."""

    kind: str = ""

    @abstractmethod
    def select(
        self,
        db: Session,
        robot_name: str,
        target_url: str,
        target_host: str,
        group_id: Optional[int],
    ) -> Optional[Proxy]:
        ...
