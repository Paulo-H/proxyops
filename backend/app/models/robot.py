from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


robot_group_association = Table(
    "robot_group_association",
    Base.metadata,
    Column("robot_id", ForeignKey("robots.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", ForeignKey("proxy_groups.id", ondelete="CASCADE"), primary_key=True),
)


class Robot(Base):
    __tablename__ = "robots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # Only the SHA-256 hash of the API key is persisted; the raw key is shown
    # to the operator once. `api_key_prefix` is a non-secret hint for the UI.
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    api_key_prefix: Mapped[str] = mapped_column(String(12), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_lease_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    groups = relationship(
        "ProxyGroup",
        secondary=robot_group_association,
        back_populates="robots",
    )
    request_logs = relationship("RequestLog", back_populates="robot")
