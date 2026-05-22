from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.session import Base


class ProxyLease(Base):
    """Tracks a single robot's checkout of a proxy.

    Created on `/rotation/acquire`, finalized on `/rotation/release`.
    The release endpoint uses the lease id to attribute the request log to the
    right proxy without trusting the robot to echo back the proxy id.
    """

    __tablename__ = "proxy_leases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    proxy_id: Mapped[int] = mapped_column(ForeignKey("proxies.id", ondelete="CASCADE"), nullable=False)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("proxy_groups.id", ondelete="SET NULL"))
    robot_id: Mapped[int] = mapped_column(ForeignKey("robots.id", ondelete="CASCADE"), nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    target_host: Mapped[str | None] = mapped_column(String(255))
    strategy_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_configs.id", ondelete="SET NULL")
    )
    strategy_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime)
