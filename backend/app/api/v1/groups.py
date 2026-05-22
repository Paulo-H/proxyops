from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.deps import AdminOrOperator, CurrentUser
from app.db.session import get_db
from app.models import Proxy, ProxyGroup, Robot
from app.schemas import ProxyGroupCreate, ProxyGroupOut, ProxyGroupUpdate

router = APIRouter()


def _serialize(group: ProxyGroup) -> ProxyGroupOut:
    return ProxyGroupOut(
        id=group.id,
        name=group.name,
        description=group.description,
        default_strategy_id=group.default_strategy_id,
        created_at=group.created_at,
        proxy_count=len(group.proxies),
        robot_count=len(group.robots),
    )


def _assign_proxies(db: Session, group: ProxyGroup, proxy_ids: list[int]) -> None:
    if not proxy_ids:
        group.proxies = []
        return
    proxies = db.query(Proxy).filter(Proxy.id.in_(proxy_ids)).all()
    if len(proxies) != len(set(proxy_ids)):
        raise HTTPException(400, "One or more proxy_ids do not exist")
    group.proxies = proxies


@router.get("", response_model=list[ProxyGroupOut])
def list_groups(_: CurrentUser, db: Session = Depends(get_db)) -> list[ProxyGroupOut]:
    groups = (
        db.query(ProxyGroup)
        .options(selectinload(ProxyGroup.proxies), selectinload(ProxyGroup.robots))
        .order_by(ProxyGroup.name)
        .all()
    )
    return [_serialize(g) for g in groups]


@router.post("", response_model=ProxyGroupOut, status_code=status.HTTP_201_CREATED)
def create_group(
    body: ProxyGroupCreate,
    _: AdminOrOperator,
    db: Session = Depends(get_db),
) -> ProxyGroupOut:
    if db.query(ProxyGroup).filter(ProxyGroup.name == body.name).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Group name already in use")
    group = ProxyGroup(
        name=body.name,
        description=body.description,
        default_strategy_id=body.default_strategy_id,
    )
    _assign_proxies(db, group, body.proxy_ids)
    db.add(group)
    db.commit()
    db.refresh(group)
    return _serialize(group)


@router.patch("/{group_id}", response_model=ProxyGroupOut)
def update_group(
    group_id: int,
    body: ProxyGroupUpdate,
    _: AdminOrOperator,
    db: Session = Depends(get_db),
) -> ProxyGroupOut:
    group = db.get(ProxyGroup, group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    data = body.model_dump(exclude_unset=True)
    proxy_ids = data.pop("proxy_ids", None)
    for k, v in data.items():
        setattr(group, k, v)
    if proxy_ids is not None:
        _assign_proxies(db, group, proxy_ids)
    db.commit()
    db.refresh(group)
    return _serialize(group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, _: AdminOrOperator, db: Session = Depends(get_db)) -> None:
    group = db.get(ProxyGroup, group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    db.delete(group)
    db.commit()
