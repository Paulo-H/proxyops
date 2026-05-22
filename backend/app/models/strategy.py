import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.session import Base


class StrategyKind(str, enum.Enum):
    round_robin = "round_robin"
    random = "random"
    bayesian_beta = "bayesian_beta"
    exponential_backoff = "exponential_backoff"


class StrategyConfig(Base):
    """A named, parameterized rotation strategy preset.

    Multiple presets can exist for the same `kind` — e.g. an
    aggressive bayesian_beta with a fast success decay and a
    conservative one with slow decay.
    """

    __tablename__ = "strategy_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[StrategyKind] = mapped_column(
        Enum(StrategyKind, name="strategy_kind"), nullable=False
    )
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())
