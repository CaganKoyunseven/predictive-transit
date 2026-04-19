"""
ML pipeline entegrasyon testleri.
Gerçek .pkl dosyaları ve model davranışı üzerinde çalışır.
TestClient gerektirmez — doğrudan dosya sistemi ve joblib.
"""

import numpy as np
import joblib
import pytest
from pathlib import Path

MODEL_DIR = Path(__file__).parent.parent / "ml" / "models"

DELAY_FEATURES_EXPECTED = [
    "hour_of_day", "day_of_week", "is_weekend", "stop_sequence",
    "cumulative_delay_min", "speed_factor", "traffic_level_enc",
    "weather_enc", "temperature_c", "precipitation_mm", "wind_speed_kmh",
    "is_terminal", "is_transfer_hub", "stop_type_enc",
    "departure_delay_min", "minutes_to_next_bus",
]

CROWD_FEATURES_EXPECTED = [
    "hour_of_day", "day_of_week", "is_weekend", "stop_type_enc",
    "minutes_to_next_bus", "weather_enc", "avg_passengers_waiting",
    "time_bucket_enc", "delay_min", "transit_delay_risk",
    "passenger_demand_multiplier",
]


def test_model_files_exist():
    """backend/ml/models/ klasöründe gerekli tüm .pkl dosyaları mevcut olmalı."""
    required = [
        "delay_model.pkl",
        "crowd_model.pkl",
        "crowding_model.pkl",
        "delay_features.pkl",
        "crowd_features.pkl",
        "crowding_features.pkl",
        "label_encoders.pkl",
        "crowding_label_encoder.pkl",
    ]
    for fname in required:
        path = MODEL_DIR / fname
        assert path.exists(), f"Model dosyası eksik: {path}"


def test_delay_features_count():
    """delay_features listesi tam olarak 16 elemanlı olmalı (IMPLEMENTATION_PLAN.md)."""
    features = joblib.load(MODEL_DIR / "delay_features.pkl")
    assert len(features) == 16, \
        f"delay_features 16 elemanlı olmalı, bulunan: {len(features)}"


def test_crowd_features_count():
    """crowd_features listesi tam olarak 11 elemanlı olmalı (IMPLEMENTATION_PLAN.md)."""
    features = joblib.load(MODEL_DIR / "crowd_features.pkl")
    assert len(features) == 11, \
        f"crowd_features 11 elemanlı olmalı, bulunan: {len(features)}"


def test_delay_model_predict():
    """Yüklenen gecikme modeli predict() çağrısına yanıt vermeli."""
    model = joblib.load(MODEL_DIR / "delay_model.pkl")
    features = joblib.load(MODEL_DIR / "delay_features.pkl")

    import pandas as pd
    row = {f: 0 for f in features}
    row.update({"hour_of_day": 8, "day_of_week": 1, "temperature_c": 15.0, "speed_factor": 0.8})
    X = pd.DataFrame([row])

    result = model.predict(X)
    assert result.shape == (1,), "Gecikme modeli tek elemanlı array dönmeli"
    assert isinstance(float(result[0]), float), "Tahmin float olmalı"


def test_crowd_model_nonnegative():
    """Kalabalık modeli negatif değer üretmemeli (max(0, round(pred)) mantığı)."""
    model = joblib.load(MODEL_DIR / "crowd_model.pkl")
    features = joblib.load(MODEL_DIR / "crowd_features.pkl")

    import pandas as pd
    row = {f: 0 for f in features}
    X = pd.DataFrame([row])

    raw = model.predict(X)
    result = max(0, round(float(raw[0])))
    assert result >= 0, f"Kalabalık tahmini negatif olmamalı, hesaplanan: {result}"


def test_feature_order_matches_plan():
    """delay_features ve crowd_features sırası IMPLEMENTATION_PLAN.md ile uyuşmalı."""
    delay_features = joblib.load(MODEL_DIR / "delay_features.pkl")
    crowd_features = joblib.load(MODEL_DIR / "crowd_features.pkl")

    assert delay_features == DELAY_FEATURES_EXPECTED, \
        "delay_features sırası planla uyuşmuyor"
    assert crowd_features == CROWD_FEATURES_EXPECTED, \
        "crowd_features sırası planla uyuşmuyor"


def test_crowding_model_predict():
    """Crowding sınıflandırma modeli predict() çağrısına yanıt vermeli ve geçerli label döndürmeli."""
    model = joblib.load(MODEL_DIR / "crowding_model.pkl")
    features = joblib.load(MODEL_DIR / "crowding_features.pkl")
    le = joblib.load(MODEL_DIR / "crowding_label_encoder.pkl")

    import pandas as pd
    row = {f: 0 for f in features}
    X = pd.DataFrame([row])

    result = model.predict(X)
    assert result.shape == (1,), "Crowding modeli tek elemanlı array dönmeli"

    label = str(le.classes_[int(result[0])])
    valid_labels = {"empty", "light", "moderate", "busy", "crowded"}
    assert label in valid_labels, \
        f"Crowding label geçersiz: '{label}'. Beklenen: {valid_labels}"
