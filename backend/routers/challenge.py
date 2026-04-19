import math

from fastapi import APIRouter

from backend.schemas import BeatTheBusRequest, BeatTheBusResponse

router = APIRouter()


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.post("/beat-the-bus", response_model=BeatTheBusResponse)
def beat_the_bus(body: BeatTheBusRequest):
    distance_m = haversine(
        body.user_lat, body.user_lng, body.target_stop_lat, body.target_stop_lng
    )
    walking_time_min = (distance_m / 1000) / 5.0 * 60
    calories = round(3.5 * body.user_weight_kg * (walking_time_min / 60), 1)
    time_saved = round(body.bus_eta_min - walking_time_min, 1)

    if walking_time_min < body.bus_eta_min:
        return BeatTheBusResponse(
            challenge=True,
            walking_time_min=round(walking_time_min, 1),
            bus_time_min=round(body.bus_eta_min, 1),
            time_saved_min=time_saved,
            calories_burned=calories,
            walking_distance_m=round(distance_m, 1),
        )

    return BeatTheBusResponse(
        challenge=False,
        walking_time_min=round(walking_time_min, 1),
        bus_time_min=round(body.bus_eta_min, 1),
        walking_distance_m=round(distance_m, 1),
        reason="bus_is_faster",
    )
