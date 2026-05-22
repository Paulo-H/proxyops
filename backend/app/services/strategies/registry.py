"""Registry mapping a `StrategyKind` to its implementation + parameter schema."""

from __future__ import annotations

from typing import Any, Type

from app.models.strategy import StrategyKind
from app.schemas.strategy import StrategyKindInfo, StrategyParameterSpec
from app.services.strategies.base import ProxySelectionStrategy
from app.services.strategies.bayesian_beta import BayesianBetaStrategy
from app.services.strategies.exponential_backoff import ExponentialBackoffStrategy
from app.services.strategies.random_choice import RandomStrategy
from app.services.strategies.round_robin import RoundRobinStrategy


STRATEGY_REGISTRY: dict[StrategyKind, Type[ProxySelectionStrategy]] = {
    StrategyKind.round_robin: RoundRobinStrategy,
    StrategyKind.random: RandomStrategy,
    StrategyKind.bayesian_beta: BayesianBetaStrategy,
    StrategyKind.exponential_backoff: ExponentialBackoffStrategy,
}


PARAMETER_SPECS: dict[StrategyKind, list[StrategyParameterSpec]] = {
    StrategyKind.round_robin: [
        StrategyParameterSpec(
            name="max_logs_per_proxy",
            type="int",
            default=10,
            min=1,
            max=10000,
            description="How many recent logs to scan to determine the last use.",
        ),
    ],
    StrategyKind.random: [],
    StrategyKind.bayesian_beta: [
        StrategyParameterSpec(
            name="decay_rate_success",
            type="float",
            default=0.0002,
            min=0.0,
            max=1.0,
            description="Lambda for the exponential time-decay applied to past successes (per second).",
        ),
        StrategyParameterSpec(
            name="decay_rate_error",
            type="float",
            default=0.0003,
            min=0.0,
            max=1.0,
            description="Lambda for the exponential time-decay applied to past failures (per second).",
        ),
        StrategyParameterSpec(
            name="error_multiplier",
            type="float",
            default=1.5,
            min=1.0,
            max=10.0,
            description="Weight multiplier applied to the beta (failure) parameter.",
        ),
        StrategyParameterSpec(
            name="initial_alpha",
            type="float",
            default=10.0,
            min=0.01,
            max=1000.0,
            description="Prior alpha for proxies with too few logs.",
        ),
        StrategyParameterSpec(
            name="initial_beta",
            type="float",
            default=1.0,
            min=0.01,
            max=1000.0,
            description="Prior beta for proxies with too few logs.",
        ),
        StrategyParameterSpec(
            name="min_total_requests",
            type="int",
            default=3,
            min=0,
            max=1000,
            description="Below this number of logs, use the prior values.",
        ),
        StrategyParameterSpec(
            name="success_delay_seconds",
            type="int",
            default=10,
            min=0,
            max=3600,
            description="A success only contributes to alpha after this many seconds.",
        ),
        StrategyParameterSpec(
            name="error_delay_seconds",
            type="int",
            default=0,
            min=0,
            max=3600,
            description="A failure only contributes to beta after this many seconds.",
        ),
        StrategyParameterSpec(
            name="max_logs_per_proxy",
            type="int",
            default=200,
            min=1,
            max=10000,
            description="Maximum logs scanned per proxy.",
        ),
    ],
    StrategyKind.exponential_backoff: [
        StrategyParameterSpec(
            name="base_backoff_minutes",
            type="float",
            default=0.5,
            min=0.0,
            max=1440.0,
            description="Base quarantine time in minutes. Total = base * 2^(failures-1).",
        ),
        StrategyParameterSpec(
            name="max_backoff_minutes",
            type="float",
            default=360.0,
            min=0.0,
            max=10080.0,
            description="Cap on the quarantine time in minutes.",
        ),
        StrategyParameterSpec(
            name="max_logs_per_proxy",
            type="int",
            default=50,
            min=1,
            max=10000,
            description="Maximum logs scanned per proxy.",
        ),
    ],
}


LABELS = {
    StrategyKind.round_robin: "Round Robin",
    StrategyKind.random: "Random",
    StrategyKind.bayesian_beta: "Bayesian Beta (Thompson Sampling)",
    StrategyKind.exponential_backoff: "Exponential Backoff",
}

DESCRIPTIONS = {
    StrategyKind.round_robin: "Pick the proxy that was least recently used for the target host.",
    StrategyKind.random: "Pick a random active proxy.",
    StrategyKind.bayesian_beta: (
        "Thompson sampling over a Beta posterior built from time-decayed successes "
        "and failures. Adapts to changing proxy quality."
    ),
    StrategyKind.exponential_backoff: (
        "Round-robin that quarantines proxies returning consecutive failures. Quarantine "
        "duration doubles with each consecutive failure, up to a cap."
    ),
}


def list_strategy_kinds() -> list[StrategyKindInfo]:
    return [
        StrategyKindInfo(
            kind=kind,
            label=LABELS[kind],
            description=DESCRIPTIONS[kind],
            parameters=PARAMETER_SPECS[kind],
        )
        for kind in StrategyKind
    ]


def build_strategy(kind: StrategyKind, parameters: dict[str, Any] | None = None) -> ProxySelectionStrategy:
    impl = STRATEGY_REGISTRY[kind]
    allowed = {spec.name for spec in PARAMETER_SPECS[kind]}
    cleaned = {k: v for k, v in (parameters or {}).items() if k in allowed}
    return impl(**cleaned)
