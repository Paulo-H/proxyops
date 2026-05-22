from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import AdminOrOperator, CurrentUser
from app.db.session import get_db
from app.models import StrategyConfig
from app.schemas import (
    StrategyConfigCreate,
    StrategyConfigOut,
    StrategyConfigUpdate,
    StrategyKindInfo,
)
from app.services.strategies import list_strategy_kinds

router = APIRouter()


@router.get("/kinds", response_model=list[StrategyKindInfo], summary="Available rotation algorithms and their parameters")
def list_kinds(_: CurrentUser) -> list[StrategyKindInfo]:
    return list_strategy_kinds()


@router.get("", response_model=list[StrategyConfigOut])
def list_configs(_: CurrentUser, db: Session = Depends(get_db)) -> list[StrategyConfig]:
    return db.query(StrategyConfig).order_by(StrategyConfig.name).all()


@router.post("", response_model=StrategyConfigOut, status_code=status.HTTP_201_CREATED)
def create_config(
    body: StrategyConfigCreate,
    _: AdminOrOperator,
    db: Session = Depends(get_db),
) -> StrategyConfig:
    if db.query(StrategyConfig).filter(StrategyConfig.name == body.name).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Name already in use")
    cfg = StrategyConfig(**body.model_dump())
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


@router.patch("/{config_id}", response_model=StrategyConfigOut)
def update_config(
    config_id: int,
    body: StrategyConfigUpdate,
    _: AdminOrOperator,
    db: Session = Depends(get_db),
) -> StrategyConfig:
    cfg = db.get(StrategyConfig, config_id)
    if not cfg:
        raise HTTPException(404, "Strategy config not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(cfg, k, v)
    db.commit()
    db.refresh(cfg)
    return cfg


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_config(config_id: int, _: AdminOrOperator, db: Session = Depends(get_db)) -> None:
    cfg = db.get(StrategyConfig, config_id)
    if not cfg:
        raise HTTPException(404, "Strategy config not found")
    db.delete(cfg)
    db.commit()
