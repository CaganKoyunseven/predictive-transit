"""
Real-time weather endpoint for Sivas via Open-Meteo (no API key required).

API: https://api.open-meteo.com/v1/forecast
     ?latitude=39.75&longitude=37.01
     &current=temperature_2m,precipitation,windspeed_10m,weather_code

WMO weather codes → our ML vocabulary (clear/cloudy/rain/snow/fog/wind).
Server-side 5-minute cache to avoid hammering the free API.
"""

import logging
import time

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=39.75&longitude=37.01"
    "&current=temperature_2m,precipitation,windspeed_10m,weather_code"
)
TIMEOUT = 6
CACHE_TTL = 300   # 5 minutes

_cache: dict = {}


class WeatherResponse(BaseModel):
    weather_condition: str    # clear | cloudy | rain | snow | fog | wind
    temperature_c: float
    precipitation_mm: float
    wind_speed_kmh: float
    description: str
    source: str               # "open-meteo" | "fallback"


# WMO code → our condition string
# https://open-meteo.com/en/docs#weathervariables
def _wmo_to_condition(code: int, wind_kmh: float) -> str:
    if code == 0:
        return "clear"
    if code in (1, 2, 3):
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):   # thunderstorm
        return "rain"
    if wind_kmh >= 40:
        return "wind"
    return "clear"


_WMO_DESCRIPTION = {
    0: "Açık", 1: "Az bulutlu", 2: "Parçalı bulutlu", 3: "Kapalı",
    45: "Sisli", 48: "Kırağılı sis",
    51: "Hafif çisenti", 53: "Çisenti", 55: "Yoğun çisenti",
    61: "Hafif yağmur", 63: "Yağmur", 65: "Yoğun yağmur",
    71: "Hafif kar", 73: "Kar", 75: "Yoğun kar",
    80: "Sağanak", 81: "Kuvvetli sağanak", 82: "Çok kuvvetli sağanak",
    95: "Gök gürültülü fırtına", 96: "Dolu ile fırtına",
}


def _fallback() -> WeatherResponse:
    return WeatherResponse(
        weather_condition="clear",
        temperature_c=15.0,
        precipitation_mm=0.0,
        wind_speed_kmh=10.0,
        description="Hava durumu alınamadı — varsayılan değerler",
        source="fallback",
    )


@router.get("", response_model=WeatherResponse)
def get_weather():
    now = time.time()
    if _cache.get("ts") and now - _cache["ts"] < CACHE_TTL and "data" in _cache:
        return _cache["data"]

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.get(OPEN_METEO_URL)
        r.raise_for_status()
        data = r.json()["current"]

        code = int(data["weather_code"])
        temp = round(float(data["temperature_2m"]), 1)
        precip = round(float(data["precipitation"]), 1)
        wind = round(float(data["windspeed_10m"]), 1)

        condition = _wmo_to_condition(code, wind)
        desc_tr = _WMO_DESCRIPTION.get(code, "Bilinmiyor")
        description = f"{desc_tr}, {temp}°C"

        result = WeatherResponse(
            weather_condition=condition,
            temperature_c=temp,
            precipitation_mm=precip,
            wind_speed_kmh=wind,
            description=description,
            source="open-meteo",
        )
        _cache["ts"] = now
        _cache["data"] = result
        logger.info("Weather: %s %s°C (WMO %s)", condition, temp, code)
        return result

    except Exception as exc:
        logger.warning("Open-Meteo request failed: %s", exc)
        return _fallback()
