from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from backend.database import get_db
from backend.models import User
from backend.schemas import UserCreate, UserResponse, UserUpdate

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already taken.")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=pwd_context.hash(body.password),
        is_disabled=body.is_disabled,
        has_stroller_profile=body.has_stroller_profile,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if body.username is not None:
        conflict = (
            db.query(User)
            .filter(User.username == body.username, User.id != user_id)
            .first()
        )
        if conflict:
            raise HTTPException(status_code=400, detail="Username already taken.")
        user.username = body.username
    if body.is_disabled is not None:
        user.is_disabled = body.is_disabled
    if body.has_stroller_profile is not None:
        user.has_stroller_profile = body.has_stroller_profile

    db.commit()
    db.refresh(user)
    return user
