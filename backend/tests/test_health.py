"""
Sağlık ve kök endpoint testleri.
GET / · GET /health
"""

from backend.main import app


def test_api_info_returns_200(client):
    """GET /api-info → 200 ve 'app' alanı içeren yanıt dönmeli."""
    resp = client.get("/api-info")
    assert resp.status_code == 200, f"GET /api-info için 200 bekleniyor: {resp.status_code}"
    assert "app" in resp.json(), "/api-info response'da 'app' alanı olmalı"


def test_health_returns_200(client):
    """GET /health → 200 ve 'status' alanı içeren yanıt dönmeli."""
    resp = client.get("/health")
    assert resp.status_code == 200, f"GET /health için 200 bekleniyor: {resp.status_code}"
    assert "status" in resp.json(), "Health response'da 'status' alanı olmalı"


def test_health_active_with_models(client):
    """Modeller yüklüyken predict_service='active' olmalı."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["predict_service"] == "active", \
        f"Modeller yüklüyken predict_service 'active' olmalı, alınan: {data['predict_service']}"


def test_health_degraded_without_models(client):
    """Modeller yokken predict_service='degraded' olmalı."""
    original = app.state.models
    try:
        app.state.models = {}
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["predict_service"] == "degraded", \
            f"Model yokken predict_service 'degraded' olmalı, alınan: {data['predict_service']}"
    finally:
        app.state.models = original
