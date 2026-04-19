from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ── User ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    is_disabled: bool = False
    has_stroller_profile: bool = False


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    is_disabled: Optional[bool] = None
    has_stroller_profile: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_disabled: bool
    has_stroller_profile: bool
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Session ───────────────────────────────────────────────────────────────────

class StrollerSessionUpdate(BaseModel):
    has_stroller_now: bool


class StrollerSessionResponse(BaseModel):
    user_id: int
    stroller_active_until: Optional[datetime]
    should_ask: bool
    is_active: bool

    model_config = {"from_attributes": True}


# ── Predict ───────────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    stop_id: str
    trip_id: Optional[str] = None
    stop_sequence: int = Field(..., ge=1)
    hour_of_day: int = Field(..., ge=0, le=23)
    day_of_week: int = Field(..., ge=0, le=6)
    is_weekend: bool = False
    cumulative_delay_min: float = 0.0
    speed_factor: float = Field(..., ge=0.0, le=1.0)
    traffic_level: str = Field(..., pattern="^(low|moderate|high|congested)$")
    weather_condition: str = Field(..., pattern="^(clear|cloudy|rain|snow|fog|wind)$")
    temperature_c: float
    precipitation_mm: float = 0.0
    wind_speed_kmh: float = 0.0
    is_terminal: bool = False
    is_transfer_hub: bool = False
    stop_type: str = "regular"
    departure_delay_min: float = 0.0
    minutes_to_next_bus: float = 15.0


class PredictResponse(BaseModel):
    stop_id: str
    predicted_delay_min: float
    predicted_passengers_waiting: int
    accessibility_warning: bool = False
    confidence: str = "medium"
    crowding_label: str = "moderate"


# ── Accessibility ─────────────────────────────────────────────────────────────

class AccessibilityRequest(BaseModel):
    user_id: int
    stop_id: str
    trip_id: Optional[str] = None
    predicted_passengers_waiting: int


class AccessibilityResponse(BaseModel):
    accessibility_warning: bool
    message: Optional[str] = None
    predicted_occupancy_pct: float


# ── Beat the Bus ──────────────────────────────────────────────────────────────

class BeatTheBusRequest(BaseModel):
    user_lat: float
    user_lng: float
    target_stop_lat: float
    target_stop_lng: float
    bus_eta_min: float
    user_weight_kg: float = 70.0


class BeatTheBusResponse(BaseModel):
    challenge: bool
    walking_time_min: Optional[float] = None
    bus_time_min: Optional[float] = None
    time_saved_min: Optional[float] = None
    calories_burned: Optional[float] = None
    walking_distance_m: Optional[float] = None
    reason: Optional[str] = None


# ── Feedback ──────────────────────────────────────────────────────────────────

class CrowdConfirmRequest(BaseModel):
    user_id: int
    stop_id: str
    trip_id: Optional[str] = None
    crowd_actual: str = Field(..., pattern="^(empty|as_predicted|crowded)$")


class PostTripReviewRequest(BaseModel):
    user_id: int
    trip_id: Optional[str] = None
    stop_id: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    is_on_time: Optional[bool] = None
    comment: Optional[str] = Field(None, max_length=500)


class FeedbackResponse(BaseModel):
    id: int
    feedback_type: str
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Stop ──────────────────────────────────────────────────────────────────────

class StopResponse(BaseModel):
    stop_id: str
    line_id: str
    line_name: str
    stop_sequence: int
    latitude: float
    longitude: float
    stop_type: str
    is_terminal: bool
    is_transfer_hub: bool
    occupancy_pct: Optional[float] = None
    occupancy_color: Optional[str] = None


class UpcomingBus(BaseModel):
    line_id: str
    line_name: str
    color: str
    minutes_away: int
    delay_min: float


class UpcomingResponse(BaseModel):
    stop_id: str
    buses: list[UpcomingBus]
