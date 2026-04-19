"""
Tahmin endpoint testleri.
POST /predict
"""

import time

import numpy as np

from backend.main import app
from backend.tests.conftest import VALID_PREDICT_PAYLOAD


def test_predict_success(client):
    """Model yüklüyken /predict 200 ve beklenen alanları dönmeli."""
    resp = client.post("/predict", json=VALID_PREDICT_PAYLOAD)
    assert resp.status_code == 200, f"Beklenen 200, alınan {resp.status_code}: {resp.json()}"
    data = resp.json()
    assert "predicted_delay_min" in data, "predicted_delay_min alanı eksik"
    assert "predicted_passengers_waiting" in data, "predicted_passengers_waiting alanı eksik"
    assert "confidence" in data, "confidence alanı eksik"
    assert "crowding_label" in data, "crowding_label alanı eksik"
    assert data["stop_id"] == VALID_PREDICT_PAYLOAD["stop_id"]


def test_predict_fallback_no_models(client):
    """Model yokken fallback değerler dönmeli: delay=8.2, crowd=34, confidence='low'."""
    original = app.state.models
    try:
        app.state.models = {}
        resp = client.post("/predict", json=VALID_PREDICT_PAYLOAD)
        assert resp.status_code == 200, f"Fallback durumda 200 bekleniyor: {resp.json()}"
        data = resp.json()
        assert data["predicted_delay_min"] == 8.2, "Fallback gecikme 8.2 dk olmalı"
        assert data["predicted_passengers_waiting"] == 34, "Fallback yolcu sayısı 34 olmalı"
        assert data["confidence"] == "low", "Fallback confidence 'low' olmalı"
    finally:
        app.state.models = original


def test_predict_missing_required_field(client):
    """Zorunlu alan eksikse 422 dönmeli."""
    payload = dict(VALID_PREDICT_PAYLOAD)
    del payload["stop_sequence"]  # zorunlu alan
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 422, "Eksik zorunlu alan için 422 bekleniyor"


def test_predict_invalid_traffic_level(client):
    """Geçersiz traffic_level değeri 422 dönmeli."""
    payload = {**VALID_PREDICT_PAYLOAD, "traffic_level": "medium"}  # geçersiz
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 422, "Geçersiz traffic_level için 422 bekleniyor"


def test_predict_invalid_weather_condition(client):
    """Geçersiz weather_condition değeri 422 dönmeli."""
    payload = {**VALID_PREDICT_PAYLOAD, "weather_condition": "tornado"}  # geçersiz
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 422, "Geçersiz weather_condition için 422 bekleniyor"


def test_predict_accessibility_warning_threshold(client, mock_models):
    """predicted_passengers_waiting >= 48 olduğunda accessibility_warning True olmalı."""
    mock_models["crowd"].predict.return_value = np.array([50.0])

    resp = client.post("/predict", json=VALID_PREDICT_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["predicted_passengers_waiting"] == 50, "Mock crowd tahmini 50 olmalı"
    assert data["accessibility_warning"] is True, "50 yolcu ile erişilebilirlik uyarısı aktif olmalı"


def test_predict_response_time(client):
    """Tahmin yanıt süresi 200ms'nin altında olmalı."""
    start = time.time()
    resp = client.post("/predict", json=VALID_PREDICT_PAYLOAD)
    elapsed_ms = (time.time() - start) * 1000

    assert resp.status_code == 200
    assert elapsed_ms < 200, f"Yanıt süresi çok uzun: {elapsed_ms:.1f}ms (limit: 200ms)"
