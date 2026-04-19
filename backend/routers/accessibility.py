import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserSession
from backend.schemas import AccessibilityResponse

router = APIRouter()

BUS_CAPACITY = int(os.getenv("BUS_CAPACITY", "60"))
ACCESSIBILITY_THRESHOLD = float(os.getenv("ACCESSIBILITY_THRESHOLD", "0.80"))
# Warning fires when predicted occupancy reaches or exceeds this passenger count (default 48)
WARNING_THRESHOLD = BUS_CAPACITY * ACCESSIBILITY_THRESHOLD


@router.get("/warning", response_model=AccessibilityResponse)
def accessibility_warning(
    user_id: int,
    stop_id: str,
    predicted_passengers_waiting: int,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Check whether the user has an active stroller session
    session = db.query(UserSession).filter(UserSession.user_id == user_id).first()
    now = datetime.now(timezone.utc)
    exp = session.stroller_active_until if session else None
    if exp is not None and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    stroller_is_active = bool(exp and exp > now)

    # User qualifies for warning if they are disabled OR carrying a stroller right now
    is_eligible = user.is_disabled or stroller_is_active
    warning = is_eligible and predicted_passengers_waiting >= WARNING_THRESHOLD

    occupancy_pct = round(predicted_passengers_waiting / BUS_CAPACITY * 100, 1)

    return AccessibilityResponse(
        accessibility_warning=warning,
        message=(
            "This bus is very crowded — the wheelchair/stroller area may be full."
            if warning
            else None
        ),
        predicted_occupancy_pct=occupancy_pct,
    )
