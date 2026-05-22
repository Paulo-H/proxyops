from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class ProxyGroup(Base):
    __tablename__ = "proxy_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    default_strategy_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_configs.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    proxies = relationship(
        "Proxy",
        secondary="proxy_group_association",
        back_populates="groups",
    )
    robots = relationship(
        "Robot",
        secondary="robot_group_association",
        back_populates="groups",
    )
    default_strategy = relationship("StrategyConfig", foreign_keys=[default_strategy_id])
    request_logs = relationship("RequestLog", back_populates="group")
