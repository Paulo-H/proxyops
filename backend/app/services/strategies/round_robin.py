"""Round-robin selection: pick the proxy least-recently used for the target host."""

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


class RoundRobinStrategy(ProxySelectionStrategy):
    kind = "round_robin"

    def __init__(self, max_logs_per_proxy: int = 10) -> None:
        self.max_logs_per_proxy = max_logs_per_proxy

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

        def last_use(proxy: Proxy) -> datetime:
            logs = getattr(proxy, "_recent_logs", [])
            return logs[0].created_at if logs else datetime.min

        proxies.sort(key=last_use)
        return proxies[0]
