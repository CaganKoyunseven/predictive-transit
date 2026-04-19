from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Feedback
from backend.schemas import CrowdConfirmRequest, FeedbackResponse, PostTripReviewRequest

router = APIRouter()


@router.post("/live-crowd", response_model=FeedbackResponse, status_code=201)
def live_crowd(body: CrowdConfirmRequest, db: Session = Depends(get_db)):
    entry = Feedback(
        user_id=body.user_id,
        stop_id=body.stop_id,
        trip_id=body.trip_id,
        feedback_type="crowd_confirm",
        crowd_actual=body.crowd_actual,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/post-trip", response_model=FeedbackResponse, status_code=201)
def post_trip(body: PostTripReviewRequest, db: Session = Depends(get_db)):
    entry = Feedback(
        user_id=body.user_id,
        trip_id=body.trip_id,
        stop_id=body.stop_id,
        feedback_type="post_trip_review",
        rating=body.rating,
        is_on_time=body.is_on_time,
        comment=body.comment,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
