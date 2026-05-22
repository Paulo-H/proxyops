from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import AdminOrOperator, CurrentUser
from app.db.session import get_db
from app.models import Provider, Proxy
from app.schemas import ProviderCreate, ProviderOut, ProviderUpdate

router = APIRouter()


def _to_out(provider: Provider, count: int) -> ProviderOut:
    data = ProviderOut.model_validate(provider).model_dump()
    data["proxy_count"] = count
    return ProviderOut(**data)


@router.get("", response_model=list[ProviderOut])
def list_providers(_: CurrentUser, db: Session = Depends(get_db)) -> list[ProviderOut]:
    counts = dict(
        db.query(Proxy.provider_id, func.count(Proxy.id))
        .group_by(Proxy.provider_id)
        .all()
    )
    return [_to_out(p, counts.get(p.id, 0)) for p in db.query(Provider).order_by(Provider.name).all()]


@router.post("", response_model=ProviderOut, status_code=status.HTTP_201_CREATED)
def create_provider(
    body: ProviderCreate,
    _: AdminOrOperator,
    db: Session = Depends(get_db),
) -> ProviderOut:
    if db.query(Provider).filter(Provider.name == body.name).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Provider name already in use")
    provider = Provider(
        name=body.name,
        website=str(body.website) if body.website else None,
        contact_email=body.contact_email,
        notes=body.notes,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return _to_out(provider, 0)


@router.patch("/{provider_id}", response_model=ProviderOut)
def update_provider(
    provider_id: int,
    body: ProviderUpdate,
    _: AdminOrOperator,
    db: Session = Depends(get_db),
) -> ProviderOut:
    provider = db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(404, "Provider not found")
    payload = body.model_dump(exclude_unset=True)
    if "website" in payload and payload["website"] is not None:
        payload["website"] = str(payload["website"])
    for k, v in payload.items():
        setattr(provider, k, v)
    db.commit()
    db.refresh(provider)
    count = db.query(func.count(Proxy.id)).filter(Proxy.provider_id == provider.id).scalar() or 0
    return _to_out(provider, count)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(provider_id: int, _: AdminOrOperator, db: Session = Depends(get_db)) -> None:
    provider = db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(404, "Provider not found")
    db.delete(provider)
    db.commit()
