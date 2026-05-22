from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import AdminOnly, CurrentUser
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas import UserCreate, UserOut, UserPasswordChange, UserUpdate

router = APIRouter()


@router.get("", response_model=list[UserOut])
def list_users(_: AdminOnly, db: Session = Depends(get_db)) -> list[User]:
    return db.query(User).order_by(User.id.asc()).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, _: AdminOnly, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")
    user = User(
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        is_active=body.is_active,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    _: AdminOnly,
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, current: AdminOnly, db: Session = Depends(get_db)) -> None:
    if user_id == current.id:
        raise HTTPException(400, "You cannot delete your own account")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    db.delete(user)
    db.commit()


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: UserPasswordChange,
    current: CurrentUser,
    db: Session = Depends(get_db),
) -> None:
    if not verify_password(body.current_password, current.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    current.hashed_password = hash_password(body.new_password)
    db.commit()
