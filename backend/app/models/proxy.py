import enum
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class ProxyProtocol(str, enum.Enum):
    http = "http"
    https = "https"
    socks4 = "socks4"
    socks5 = "socks5"


proxy_group_association = Table(
    "proxy_group_association",
    Base.metadata,
    Column("proxy_id", ForeignKey("proxies.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", ForeignKey("proxy_groups.id", ondelete="CASCADE"), primary_key=True),
)


class Proxy(Base):
    __tablename__ = "proxies"
    __table_args__ = (
        UniqueConstraint("host", "port", "username", name="uq_proxy_host_port_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider_id: Mapped[int | None] = mapped_column(ForeignKey("providers.id", ondelete="SET NULL"))
    host: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    password: Mapped[str | None] = mapped_column(String(255))
    protocol: Mapped[ProxyProtocol] = mapped_column(
        Enum(ProxyProtocol, name="proxy_protocol"),
        default=ProxyProtocol.http,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)

    last_used: Mapped[datetime | None] = mapped_column(DateTime)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_response_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    is_in_use: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    locked_by_robot: Mapped[str | None] = mapped_column(String(255))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, index=True)

    extra_metadata: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    provider = relationship("Provider", back_populates="proxies")
    groups = relationship(
        "ProxyGroup",
        secondary=proxy_group_association,
        back_populates="proxies",
    )
    request_logs = relationship("RequestLog", back_populates="proxy")

    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def is_locked(self) -> bool:
        if not self.is_in_use:
            return False
        if self.locked_until and datetime.utcnow() > self.locked_until:
            self.is_in_use = False
            self.locked_by_robot = None
            self.locked_until = None
            return False
        return True

    def lock_for(self, robot_name: str, lease_minutes: int = 5) -> bool:
        if self.is_locked():
            return False
        now = datetime.utcnow()
        self.is_in_use = True
        self.locked_by_robot = robot_name
        self.locked_until = now + timedelta(minutes=lease_minutes)
        self.last_used = now
        return True

    def unlock(self, robot_name: str | None = None) -> bool:
        if not self.is_in_use:
            return False
        if robot_name is not None and self.locked_by_robot != robot_name:
            return False
        self.is_in_use = False
        self.locked_by_robot = None
        self.locked_until = None
        return True
