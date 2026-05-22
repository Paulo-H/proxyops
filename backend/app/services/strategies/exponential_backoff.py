"""Round-robin selection that quarantines proxies with consecutive failures.

Ported from the master's thesis implementation. A proxy with ``k`` consecutive
failures (counting back from the most recent log for the same target host) is
considered "in timeout" for ``base * 2^(k-1)`` minutes, capped at ``max_backoff``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Proxy
from app.services.strategies.base import (
    ProxySelectionStrategy,
    attach_recent_logs,
    fetch_candidate_proxies,
)


class ExponentialBackoffStrategy(ProxySelectionStrategy):
    kind = "exponential_backoff"

    def __init__(
        self,
        base_backoff_minutes: float = 0.5,
        max_backoff_minutes: float = 360.0,
        max_logs_per_proxy: int = 50,
    ) -> None:
        self.base_backoff_minutes = base_backoff_minutes
        self.max_backoff_minutes = max_backoff_minutes
        self.max_logs_per_proxy = max_logs_per_proxy

    def _backoff_minutes(self, consecutive_failures: int) -> float:
        if consecutive_failures <= 0:
            return 0.0
        return min(
            self.base_backoff_minutes * (2 ** (consecutive_failures - 1)),
            self.max_backoff_minutes,
        )

    def _is_in_timeout(self, proxy: Proxy, now: datetime) -> tuple[bool, datetime]:
        logs = getattr(proxy, "_recent_logs", [])
        if not logs:
            return False, datetime.min

        last_used = logs[0].created_at
        consecutive = 0
        last_failure: datetime | None = None
        for log in logs:
            if log.success:
                break
            consecutive += 1
            if last_failure is None:
                last_failure = log.created_at

        if consecutive == 0 or last_failure is None:
            return False, last_used

        wait_minutes = self._backoff_minutes(consecutive)
        elapsed_minutes = (now - last_failure).total_seconds() / 60
        return elapsed_minutes < wait_minutes, last_used

    def select(
        self,
        db: Session,
        robot_name: str,
        target_url: str,
        target_host: str,
        group_id: Optional[int],
    ) -> Optional[Proxy]:
        proxies = fetch_candidate_proxies(db, group_id)
        if not proxies:
            return None

        attach_recent_logs(db, proxies, target_host, self.max_logs_per_proxy)

        now = datetime.utcnow()
        available: list[tuple[Proxy, datetime]] = []
        for proxy in proxies:
            in_timeout, last_used = self._is_in_timeout(proxy, now)
            if not in_timeout:
                available.append((proxy, last_used))

        if not available:
            return None

        available.sort(key=lambda pair: pair[1])
        return available[0][0]
