"""
Route shape endpoints.

Uses OSRM to snap stops to real roads and return road-following polylines.
The OSRM /route call returns both:
  - route geometry  (coordinates following roads)
  - waypoints       (each input stop snapped to its nearest road point)

So stops rendered from waypoints will sit exactly on the route line.
Results are cached in-process (one OSRM call per line per server lifetime).
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent

LINE_COLORS: Dict[str, str] = {
    "L01": "#2980B9",
    "L02": "#27AE60",
    "L03": "#E67E22",
    "L04": "#8E44AD",
    "L05": "#E74C3C",
}


_SHAPE_CACHE: Dict[str, "RouteShape"] = {}

OSRM_BASE = "https://router.project-osrm.org/route/v1/driving"
OSRM_TIMEOUT = 12


class SnappedStop(BaseModel):
    stop_id: str
    name: str
    lat: float
    lng: float
    is_terminal: bool
    is_transfer_hub: bool = False
    stop_type: str
    stop_sequence: int = 0
    line_id: str = ""
    line_name: str = ""


class RouteShape(BaseModel):
    line_id: str
    line_name: str
    color: str
    coordinates: List[List[float]]   # road-following [[lat, lng], ...]
    stops: List[SnappedStop] = []    # each stop snapped to its road point
    snapped: bool = False


class AllShapes(BaseModel):
    routes: List[RouteShape]


def _csv_path() -> Path:
    sub = _PROJECT_ROOT / "data" / "bus_stops.csv"
    return sub if sub.exists() else _PROJECT_ROOT / "bus_stops.csv"


def _load_stops() -> pd.DataFrame:
    path = _csv_path()
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)



def _osrm_route(
    waypoints: List[List[float]],
) -> Optional[Tuple[List[List[float]], List[List[float]]]]:
    """
    Call OSRM with all stop waypoints.
    Returns (road_coords, snapped_waypoints) or None on failure.
    - road_coords: dense road-following [lat, lng] list
    - snapped_waypoints: each input stop snapped to nearest road point
    """
    if len(waypoints) < 2:
        return None

    coord_str = ";".join(f"{lng},{lat}" for lat, lng in waypoints)
    url = f"{OSRM_BASE}/{coord_str}"
    params = {"overview": "full", "geometries": "geojson"}

    try:
        with httpx.Client(timeout=OSRM_TIMEOUT) as client:
            r = client.get(url, params=params)
        if r.status_code != 200:
            logger.warning("OSRM %s returned HTTP %s", url[:80], r.status_code)
            return None

        data = r.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            return None

        # Road-following geometry (flip GeoJSON [lng, lat] → [lat, lng])
        geojson_coords = data["routes"][0]["geometry"]["coordinates"]
        road_coords = [[lat, lng] for lng, lat in geojson_coords]

        # Snapped waypoints: OSRM returns where it actually placed each input point
        snapped = [
            [wp["location"][1], wp["location"][0]]   # [lat, lng]
            for wp in data.get("waypoints", [])
        ]

        return road_coords, snapped

    except Exception as exc:
        logger.warning("OSRM request failed: %s", exc)
        return None


_osrm_call_count = 0


def _build_shape(line_id: str, df: pd.DataFrame) -> RouteShape:
    if line_id in _SHAPE_CACHE:
        return _SHAPE_CACHE[line_id]

    line_df = df[df["line_id"] == line_id].sort_values("stop_sequence").reset_index(drop=True)
    if line_df.empty:
        raise HTTPException(status_code=404, detail=f"Line {line_id} not found.")

    line_name = str(line_df.iloc[0]["line_name"])
    color = LINE_COLORS.get(line_id, "#607D8B")
    raw_coords = line_df[["latitude", "longitude"]].values.tolist()

    stop_names = [str(row["stop_id"]) for _, row in line_df.iterrows()]

    # Polite delay between OSRM calls (not for cache hits)
    global _osrm_call_count
    if _osrm_call_count > 0:
        time.sleep(0.3)
    _osrm_call_count += 1
    osrm_result = _osrm_route(raw_coords)

    if osrm_result:
        road_coords, snapped_wps = osrm_result
        # Use snapped positions for stop markers (they sit on the road/route line)
        snap_positions = snapped_wps if len(snapped_wps) == len(line_df) else raw_coords
        logger.info(
            "OSRM snapped %s: %d stops → %d road pts",
            line_id, len(raw_coords), len(road_coords),
        )
        snapped = True
    else:
        logger.warning("OSRM unavailable for %s — straight-line fallback", line_id)
        road_coords = raw_coords
        snap_positions = raw_coords
        snapped = False

    stops = [
        SnappedStop(
            stop_id=str(line_df.iloc[i]["stop_id"]),
            name=stop_names[i],
            lat=round(snap_positions[i][0], 6),
            lng=round(snap_positions[i][1], 6),
            is_terminal=bool(line_df.iloc[i]["is_terminal"]),
            is_transfer_hub=bool(line_df.iloc[i].get("is_transfer_hub", False)),
            stop_type=str(line_df.iloc[i]["stop_type"]),
            stop_sequence=int(line_df.iloc[i]["stop_sequence"]),
            line_id=line_id,
            line_name=line_name,
        )
        for i in range(len(line_df))
    ]

    shape = RouteShape(
        line_id=line_id,
        line_name=line_name,
        color=color,
        coordinates=road_coords,
        stops=stops,
        snapped=snapped,
    )
    _SHAPE_CACHE[line_id] = shape
    return shape


@router.get("/all/shapes", response_model=AllShapes)
def get_all_shapes():
    df = _load_stops()
    if df.empty:
        return AllShapes(routes=[])

    routes = []
    for line_id in sorted(df["line_id"].unique()):
        try:
            routes.append(_build_shape(str(line_id), df))
        except Exception as exc:
            logger.warning("Skipping line %s: %s", line_id, exc)
    return AllShapes(routes=routes)


@router.get("/{line_id}/shape", response_model=RouteShape)
def get_route_shape(line_id: str):
    df = _load_stops()
    if df.empty:
        raise HTTPException(status_code=503, detail="Stop data unavailable.")
    return _build_shape(line_id.upper(), df)
