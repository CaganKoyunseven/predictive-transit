from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserSession
from backend.schemas import StrollerSessionResponse, StrollerSessionUpdate

router = APIRouter()

STROLLER_CACHE_MINUTES = 90


@router.get("/{user_id}/session", response_model=StrollerSessionResponse)
def get_session(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if not user.has_stroller_profile:
        return StrollerSessionResponse(
            user_id=user_id,
            stroller_active_until=None,
            should_ask=False,
            is_active=False,
        )

    session = db.query(UserSession).filter(UserSession.user_id == user_id).first()
    if not session:
        session = UserSession(user_id=user_id)
        db.add(session)
        db.commit()
        db.refresh(session)

    now = datetime.now(timezone.utc)
    exp = session.stroller_active_until
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp and exp > now:
        return StrollerSessionResponse(
            user_id=user_id,
            stroller_active_until=exp,
            should_ask=False,
            is_active=True,
        )

    return StrollerSessionResponse(
        user_id=user_id,
        stroller_active_until=exp,
        should_ask=True,
        is_active=False,
    )


@router.patch("/{user_id}/session", response_model=StrollerSessionResponse)
def update_session(
    user_id: int, body: StrollerSessionUpdate, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    session = db.query(UserSession).filter(UserSession.user_id == user_id).first()
    if not session:
        session = UserSession(user_id=user_id)
        db.add(session)

    now = datetime.now(timezone.utc)
    if body.has_stroller_now:
        session.stroller_active_until = now + timedelta(minutes=STROLLER_CACHE_MINUTES)
        session.last_asked_at = now
        is_active = True
    else:
        session.stroller_active_until = None
        session.last_asked_at = now
        is_active = False

    db.commit()
    db.refresh(session)

    return StrollerSessionResponse(
        user_id=user_id,
        stroller_active_until=session.stroller_active_until,
        should_ask=False,
        is_active=is_active,
    )
