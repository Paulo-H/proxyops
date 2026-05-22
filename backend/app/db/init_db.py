"""First-boot bootstrap: ensure schema exists and a seed admin is present."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models.strategy import StrategyConfig, StrategyKind
from app.models.user import User, UserRole

log = logging.getLogger("init_db")


def _ensure_admin(db: Session) -> None:
    if db.query(User).count() > 0:
        return
    admin = User(
        email=settings.FIRST_ADMIN_EMAIL,
        full_name="Initial admin",
        hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
        role=UserRole.admin,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    log.info("Seeded initial admin user: %s", settings.FIRST_ADMIN_EMAIL)


def _ensure_default_strategies(db: Session) -> None:
    defaults = [
        ("Default Round Robin", StrategyKind.round_robin, {"max_logs_per_proxy": 10}),
        ("Default Random", StrategyKind.random, {}),
        (
            "Default Bayesian Beta",
            StrategyKind.bayesian_beta,
            {
                "decay_rate_success": 0.0002,
                "decay_rate_error": 0.0003,
                "error_multiplier": 1.5,
                "initial_alpha": 10.0,
                "initial_beta": 1.0,
                "min_total_requests": 3,
                "success_delay_seconds": 10,
                "error_delay_seconds": 0,
                "max_logs_per_proxy": 200,
            },
        ),
        (
            "Default Exponential Backoff",
            StrategyKind.exponential_backoff,
            {
                "base_backoff_minutes": 0.5,
                "max_backoff_minutes": 360.0,
                "max_logs_per_proxy": 50,
            },
        ),
    ]
    existing = {row.name for row in db.query(StrategyConfig).all()}
    for name, kind, params in defaults:
        if name in existing:
            continue
        db.add(StrategyConfig(name=name, kind=kind, parameters=params))
    db.commit()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _ensure_admin(db)
        _ensure_default_strategies(db)
    finally:
        db.close()
