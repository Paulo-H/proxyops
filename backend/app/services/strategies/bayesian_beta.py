"""Bayesian Beta strategy with Thompson sampling and time-decay.

Ported from the master's thesis implementation.

For each candidate proxy we compute (alpha, beta) parameters from the recent
request history:

    alpha = sum_{successes} exp(-lambda_s * dt)
    beta  = error_multiplier * sum_{failures} exp(-lambda_e * dt)

Then we draw a sample from Beta(alpha, beta) for each proxy and pick the one
with the highest sample. This is the canonical Thompson Sampling formulation
for Bernoulli rewards.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from app.models import Proxy
from app.services.strategies.base import (
    ProxySelectionStrategy,
    attach_recent_logs,
    fetch_candidate_proxies,
)


class BayesianBetaStrategy(ProxySelectionStrategy):
    kind = "bayesian_beta"

    def __init__(
        self,
        decay_rate_success: float = 0.0002,
        decay_rate_error: float = 0.0003,
        error_multiplier: float = 1.5,
        initial_alpha: float = 10.0,
        initial_beta: float = 1.0,
        min_total_requests: int = 3,
        success_delay_seconds: int = 10,
        error_delay_seconds: int = 0,
        max_logs_per_proxy: int = 200,
    ) -> None:
        self.decay_rate_success = decay_rate_success
        self.decay_rate_error = decay_rate_error
        self.error_multiplier = error_multiplier
        self.initial_alpha = initial_alpha
        self.initial_beta = initial_beta
        self.min_total_requests = min_total_requests
        self.success_delay_seconds = success_delay_seconds
        self.error_delay_seconds = error_delay_seconds
        self.max_logs_per_proxy = max_logs_per_proxy

        slowest = min(self.decay_rate_success, self.decay_rate_error)
        self._max_window = -math.log(0.01) / max(slowest, 1e-9)

    def _alpha_beta(self, proxy: Proxy) -> tuple[float, float]:
        logs = getattr(proxy, "_recent_logs", [])
        if not logs:
            return 0.0, 0.0

        now = datetime.utcnow()
        timestamps = np.array([(now - log.created_at).total_seconds() for log in logs])
        successes = np.array([log.success for log in logs], dtype=bool)
        errors = ~successes

        valid_s = successes & (timestamps >= self.success_delay_seconds) & (timestamps <= self._max_window)
        valid_e = errors & (timestamps >= self.error_delay_seconds) & (timestamps <= self._max_window)

        alpha = 0.0
        beta = 0.0

        if np.any(valid_s):
            dts = timestamps[valid_s]
            weights = np.exp(-self.decay_rate_success * dts)
            alpha = float(weights[weights >= 0.01].sum())
        if np.any(valid_e):
            dts = timestamps[valid_e]
            weights = np.exp(-self.decay_rate_error * dts)
            beta = float(weights[weights >= 0.01].sum()) * self.error_multiplier

        return alpha, beta

    def _thompson_sample_batch(self, alphas: np.ndarray, betas: np.ndarray) -> np.ndarray:
        alphas = np.maximum(alphas, 0.01)
        betas = np.maximum(betas, 0.01)
        # Clip very large values to keep numpy.random.beta numerically stable.
        alphas = np.minimum(alphas, 1000.0)
        betas = np.minimum(betas, 1000.0)
        try:
            return np.random.beta(alphas, betas)
        except (ValueError, OverflowError):
            expected = alphas / (alphas + betas)
            return np.clip(expected + np.random.normal(0, 0.1, size=len(alphas)), 0.0, 1.0)

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
        if len(proxies) == 1:
            return proxies[0]

        attach_recent_logs(db, proxies, target_host, self.max_logs_per_proxy)

        alphas: list[float] = []
        betas: list[float] = []
        for proxy in proxies:
            logs = getattr(proxy, "_recent_logs", [])
            if len(logs) < self.min_total_requests:
                alphas.append(self.initial_alpha)
                betas.append(self.initial_beta)
            else:
                a, b = self._alpha_beta(proxy)
                alphas.append(a)
                betas.append(b)

        scores = self._thompson_sample_batch(np.asarray(alphas), np.asarray(betas))
        return proxies[int(np.argmax(scores))]
