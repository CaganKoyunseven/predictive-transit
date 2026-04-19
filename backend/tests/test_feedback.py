"""
Geri bildirim endpoint testleri.
POST /feedback/live-crowd · POST /feedback/post-trip
"""

from backend.models import Feedback


def test_live_crowd_success(client, test_user):
    """Geçerli crowd_confirm geri bildirimi 201 ve FeedbackResponse dönmeli."""
    resp = client.post("/feedback/live-crowd", json={
        "user_id": test_user["id"],
        "stop_id": "STP-L01-01",
        "crowd_actual": "as_predicted",
    })
    assert resp.status_code == 201, f"Beklenen 201, alınan {resp.status_code}: {resp.json()}"
    data = resp.json()
    assert data["feedback_type"] == "crowd_confirm", "feedback_type 'crowd_confirm' olmalı"
    assert "id" in data, "Response'da id alanı olmalı"


def test_live_crowd_invalid_crowd_actual(client, test_user):
    """Geçersiz crowd_actual değeri 422 dönmeli."""
    resp = client.post("/feedback/live-crowd", json={
        "user_id": test_user["id"],
        "stop_id": "STP-L01-01",
        "crowd_actual": "geçersiz_deger",
    })
    assert resp.status_code == 422, "Geçersiz crowd_actual için 422 bekleniyor"


def test_post_trip_success(client, test_user):
    """Geçerli post_trip_review geri bildirimi 201 dönmeli."""
    resp = client.post("/feedback/post-trip", json={
        "user_id": test_user["id"],
        "rating": 4,
        "is_on_time": True,
        "comment": "Otobüs zamanındaydı.",
    })
    assert resp.status_code == 201, f"Beklenen 201, alınan {resp.status_code}: {resp.json()}"
    data = resp.json()
    assert data["feedback_type"] == "post_trip_review", "feedback_type 'post_trip_review' olmalı"


def test_post_trip_rating_too_low(client, test_user):
    """rating=0 (ge=1 ihlali) → 422 dönmeli."""
    resp = client.post("/feedback/post-trip", json={
        "user_id": test_user["id"],
        "rating": 0,
    })
    assert resp.status_code == 422, "rating=0 için 422 bekleniyor (ge=1)"


def test_post_trip_rating_too_high(client, test_user):
    """rating=6 (le=5 ihlali) → 422 dönmeli."""
    resp = client.post("/feedback/post-trip", json={
        "user_id": test_user["id"],
        "rating": 6,
    })
    assert resp.status_code == 422, "rating=6 için 422 bekleniyor (le=5)"


def test_post_trip_comment_too_long(client, test_user):
    """500 karakterden uzun comment → 422 dönmeli."""
    resp = client.post("/feedback/post-trip", json={
        "user_id": test_user["id"],
        "rating": 3,
        "comment": "x" * 501,
    })
    assert resp.status_code == 422, "501 karakterlik comment için 422 bekleniyor (max_length=500)"


def test_feedback_saved_to_db(client, test_user, test_db):
    """Gönderilen geri bildirimler DB'ye gerçekten kaydedilmeli."""
    uid = test_user["id"]

    client.post("/feedback/live-crowd", json={
        "user_id": uid,
        "stop_id": "STP-L01-02",
        "crowd_actual": "crowded",
    })
    client.post("/feedback/post-trip", json={
        "user_id": uid,
        "rating": 5,
    })

    db = test_db()
    count = db.query(Feedback).filter(Feedback.user_id == uid).count()
    db.close()

    assert count == 2, f"DB'de 2 feedback kaydı olmalı, bulunan: {count}"
