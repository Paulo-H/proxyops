"""Pure-random selection."""

from __future__ import annotations

import random
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Proxy
from app.services.strategies.base import ProxySelectionStrategy, fetch_candidate_proxies


class RandomStrategy(ProxySelectionStrategy):
    kind = "random"

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
        return random.choice(proxies)
