from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class RequestLog(Base):
    __tablename__ = "request_logs"
    __table_args__ = (
        Index("ix_request_logs_created_at", "created_at"),
        Index("ix_request_logs_robot_created", "robot_id", "created_at"),
        Index("ix_request_logs_proxy_created", "proxy_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    proxy_id: Mapped[int] = mapped_column(ForeignKey("proxies.id", ondelete="CASCADE"), nullable=False)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("proxy_groups.id", ondelete="SET NULL"))
    robot_id: Mapped[int | None] = mapped_column(ForeignKey("robots.id", ondelete="SET NULL"))

    robot_name: Mapped[str] = mapped_column(String(150), nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    target_host: Mapped[str | None] = mapped_column(String(255), index=True)

    # Which rotation strategy produced this selection. `strategy_kind` is
    # denormalized so breakdowns survive deletion of the preset.
    strategy_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_configs.id", ondelete="SET NULL")
    )
    strategy_kind: Mapped[str | None] = mapped_column(String(50), index=True)

    status_code: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    duration_ms: Mapped[float | None] = mapped_column(Float)
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    proxy = relationship("Proxy", back_populates="request_logs")
    group = relationship("ProxyGroup", back_populates="request_logs")
    robot = relationship("Robot", back_populates="request_logs")
