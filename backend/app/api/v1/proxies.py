from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.core.deps import AdminOrOperator, CurrentUser
from app.db.session import get_db
from app.models import Proxy, ProxyGroup
from app.schemas import ProxyBulkCreate, ProxyCreate, ProxyOut, ProxyUpdate

router = APIRouter()


def _serialize(proxy: Proxy) -> ProxyOut:
    total = proxy.success_count + proxy.failure_count
    success_rate = (proxy.success_count / total) if total else 0.0
    return ProxyOut(
        id=proxy.id,
        provider_id=proxy.provider_id,
        host=proxy.host,
        port=proxy.port,
        username=proxy.username,
        protocol=proxy.protocol,
        is_active=proxy.is_active,
        expires_at=proxy.expires_at,
        extra_metadata=proxy.extra_metadata,
        last_used=proxy.last_used,
        success_count=proxy.success_count,
        failure_count=proxy.failure_count,
        avg_response_time_ms=proxy.avg_response_time_ms,
        is_in_use=proxy.is_in_use,
        created_at=proxy.created_at,
        group_ids=[g.id for g in proxy.groups],
        provider_name=proxy.provider.name if proxy.provider else None,
        success_rate=round(success_rate, 4),
    )


@router.get("", response_model=list[ProxyOut])
def list_proxies(
    _: CurrentUser,
    db: Session = Depends(get_db),
    provider_id: int | None = None,
    group_id: int | None = None,
    is_active: bool | None = None,
    search: str | None = Query(default=None, description="Match against host or username"),
    expiring_in_days: int | None = Query(default=None, ge=0, le=365),
) -> list[ProxyOut]:
    query = db.query(Proxy).options(selectinload(Proxy.groups), selectinload(Proxy.provider))
    if provider_id is not None:
        query = query.filter(Proxy.provider_id == provider_id)
    if is_active is not None:
        query = query.filter(Proxy.is_active.is_(is_active))
    if group_id is not None:
        query = query.join(Proxy.groups).filter(ProxyGroup.id == group_id)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Proxy.host.ilike(like), Proxy.username.ilike(like)))
    if expiring_in_days is not None:
        from datetime import timedelta
        cutoff = datetime.utcnow() + timedelta(days=expiring_in_days)
        query = query.filter(Proxy.expires_at.isnot(None), Proxy.expires_at <= cutoff)
    return [_serialize(p) for p in query.order_by(Proxy.id.desc()).all()]


def _assign_groups(db: Session, proxy: Proxy, group_ids: list[int]) -> None:
    if not group_ids:
        proxy.groups = []
        return
    groups = db.query(ProxyGroup).filter(ProxyGroup.id.in_(group_ids)).all()
    if len(groups) != len(set(group_ids)):
        raise HTTPException(400, "One or more group_ids do not exist")
    proxy.groups = groups


@router.post("", response_model=ProxyOut, status_code=status.HTTP_201_CREATED)
def create_proxy(
    body: ProxyCreate,
    _: AdminOrOperator,
    db: Session = Depends(get_db),
) -> ProxyOut:
    proxy = Proxy(
        provider_id=body.provider_id,
        host=body.host,
        port=body.port,
        username=body.username,
        password=body.password,
        protocol=body.protocol,
        is_active=body.is_active,
        expires_at=body.expires_at,
        extra_metadata=body.extra_metadata,
    )
    _assign_groups(db, proxy, body.group_ids)
    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    return _serialize(proxy)


@router.post("/bulk", response_model=list[ProxyOut], status_code=status.HTTP_201_CREATED)
def bulk_create(
    body: ProxyBulkCreate,
    _: AdminOrOperator,
    db: Session = Depends(get_db),
) -> list[ProxyOut]:
    if body.group_ids:
        groups = db.query(ProxyGroup).filter(ProxyGroup.id.in_(body.group_ids)).all()
        if len(groups) != len(set(body.group_ids)):
            raise HTTPException(400, "One or more group_ids do not exist")
    else:
        groups = []
    created: list[Proxy] = []
    for row in body.proxies:
        proxy = Proxy(
            provider_id=body.provider_id,
            host=row.host,
            port=row.port,
            username=row.username,
            password=row.password,
            protocol=row.protocol,
            expires_at=row.expires_at,
        )
        proxy.groups = list(groups)
        db.add(proxy)
        created.append(proxy)
    db.commit()
    for p in created:
        db.refresh(p)
    return [_serialize(p) for p in created]


@router.patch("/{proxy_id}", response_model=ProxyOut)
def update_proxy(
    proxy_id: int,
    body: ProxyUpdate,
    _: AdminOrOperator,
    db: Session = Depends(get_db),
) -> ProxyOut:
    proxy = db.get(Proxy, proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    data = body.model_dump(exclude_unset=True)
    group_ids = data.pop("group_ids", None)
    for k, v in data.items():
        setattr(proxy, k, v)
    if group_ids is not None:
        _assign_groups(db, proxy, group_ids)
    db.commit()
    db.refresh(proxy)
    return _serialize(proxy)


@router.delete("/{proxy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_proxy(proxy_id: int, _: AdminOrOperator, db: Session = Depends(get_db)) -> None:
    proxy = db.get(Proxy, proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    db.delete(proxy)
    db.commit()


@router.post("/{proxy_id}/unlock", response_model=ProxyOut)
def force_unlock(proxy_id: int, _: AdminOrOperator, db: Session = Depends(get_db)) -> ProxyOut:
    proxy = db.get(Proxy, proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    proxy.is_in_use = False
    proxy.locked_by_robot = None
    proxy.locked_until = None
    db.commit()
    db.refresh(proxy)
    return _serialize(proxy)
