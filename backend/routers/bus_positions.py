"""
Simulated bus positions for the live map.

Since there is no real-time GPS feed, positions are derived from
bus_trips.csv schedules: for the current time-of-day, find trips that
would be in-progress and interpolate each bus between consecutive stops.
"""

import logging
import math
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel
from backend.routers.route_shapes import _SHAPE_CACHE

router = APIRouter()
logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent

LINE_COLORS = {
    "L01": "#2980B9",
    "L02": "#27AE60",
    "L03": "#E67E22",
    "L04": "#8E44AD",
    "L05": "#E74C3C",
}


def _occupancy_label(pct: float) -> str:
    if pct <= 30:
        return "Boş"
    if pct <= 60:
        return "Orta"
    if pct <= 80:
        return "Kalabalık"
    return "Çok Kalabalık"


def _occupancy_color(pct: float) -> str:
    if pct <= 30:
        return "#27AE60"
    if pct <= 60:
        return "#F1C40F"
    if pct <= 80:
        return "#E67E22"
    return "#E74C3C"


def _csv(name: str) -> Path:
    sub = _PROJECT_ROOT / "data" / name
    return sub if sub.exists() else _PROJECT_ROOT / name


def _interpolate(lat1: float, lng1: float, lat2: float, lng2: float, t: float):
    return lat1 + (lat2 - lat1) * t, lng1 + (lng2 - lng1) * t


def _point_along_road(road_coords: list, progress: float):
    """Find lat/lng at `progress` [0,1] fraction along a road polyline."""
    if len(road_coords) < 2:
        return road_coords[0][0], road_coords[0][1]

    segs = []
    total = 0.0
    for i in range(len(road_coords) - 1):
        lat1, lng1 = road_coords[i][0], road_coords[i][1]
        lat2, lng2 = road_coords[i + 1][0], road_coords[i + 1][1]
        d = math.sqrt((lat2 - lat1) ** 2 + (lng2 - lng1) ** 2)
        segs.append(d)
        total += d

    target = progress * total
    cum = 0.0
    for i, d in enumerate(segs):
        if cum + d >= target:
            t = (target - cum) / d if d > 0 else 0.0
            lat1, lng1 = road_coords[i][0], road_coords[i][1]
            lat2, lng2 = road_coords[i + 1][0], road_coords[i + 1][1]
            return lat1 + (lat2 - lat1) * t, lng1 + (lng2 - lng1) * t
        cum += d

    return road_coords[-1][0], road_coords[-1][1]


class BusPosition(BaseModel):
    bus_id: str
    line_id: str
    line_name: str
    latitude: float
    longitude: float
    next_stop_id: str
    delay_min: float
    occupancy_pct: float
    occupancy_label: str
    occupancy_color: str
    color: str


@router.get("", response_model=List[BusPosition])
def get_bus_positions():
    stops_df = pd.read_csv(_csv("bus_stops.csv")).sort_values(["line_id", "stop_sequence"])
    trips_df = pd.read_csv(_csv("bus_trips.csv"))

    now = datetime.now()
    now_minutes = now.hour * 60 + now.minute

    results: List[BusPosition] = []
    bus_counter = 0

    for line_id, line_stops in stops_df.groupby("line_id"):
        line_stops = line_stops.reset_index(drop=True)
        line_trips = trips_df[trips_df["line_id"] == line_id].copy()
        if line_trips.empty or len(line_stops) < 2:
            continue

        line_name = line_stops.iloc[0]["line_name"]
        line_color = LINE_COLORS.get(str(line_id), "#607D8B")
        num_stops = len(line_stops)

        # Parse departure times → minutes since midnight
        line_trips["dep_dt"] = pd.to_datetime(line_trips["planned_departure"])
        line_trips["dep_min"] = line_trips["dep_dt"].dt.hour * 60 + line_trips["dep_dt"].dt.minute
        line_trips["dur_min"] = line_trips["planned_duration_min"]

        # Find trips in-progress right now (by time-of-day pattern)
        in_progress = line_trips[
            (line_trips["dep_min"] <= now_minutes) &
            (line_trips["dep_min"] + line_trips["dur_min"] >= now_minutes)
        ].head(3)

        if in_progress.empty:
            # Fall back to the closest upcoming trip
            upcoming = line_trips[line_trips["dep_min"] > now_minutes].head(1)
            in_progress = upcoming if not upcoming.empty else line_trips.head(1)

        for _, trip in in_progress.iterrows():
            bus_counter += 1
            elapsed = max(0, now_minutes - trip["dep_min"])
            progress = min(0.99, elapsed / max(1, trip["dur_min"]))

            # Map progress → position between stops
            seg_len = 1.0 / (num_stops - 1)
            seg_idx = min(num_stops - 2, int(progress / seg_len))
            seg_t = (progress - seg_idx * seg_len) / seg_len

            s2 = line_stops.iloc[min(seg_idx + 1, num_stops - 1)]

            # Use OSRM road polyline if cached, else fall back to straight line
            shape = _SHAPE_CACHE.get(str(line_id))
            if shape and shape.coordinates:
                lat, lng = _point_along_road(shape.coordinates, progress)
            else:
                s1 = line_stops.iloc[seg_idx]
                lat, lng = _interpolate(
                    float(s1["latitude"]), float(s1["longitude"]),
                    float(s2["latitude"]), float(s2["longitude"]),
                    seg_t,
                )

            occ = float(trip["avg_occupancy_pct"])
            delay = float(trip["departure_delay_min"])

            results.append(BusPosition(
                bus_id=f"{line_id}-{bus_counter}",
                line_id=str(line_id),
                line_name=line_name,
                latitude=round(lat, 6),
                longitude=round(lng, 6),
                next_stop_id=str(s2["stop_id"]),
                delay_min=round(delay, 1),
                occupancy_pct=round(occ, 1),
                occupancy_label=_occupancy_label(occ),
                occupancy_color=_occupancy_color(occ),
                color=line_color,
            ))

    return results
