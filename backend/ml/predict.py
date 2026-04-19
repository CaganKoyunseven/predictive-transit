"""
Predictive Transit — ML Predict Helpers
Router'lardan kullanılan yardımcı fonksiyonlar.
"""

import pandas as pd

# --- Encoding maps (routers/predict.py ile tutarlı) ---
TRAFFIC_MAP = {"low": 0, "moderate": 1, "high": 2, "congested": 3}
WEATHER_MAP = {"clear": 0, "cloudy": 1, "rain": 2, "fog": 3, "wind": 4, "snow": 5}
STOP_TYPE_MAP = {
    "regular": 0, "terminal": 1, "transfer_hub": 2,
    "university": 3, "hospital": 4, "market": 5, "residential": 6
}
TIME_BUCKET_MAP = {
    "early_morning": 0, "morning_peak": 1, "midday": 2,
    "evening_peak": 3, "evening": 4, "night": 5
}


def _hour_to_time_bucket_enc(hour: int) -> int:
    """Saat değerinden time_bucket_enc üret (eğitim verisindeki aralıklarla uyumlu)."""
    if 5 <= hour < 7:
        return TIME_BUCKET_MAP["early_morning"]   # 0
    elif 7 <= hour < 9:
        return TIME_BUCKET_MAP["morning_peak"]    # 1
    elif 9 <= hour < 16:
        return TIME_BUCKET_MAP["midday"]          # 2
    elif 16 <= hour < 19:
        return TIME_BUCKET_MAP["evening_peak"]    # 3
    elif 19 <= hour < 22:
        return TIME_BUCKET_MAP["evening"]         # 4
    else:
        return TIME_BUCKET_MAP["night"]           # 5


def build_delay_features(req, feature_list: list) -> pd.DataFrame:
    """
    PredictRequest'ten gecikme modeli için DataFrame oluşturur.

    Parameters
    ----------
    req         : schemas.PredictRequest
    feature_list: app.state.models["delay_features"] — eğitim sırasındaki sıra

    Returns
    -------
    pd.DataFrame — tek satır, feature_list sırasında
    """
    row = {
        "hour_of_day":          req.hour_of_day,
        "day_of_week":          req.day_of_week,
        "is_weekend":           int(req.is_weekend),
        "stop_sequence":        req.stop_sequence,
        "cumulative_delay_min": req.cumulative_delay_min,
        "speed_factor":         req.speed_factor,
        "traffic_level_enc":    TRAFFIC_MAP.get(req.traffic_level, 1),
        "weather_enc":          WEATHER_MAP.get(req.weather_condition, 0),
        "temperature_c":        req.temperature_c,
        "precipitation_mm":     req.precipitation_mm,
        "wind_speed_kmh":       req.wind_speed_kmh,
        "is_terminal":          int(req.is_terminal),
        "is_transfer_hub":      int(req.is_transfer_hub),
        "stop_type_enc":        STOP_TYPE_MAP.get(req.stop_type, 0),
        "departure_delay_min":  req.departure_delay_min,
        "minutes_to_next_bus":  req.minutes_to_next_bus,
    }
    # feature_list sırasına göre döndür; eksik feature varsa 0 ile doldur
    data = {f: row.get(f, 0) for f in feature_list}
    return pd.DataFrame([data])


def build_crowd_features(req, predicted_delay: float, feature_list: list) -> pd.DataFrame:
    """
    PredictRequest'ten kalabalık modeli için DataFrame oluşturur.

    Parameters
    ----------
    req             : schemas.PredictRequest
    predicted_delay : delay modelinden gelen tahmin (delay_min feature'ı olarak kullanılır)
    feature_list    : app.state.models["crowd_features"] — eğitim sırasındaki sıra

    Fallback değerler (eğitim verisinde merge ile gelen; gerçek zamanda bilinmiyor):
        avg_passengers_waiting    = 34.0
        transit_delay_risk        = 0.3
        passenger_demand_multiplier = 1.0
        time_bucket_enc           = saat'ten hesaplanır (yoksa 2 = midday)

    Returns
    -------
    pd.DataFrame — tek satır, feature_list sırasında
    """
    row = {
        "hour_of_day":                  req.hour_of_day,
        "day_of_week":                  req.day_of_week,
        "is_weekend":                   int(req.is_weekend),
        "stop_type_enc":                STOP_TYPE_MAP.get(req.stop_type, 0),
        "minutes_to_next_bus":          req.minutes_to_next_bus,
        "weather_enc":                  WEATHER_MAP.get(req.weather_condition, 0),
        "avg_passengers_waiting":       34.0,
        "time_bucket_enc":              _hour_to_time_bucket_enc(req.hour_of_day),
        "delay_min":                    predicted_delay,
        "transit_delay_risk":           0.3,
        "passenger_demand_multiplier":  1.0,
    }
    # feature_list sırasına göre döndür; eksik feature varsa 0 ile doldur
    data = {f: row.get(f, 0) for f in feature_list}
    return pd.DataFrame([data])
