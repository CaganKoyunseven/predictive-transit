"""
Bebek arabası oturum endpoint testleri.
GET /users/{id}/session · PATCH /users/{id}/session
"""

from datetime import datetime, timedelta, timezone

from backend.models import UserSession


def test_session_no_stroller_profile(client, test_user):
    """has_stroller_profile=False olan kullanıcıda should_ask her zaman False olmalı."""
    resp = client.get(f"/users/{test_user['id']}/session")
    assert resp.status_code == 200
    data = resp.json()
    assert data["should_ask"] is False, "Bebek arabası profili olmayan kullanıcıya soru sorulmamalı"
    assert data["is_active"] is False


def test_session_stroller_profile_no_session(client, stroller_user):
    """has_stroller_profile=True ama hiç oturum kaydı yok → should_ask=True olmalı."""
    resp = client.get(f"/users/{stroller_user['id']}/session")
    assert resp.status_code == 200
    data = resp.json()
    assert data["should_ask"] is True, "Aktif oturumu olmayan stroller kullanıcısına soru sorulmalı"
    assert data["is_active"] is False


def test_session_active_stroller(client, stroller_user):
    """PATCH ile stroller aktif edilince GET should_ask=False, is_active=True dönmeli."""
    uid = stroller_user["id"]
    # Stroller aktif et
    patch_resp = client.patch(f"/users/{uid}/session", json={"has_stroller_now": True})
    assert patch_resp.status_code == 200

    get_resp = client.get(f"/users/{uid}/session")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["should_ask"] is False, "Aktif stroller oturumunda should_ask False olmalı"
    assert data["is_active"] is True, "Aktif stroller oturumunda is_active True olmalı"


def test_session_expired_stroller(client, stroller_user, test_db):
    """Süresi dolmuş stroller_active_until ile GET should_ask=True dönmeli."""
    uid = stroller_user["id"]

    # Önce oturum oluştur (GET tetikler)
    client.get(f"/users/{uid}/session")

    # DB'de stroller_active_until'ı geçmişe al
    db = test_db()
    session = db.query(UserSession).filter(UserSession.user_id == uid).first()
    session.stroller_active_until = datetime.now(timezone.utc) - timedelta(hours=2)
    db.commit()
    db.close()

    resp = client.get(f"/users/{uid}/session")
    assert resp.status_code == 200
    data = resp.json()
    assert data["should_ask"] is True, "Süresi dolmuş oturumda should_ask True olmalı"
    assert data["is_active"] is False, "Süresi dolmuş oturumda is_active False olmalı"


def test_patch_session_stroller_true(client, stroller_user):
    """has_stroller_now=True → stroller_active_until yaklaşık 90 dakika sonra olmalı."""
    uid = stroller_user["id"]
    before = datetime.now(timezone.utc)

    resp = client.patch(f"/users/{uid}/session", json={"has_stroller_now": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is True, "Stroller aktif edilince is_active True olmalı"

    # stroller_active_until 85-95 dakika arası olmalı
    active_until = datetime.fromisoformat(data["stroller_active_until"])
    if active_until.tzinfo is None:
        active_until = active_until.replace(tzinfo=timezone.utc)
    diff_min = (active_until - before).total_seconds() / 60
    assert 85 <= diff_min <= 95, f"Cache süresi 90 dakika olmalı, hesaplanan: {diff_min:.1f} dk"


def test_patch_session_stroller_false(client, stroller_user):
    """has_stroller_now=False → stroller_active_until None olmalı."""
    uid = stroller_user["id"]
    # Önce aktif et
    client.patch(f"/users/{uid}/session", json={"has_stroller_now": True})

    # Sonra iptal et
    resp = client.patch(f"/users/{uid}/session", json={"has_stroller_now": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is False, "Stroller iptal edilince is_active False olmalı"
    assert data["stroller_active_until"] is None, "Stroller iptal edilince active_until None olmalı"


def test_session_cache_90min(client, stroller_user):
    """Aktif oturum süresince iki ardışık GET çağrısında should_ask False kalmalı."""
    uid = stroller_user["id"]

    client.patch(f"/users/{uid}/session", json={"has_stroller_now": True})

    resp1 = client.get(f"/users/{uid}/session")
    assert resp1.json()["should_ask"] is False, "1. GET: aktif cache'de should_ask False olmalı"

    resp2 = client.get(f"/users/{uid}/session")
    assert resp2.json()["should_ask"] is False, "2. GET: cache süresi dolmadan should_ask hâlâ False olmalı"
    assert resp2.json()["is_active"] is True
