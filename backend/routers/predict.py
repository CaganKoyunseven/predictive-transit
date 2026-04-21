import logging
import os

from fastapi import APIRouter, Request

from backend.schemas import PredictRequest, PredictResponse
from backend.ml.predict import build_delay_features, build_crowd_features

router = APIRouter()
logger = logging.getLogger(__name__)

BUS_CAPACITY = int(os.getenv("BUS_CAPACITY", "60"))
ACCESSIBILITY_THRESHOLD = float(os.getenv("ACCESSIBILITY_THRESHOLD", "0.80"))

# Fallback values used when models are not loaded
_FALLBACK_DELAY_MIN = 8.2
_FALLBACK_PASSENGERS = 34


@router.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest, request: Request):
    models = getattr(request.app.state, "models", {})

    delay_model    = models.get("delay")
    crowd_model    = models.get("crowd")
    delay_features = models.get("delay_features")
    crowd_features = models.get("crowd_features")

    crowding_model    = models.get("crowding")
    crowding_features = models.get("crowding_features")
    crowding_le       = models.get("crowding_label_encoder")

    # If any required model artifact is missing, return conservative fallback values
    if not all([delay_model, crowd_model, delay_features, crowd_features]):
        logger.warning("One or more models not loaded — returning fallback prediction.")
        return PredictResponse(
            stop_id=req.stop_id,
            predicted_delay_min=_FALLBACK_DELAY_MIN,
            predicted_passengers_waiting=_FALLBACK_PASSENGERS,
            accessibility_warning=False,
            confidence="low",
            crowding_label="moderate",
        )

    # Step 1: predict arrival delay
    delay_df = build_delay_features(req, delay_features)
    predicted_delay = float(delay_model.predict(delay_df)[0])

    # Step 2: predict passengers waiting (uses predicted delay as input feature)
    crowd_df = build_crowd_features(req, predicted_delay, crowd_features)
    predicted_crowd = max(0, round(float(crowd_model.predict(crowd_df)[0])))

    # Confidence tier based on predicted occupancy level
    if predicted_crowd < 20:
        confidence = "high"
    elif predicted_crowd < 50:
        confidence = "medium"
    else:
        confidence = "low"

    accessibility_warning = False

    # Step 3: predict crowding label using classification model
    if all([crowding_model, crowding_features, crowding_le]):
        crowding_df  = build_crowd_features(req, predicted_delay, crowding_features)
        crowding_enc = int(crowding_model.predict(crowding_df)[0])
        crowding_label = str(crowding_le.classes_[crowding_enc])
    else:
        crowding_label = "moderate"

    return PredictResponse(
        stop_id=req.stop_id,
        predicted_delay_min=round(predicted_delay, 2),
        predicted_passengers_waiting=predicted_crowd,
        accessibility_warning=accessibility_warning,
        confidence=confidence,
        crowding_label=crowding_label,
    )
