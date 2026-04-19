"""
Erişilebilirlik uyarısı endpoint testleri.
GET /accessibility/warning
"""

from datetime import datetime, timedelta, timezone

from backend.models import UserSession


def _warning_url(user_id: int, pax: int, stop_id: str = "STP-L01-01") -> str:
    return (
        f"/accessibility/warning"
        f"?user_id={user_id}&stop_id={stop_id}&predicted_passengers_waiting={pax}"
    )


def test_warning_disabled_user_high_occupancy(client):
    """is_disabled=True ve yolcu >= 48 → accessibility_warning=True olmalı."""
    resp = client.post("/users", json={
        "username": "engelli_kullanici",
        "email": "engelli@example.com",
        "password": "sifre123",
        "is_disabled": True,
    })
    user_id = resp.json()["id"]

    r = client.get(_warning_url(user_id, 50))
    assert r.status_code == 200
    assert r.json()["accessibility_warning"] is True, \
        "Engelli kullanıcı + yoğun otobüs → uyarı verilmeli"


def test_warning_normal_user_high_occupancy(client):
    """is_disabled=False, stroller yok, yolcu >= 48 → accessibility_warning=False olmalı."""
    resp = client.post("/users", json={
        "username": "normal_kullanici",
        "email": "normal@example.com",
        "password": "sifre123",
    })
    user_id = resp.json()["id"]

    r = client.get(_warning_url(user_id, 55))
    assert r.status_code == 200
    assert r.json()["accessibility_warning"] is False, \
        "Normal kullanıcıya yüksek dolulukta uyarı verilmemeli"


def test_warning_disabled_user_low_occupancy(client):
    """is_disabled=True ama yolcu < 48 → accessibility_warning=False olmalı."""
    resp = client.post("/users", json={
        "username": "engelli2",
        "email": "engelli2@example.com",
        "password": "sifre123",
        "is_disabled": True,
    })
    user_id = resp.json()["id"]

    r = client.get(_warning_url(user_id, 20))
    assert r.status_code == 200
    assert r.json()["accessibility_warning"] is False, \
        "Engelli kullanıcı + düşük doluluk → uyarı verilmemeli"


def test_warning_active_stroller_high_occupancy(client, stroller_user):
    """Aktif stroller oturumu + yolcu >= 48 → accessibility_warning=True olmalı."""
    uid = stroller_user["id"]
    # Stroller aktif et
    client.patch(f"/users/{uid}/session", json={"has_stroller_now": True})

    r = client.get(_warning_url(uid, 50))
    assert r.status_code == 200
    assert r.json()["accessibility_warning"] is True, \
        "Aktif stroller + yoğun otobüs → uyarı verilmeli"


def test_warning_expired_stroller_high_occupancy(client, stroller_user, test_db):
    """Süresi dolmuş stroller + yolcu >= 48 → accessibility_warning=False olmalı."""
    uid = stroller_user["id"]

    # Oturumu oluştur ve süresini geçmişe al
    client.get(f"/users/{uid}/session")
    db = test_db()
    session = db.query(UserSession).filter(UserSession.user_id == uid).first()
    session.stroller_active_until = datetime.now(timezone.utc) - timedelta(hours=3)
    db.commit()
    db.close()

    r = client.get(_warning_url(uid, 55))
    assert r.status_code == 200
    assert r.json()["accessibility_warning"] is False, \
        "Süresi dolmuş stroller + yoğun otobüs → uyarı verilmemeli"


def test_occupancy_pct_calculation(client):
    """predicted_occupancy_pct = predicted_passengers_waiting / 60 * 100 formülü doğru olmalı."""
    resp = client.post("/users", json={
        "username": "doluluk_test",
        "email": "doluluk@example.com",
        "password": "sifre123",
    })
    user_id = resp.json()["id"]

    pax = 30
    r = client.get(_warning_url(user_id, pax))
    assert r.status_code == 200
    expected_pct = round(pax / 60 * 100, 1)
    assert r.json()["predicted_occupancy_pct"] == expected_pct, \
        f"Doluluk yüzdesi {expected_pct} olmalı, hesaplanan: {r.json()['predicted_occupancy_pct']}"
