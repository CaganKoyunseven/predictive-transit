import logging
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd
from fastapi import APIRouter, HTTPException

from backend.schemas import StopResponse, UpcomingBus, UpcomingResponse

router = APIRouter()
logger = logging.getLogger(__name__)

LINE_COLORS = {
    "L01": "#2980B9",
    "L02": "#27AE60",
    "L03": "#E67E22",
    "L04": "#8E44AD",
    "L05": "#E74C3C",
}


def _occupancy_color(pct: float) -> str:
    if pct <= 30:
        return "#27AE60"
    if pct <= 60:
        return "#F1C40F"
    if pct <= 80:
        return "#E67E22"
    return "#E74C3C"

# CSV is expected at <project_root>/data/bus_stops.csv.
# Fall back to <project_root>/bus_stops.csv when the data/ sub-directory does not exist
# (matches the layout used during ML training).
_PROJECT_ROOT = Path(__file__).parent.parent.parent


def _csv_path(name: str = "bus_stops.csv") -> Path:
    sub = _PROJECT_ROOT / "data" / name
    if sub.exists():
        return sub
    return _PROJECT_ROOT / name


def _load_stops() -> pd.DataFrame:
    path = _csv_path("bus_stops.csv")
    if not path.exists():
        logger.warning("bus_stops.csv not found at %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path)

    # Join average occupancy per line from bus_trips.csv
    trips_path = _csv_path("bus_trips.csv")
    if trips_path.exists():
        trips = pd.read_csv(trips_path)
        occ = trips.groupby("line_id")["avg_occupancy_pct"].mean().reset_index()
        occ.columns = ["line_id", "occupancy_pct"]
        df = df.merge(occ, on="line_id", how="left")
        df["occupancy_color"] = df["occupancy_pct"].apply(
            lambda x: _occupancy_color(x) if pd.notna(x) else "#3b82f6"
        )
    else:
        df["occupancy_pct"] = None
        df["occupancy_color"] = "#3b82f6"

    return df


@router.get("", response_model=List[StopResponse])
def list_stops():
    df = _load_stops()
    if df.empty:
        return []
    return df.to_dict(orient="records")


@router.get("/{stop_id}", response_model=StopResponse)
def get_stop(stop_id: str):
    df = _load_stops()
    if df.empty:
        raise HTTPException(status_code=404, detail="Stop not found.")

    row = df[df["stop_id"] == stop_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="Stop not found.")

    return row.iloc[0].to_dict()


@router.get("/{stop_id}/upcoming", response_model=UpcomingResponse)
def get_upcoming(stop_id: str):
    """
    Returns the next 3 simulated bus arrivals at a stop.
    Times are derived from bus_trips.csv schedule patterns.
    """
    stops_df = _load_stops()
    if stops_df.empty:
        raise HTTPException(status_code=404, detail="Stop not found.")

    row = stops_df[stops_df["stop_id"] == stop_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="Stop not found.")

    line_id = str(row.iloc[0]["line_id"])
    stop_seq = int(row.iloc[0]["stop_sequence"])

    trips_path = _csv_path("bus_trips.csv")
    if not trips_path.exists():
        return UpcomingResponse(stop_id=stop_id, buses=[])

    trips = pd.read_csv(trips_path)
    line_trips = trips[trips["line_id"] == line_id].copy()
    if line_trips.empty:
        return UpcomingResponse(stop_id=stop_id, buses=[])

    now = datetime.now()
    now_min = now.hour * 60 + now.minute

    line_trips["dep_dt"] = pd.to_datetime(line_trips["planned_departure"])
    line_trips["dep_min"] = line_trips["dep_dt"].dt.hour * 60 + line_trips["dep_dt"].dt.minute
    line_trips["dur_min"] = line_trips["planned_duration_min"]

    # Estimate arrival at this stop: proportional to stop_sequence / num_stops
    num_stops = int(line_trips["num_stops"].iloc[0]) if "num_stops" in line_trips.columns else 10
    stop_ratio = min(1.0, stop_seq / max(1, num_stops))
    line_trips["arr_min"] = line_trips["dep_min"] + line_trips["dur_min"] * stop_ratio

    # Find upcoming arrivals
    upcoming = line_trips[line_trips["arr_min"] > now_min].sort_values("arr_min").head(3)
    if upcoming.empty:
        # Wrap around: buses from start of next day
        upcoming = line_trips.sort_values("arr_min").head(3)

    line_name = str(line_trips.iloc[0]["line_name"])
    color = LINE_COLORS.get(line_id, "#607D8B")

    buses = []
    for _, t in upcoming.iterrows():
        minutes_away = max(1, int(round(t["arr_min"] - now_min)))
        buses.append(UpcomingBus(
            line_id=line_id,
            line_name=line_name,
            color=color,
            minutes_away=minutes_away,
            delay_min=round(float(t["departure_delay_min"]), 1),
        ))

    return UpcomingResponse(stop_id=stop_id, buses=buses)
