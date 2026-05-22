from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_token, hash_api_key
from app.db.session import get_db
from app.models.robot import Robot
from app.models.user import User, UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except ValueError:
        raise credentials_exc
    if payload.get("type") != "access":
        raise credentials_exc
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exc
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise credentials_exc
    return user


def require_role(*allowed: UserRole):
    def _checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(r.value for r in allowed)}",
            )
        return user

    return _checker


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]
AdminOrOperator = Annotated[User, Depends(require_role(UserRole.admin, UserRole.operator))]


def get_robot_from_key(
    x_robot_key: Annotated[str | None, Header(alias="X-Robot-Key")] = None,
    db: Session = Depends(get_db),
) -> Robot:
    if not x_robot_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Robot-Key header",
        )
    robot = (
        db.query(Robot)
        .filter(Robot.api_key_hash == hash_api_key(x_robot_key), Robot.is_active.is_(True))
        .first()
    )
    if not robot:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid robot API key",
        )
    return robot


CurrentRobot = Annotated[Robot, Depends(get_robot_from_key)]
