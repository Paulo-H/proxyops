from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.deps import AdminOrOperator, CurrentUser
from app.core.security import api_key_prefix, generate_api_key, hash_api_key
from app.db.session import get_db
from app.models import ProxyGroup, Robot
from app.schemas import RobotCreate, RobotOut, RobotOutWithKey, RobotUpdate

router = APIRouter()


def _serialize(robot: Robot, raw_key: str | None = None) -> RobotOut | RobotOutWithKey:
    common = dict(
        id=robot.id,
        name=robot.name,
        description=robot.description,
        is_active=robot.is_active,
        default_lease_minutes=robot.default_lease_minutes,
        created_at=robot.created_at,
        group_ids=[g.id for g in robot.groups],
        api_key_prefix=robot.api_key_prefix,
    )
    # The raw key only exists in memory right after generation; if present we
    # echo it back exactly once.
    if raw_key is not None:
        return RobotOutWithKey(**common, api_key=raw_key)
    return RobotOut(**common)


def _assign_groups(db: Session, robot: Robot, group_ids: list[int]) -> None:
    if not group_ids:
        robot.groups = []
        return
    groups = db.query(ProxyGroup).filter(ProxyGroup.id.in_(group_ids)).all()
    if len(groups) != len(set(group_ids)):
        raise HTTPException(400, "One or more group_ids do not exist")
    robot.groups = groups


@router.get("", response_model=list[RobotOut])
def list_robots(_: CurrentUser, db: Session = Depends(get_db)) -> list[RobotOut]:
    robots = (
        db.query(Robot).options(selectinload(Robot.groups)).order_by(Robot.name).all()
    )
    return [_serialize(r) for r in robots]


@router.post("", response_model=RobotOutWithKey, status_code=status.HTTP_201_CREATED)
def create_robot(
    body: RobotCreate,
    _: AdminOrOperator,
    db: Session = Depends(get_db),
) -> RobotOutWithKey:
    if db.query(Robot).filter(Robot.name == body.name).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Robot name already in use")
    raw_key = generate_api_key()
    robot = Robot(
        name=body.name,
        description=body.description,
        is_active=body.is_active,
        default_lease_minutes=body.default_lease_minutes,
        api_key_hash=hash_api_key(raw_key),
        api_key_prefix=api_key_prefix(raw_key),
    )
    _assign_groups(db, robot, body.group_ids)
    db.add(robot)
    db.commit()
    db.refresh(robot)
    return _serialize(robot, raw_key=raw_key)


@router.patch("/{robot_id}", response_model=RobotOut)
def update_robot(
    robot_id: int,
    body: RobotUpdate,
    _: AdminOrOperator,
    db: Session = Depends(get_db),
) -> RobotOut:
    robot = db.get(Robot, robot_id)
    if not robot:
        raise HTTPException(404, "Robot not found")
    data = body.model_dump(exclude_unset=True)
    group_ids = data.pop("group_ids", None)
    for k, v in data.items():
        setattr(robot, k, v)
    if group_ids is not None:
        _assign_groups(db, robot, group_ids)
    db.commit()
    db.refresh(robot)
    return _serialize(robot)


@router.post("/{robot_id}/rotate-key", response_model=RobotOutWithKey)
def rotate_key(robot_id: int, _: AdminOrOperator, db: Session = Depends(get_db)) -> RobotOutWithKey:
    robot = db.get(Robot, robot_id)
    if not robot:
        raise HTTPException(404, "Robot not found")
    raw_key = generate_api_key()
    robot.api_key_hash = hash_api_key(raw_key)
    robot.api_key_prefix = api_key_prefix(raw_key)
    db.commit()
    db.refresh(robot)
    return _serialize(robot, raw_key=raw_key)


@router.delete("/{robot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_robot(robot_id: int, _: AdminOrOperator, db: Session = Depends(get_db)) -> None:
    robot = db.get(Robot, robot_id)
    if not robot:
        raise HTTPException(404, "Robot not found")
    db.delete(robot)
    db.commit()
