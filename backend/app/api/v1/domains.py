from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import AdminOrOperator, CurrentUser
from app.db.session import get_db
from app.models import Domain
from app.schemas import DomainCreate, DomainOut, DomainUpdate

router = APIRouter()


@router.get("", response_model=list[DomainOut])
def list_domains(_: CurrentUser, db: Session = Depends(get_db)) -> list[Domain]:
    return db.query(Domain).order_by(Domain.hostname).all()


@router.post("", response_model=DomainOut, status_code=status.HTTP_201_CREATED)
def create_domain(body: DomainCreate, _: AdminOrOperator, db: Session = Depends(get_db)) -> Domain:
    if db.query(Domain).filter(Domain.hostname == body.hostname).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Domain already registered")
    domain = Domain(**body.model_dump())
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


@router.patch("/{domain_id}", response_model=DomainOut)
def update_domain(
    domain_id: int,
    body: DomainUpdate,
    _: AdminOrOperator,
    db: Session = Depends(get_db),
) -> Domain:
    domain = db.get(Domain, domain_id)
    if not domain:
        raise HTTPException(404, "Domain not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(domain, k, v)
    db.commit()
    db.refresh(domain)
    return domain


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain(domain_id: int, _: AdminOrOperator, db: Session = Depends(get_db)) -> None:
    domain = db.get(Domain, domain_id)
    if not domain:
        raise HTTPException(404, "Domain not found")
    db.delete(domain)
    db.commit()
