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


# ---------------------------------------------------------------------------
# Simple ("friendly") parameters
# ---------------------------------------------------------------------------
# Some strategies expose math-heavy knobs (decay rates, Beta priors...). The
# simple layer presents a handful of intuitive 1-10 dials and translates them
# into the raw parameters at build time. A preset stores `{"mode": "simple",
# <dial>: <value>, ...}` in its JSON; only the dials are persisted and they are
# re-translated on every build, so tuning the formula updates existing presets.

SIMPLE_PARAMETER_SPECS: dict[StrategyKind, list[StrategyParameterSpec]] = {
    StrategyKind.bayesian_beta: [
        StrategyParameterSpec(
            name="precision",
            type="int",
            default=5,
            min=1,
            max=10,
            description="How much history to weigh per decision. Higher = more data considered (more accurate, a bit heavier).",
        ),
        StrategyParameterSpec(
            name="memory",
            type="int",
            default=5,
            min=1,
            max=10,
            description="How long the system remembers a proxy's behavior. Low = forgets in minutes; high = remembers for hours.",
        ),
        StrategyParameterSpec(
            name="error_sensitivity",
            type="int",
            default=5,
            min=1,
            max=10,
            description="How harshly failing proxies are penalized. Higher = avoid a proxy faster (and longer) after errors.",
        ),
        StrategyParameterSpec(
            name="success_sensitivity",
            type="int",
            default=5,
            min=1,
            max=10,
            description="How quickly a good result starts to count. Higher = react to fresh successes almost immediately.",
        ),
        StrategyParameterSpec(
            name="exploration",
            type="int",
            default=5,
            min=1,
            max=10,
            description="How willing it is to try new / unproven proxies. Higher = experiment more; lower = stick to known-good ones.",
        ),
    ],
}


def _clamp_dial(value: Any, default: float = 5.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = default
    return min(10.0, max(1.0, v))


def _bayesian_beta_simple_to_raw(simple: dict[str, Any]) -> dict[str, Any]:
    import math

    precision = _clamp_dial(simple.get("precision", 5))
    memory = _clamp_dial(simple.get("memory", 5))
    error_sensitivity = _clamp_dial(simple.get("error_sensitivity", 5))
    success_sensitivity = _clamp_dial(simple.get("success_sensitivity", 5))
    exploration = _clamp_dial(simple.get("exploration", 5))

    # precision -> logs scanned + how soon real history is trusted
    max_logs = int(round(50 * precision))               # 50 .. 500
    min_total = int(round(2 + (precision - 1) * 0.9))   # ~2 .. 10

    # memory -> half-life (minutes) of a result's weight, then lambda = ln2 / halflife
    halflife_minutes = 2.0 * (1.74 ** (memory - 1))     # ~2 min .. ~6 h
    base_lambda = math.log(2) / (halflife_minutes * 60.0)

    # error sensitivity -> stronger penalty + errors remembered a bit longer
    error_multiplier = 1.0 + (error_sensitivity - 1) / 9.0 * 2.0   # 1.0 .. 3.0
    decay_error = max(base_lambda * (1.3 - 0.06 * error_sensitivity), base_lambda * 0.5)

    # success sensitivity -> how soon a success begins to count
    success_delay = int(round(max(0.0, 15.0 - (success_sensitivity - 1) * 1.6)))  # ~15 .. 0 s

    # exploration -> optimism of the prior given to unproven proxies
    initial_alpha = 4.0 + exploration                   # 5 .. 14

    return {
        "decay_rate_success": round(base_lambda, 6),
        "decay_rate_error": round(decay_error, 6),
        "error_multiplier": round(error_multiplier, 3),
        "initial_alpha": round(initial_alpha, 2),
        "initial_beta": 1.0,
        "min_total_requests": min_total,
        "success_delay_seconds": success_delay,
        "error_delay_seconds": 0,
        "max_logs_per_proxy": max_logs,
    }


_SIMPLE_TRANSLATORS = {
    StrategyKind.bayesian_beta: _bayesian_beta_simple_to_raw,
}


def is_simple(parameters: dict[str, Any] | None) -> bool:
    return bool(parameters) and parameters.get("mode") == "simple"


def resolve_raw_parameters(kind: StrategyKind, parameters: dict[str, Any] | None) -> dict[str, Any]:
    """Return the effective raw parameters, translating simple presets when needed."""
    if is_simple(parameters) and kind in _SIMPLE_TRANSLATORS:
        return _SIMPLE_TRANSLATORS[kind](parameters or {})
    allowed = {spec.name for spec in PARAMETER_SPECS[kind]}
    return {k: v for k, v in (parameters or {}).items() if k in allowed}


def list_strategy_kinds() -> list[StrategyKindInfo]:
    return [
        StrategyKindInfo(
            kind=kind,
            label=LABELS[kind],
            description=DESCRIPTIONS[kind],
            parameters=PARAMETER_SPECS[kind],
            simple_parameters=SIMPLE_PARAMETER_SPECS.get(kind, []),
        )
        for kind in StrategyKind
    ]


def build_strategy(kind: StrategyKind, parameters: dict[str, Any] | None = None) -> ProxySelectionStrategy:
    impl = STRATEGY_REGISTRY[kind]
    cleaned = resolve_raw_parameters(kind, parameters)
    return impl(**cleaned)
