"""
Durak endpoint testleri.
GET /stops · GET /stops/{stop_id} · GET /stops/{stop_id}/upcoming
"""

import pytest
from unittest.mock import patch


# CSV'den bilinen geçerli bir durak id'si
KNOWN_STOP_ID = "STP-L01-01"


def test_list_stops_not_empty(client):
    """GET /stops boş olmayan bir liste dönmeli."""
    resp = client.get("/stops")
    assert resp.status_code == 200, f"GET /stops başarısız: {resp.status_code}"
    data = resp.json()
    assert isinstance(data, list), "Response bir liste olmalı"
    assert len(data) > 0, "Durak listesi boş olmamalı"


def test_list_stops_required_fields(client):
    """Her durak item'ında stop_id, latitude, longitude alanları olmalı."""
    resp = client.get("/stops")
    assert resp.status_code == 200
    for stop in resp.json():
        assert "stop_id" in stop, f"stop_id eksik: {stop}"
        assert "latitude" in stop, f"latitude eksik: {stop}"
        assert "longitude" in stop, f"longitude eksik: {stop}"


def test_get_stop_success(client):
    """Mevcut stop_id ile GET isteği 200 ve durak bilgisi dönmeli."""
    resp = client.get(f"/stops/{KNOWN_STOP_ID}")
    assert resp.status_code == 200, f"Mevcut durak için 200 bekleniyor: {resp.status_code}"
    data = resp.json()
    assert data["stop_id"] == KNOWN_STOP_ID, "stop_id eşleşmeli"
    assert "latitude" in data
    assert "longitude" in data


def test_get_stop_not_found(client):
    """Olmayan stop_id ile GET isteği 404 dönmeli."""
    resp = client.get("/stops/OLMAYAN-DURAK-999")
    assert resp.status_code == 404, "Olmayan durak için 404 bekleniyor"


def test_get_upcoming_returns_list(client):
    """GET /stops/{id}/upcoming liste dönmeli, maksimum 3 item olmalı."""
    resp = client.get(f"/stops/{KNOWN_STOP_ID}/upcoming")
    assert resp.status_code == 200, f"Upcoming endpoint başarısız: {resp.status_code}"
    data = resp.json()
    assert "buses" in data, "Response'da 'buses' alanı olmalı"
    assert isinstance(data["buses"], list), "buses bir liste olmalı"
    assert len(data["buses"]) <= 3, f"Maksimum 3 otobüs dönmeli, dönen: {len(data['buses'])}"


def test_get_upcoming_required_fields(client):
    """Upcoming her item'ında line_id ve minutes_away alanları olmalı."""
    resp = client.get(f"/stops/{KNOWN_STOP_ID}/upcoming")
    assert resp.status_code == 200
    buses = resp.json().get("buses", [])
    for bus in buses:
        assert "line_id" in bus, f"line_id eksik: {bus}"
        assert "minutes_away" in bus, f"minutes_away eksik: {bus}"
