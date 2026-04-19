"""
"Otobüsü Yen!" challenge endpoint testleri.
POST /challenge/beat-the-bus
"""

import math

from backend.routers.challenge import haversine

# Sivas merkezi yakınında iki nokta (~1.4 km arayla)
ORIGIN = {"user_lat": 39.748, "user_lng": 37.014}
STOP   = {"target_stop_lat": 39.760, "target_stop_lng": 37.025}

# Gerçek mesafe ≈ 1580 m → yürüyüş süresi ≈ 18.96 dk
_DIST_M = haversine(ORIGIN["user_lat"], ORIGIN["user_lng"],
                    STOP["target_stop_lat"], STOP["target_stop_lng"])
_WALK_MIN = (_DIST_M / 1000) / 5.0 * 60


def test_challenge_walking_faster(client):
    """Yürüyüş süresi otobüsten kısaysa challenge=True, time_saved_min > 0 olmalı."""
    payload = {**ORIGIN, **STOP, "bus_eta_min": _WALK_MIN + 10}  # otobüs 10 dk daha geç
    resp = client.post("/challenge/beat-the-bus", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["challenge"] is True, "Yürüyüş daha hızsa challenge True olmalı"
    assert data["time_saved_min"] > 0, "Kazanılan süre pozitif olmalı"
    assert data["calories_burned"] is not None and data["calories_burned"] > 0, \
        "Kalori değeri pozitif olmalı"


def test_challenge_bus_faster(client):
    """Otobüs daha hızsa challenge=False, reason='bus_is_faster' olmalı."""
    payload = {**ORIGIN, **STOP, "bus_eta_min": _WALK_MIN / 2}  # otobüs çok hızlı
    resp = client.post("/challenge/beat-the-bus", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["challenge"] is False, "Otobüs daha hızsa challenge False olmalı"
    assert data["reason"] == "bus_is_faster", "Reason 'bus_is_faster' olmalı"


def test_haversine_accuracy():
    """Haversine fonksiyonu bilinen iki koordinat arasındaki mesafeyi ±5% toleransla hesaplamalı."""
    # Sivas merkezi - yaklaşık bilinen mesafe ~1580 m
    dist = haversine(39.748, 37.014, 39.760, 37.025)
    # Referans değer: online araçlarla hesaplanan ~1571 m
    reference_m = 1571
    tolerance = reference_m * 0.05
    assert abs(dist - reference_m) <= tolerance, \
        f"Haversine mesafesi {dist:.0f}m, beklenen {reference_m}±{tolerance:.0f}m"


def test_calorie_formula(client):
    """Kalori hesabı: 3.5 * weight_kg * (walking_time_min / 60) formülü doğru olmalı."""
    weight = 80.0
    payload = {**ORIGIN, **STOP, "bus_eta_min": _WALK_MIN + 5, "user_weight_kg": weight}
    resp = client.post("/challenge/beat-the-bus", json=payload)
    data = resp.json()

    expected_calories = round(3.5 * weight * (_WALK_MIN / 60), 1)
    assert abs(data["calories_burned"] - expected_calories) < 0.5, \
        f"Kalori hesabı yanlış: beklenen {expected_calories}, hesaplanan {data['calories_burned']}"


def test_walking_time_formula(client):
    """Yürüyüş süresi: (mesafe_m / 1000) / 5.0 * 60 formülü doğru olmalı."""
    payload = {**ORIGIN, **STOP, "bus_eta_min": _WALK_MIN + 5}
    resp = client.post("/challenge/beat-the-bus", json=payload)
    data = resp.json()

    expected_walk = round(_WALK_MIN, 1)
    assert abs(data["walking_time_min"] - expected_walk) < 0.5, \
        f"Yürüyüş süresi yanlış: beklenen {expected_walk}, hesaplanan {data['walking_time_min']}"


def test_challenge_missing_field(client):
    """Zorunlu alan eksikse 422 dönmeli."""
    payload = {**ORIGIN, "bus_eta_min": 20}  # target_stop_lat/lng eksik
    resp = client.post("/challenge/beat-the-bus", json=payload)
    assert resp.status_code == 422, "Eksik alan için 422 bekleniyor"
