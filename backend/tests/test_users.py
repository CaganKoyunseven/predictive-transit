"""
Kullanıcı CRUD endpoint testleri.
POST /users · GET /users/{id} · PATCH /users/{id}
"""


def test_create_user_success(client):
    """Geçerli verilerle kullanıcı oluşturma başarılı olmalı."""
    resp = client.post("/users", json={
        "username": "yenikullanici",
        "email": "yeni@example.com",
        "password": "sifre123",
    })
    assert resp.status_code == 201, f"Beklenen 201, alınan {resp.status_code}: {resp.json()}"
    data = resp.json()
    assert data["username"] == "yenikullanici", "Kullanıcı adı response'da olmalı"
    assert data["email"] == "yeni@example.com", "E-posta response'da olmalı"
    assert "id" in data, "Response'da id alanı olmalı"
    assert "hashed_password" not in data, "Hash şifre response'a sızmamalı"


def test_create_user_duplicate_username(client, test_user):
    """Aynı username ile ikinci kayıt 400 dönmeli."""
    resp = client.post("/users", json={
        "username": test_user["username"],  # zaten var
        "email": "baska@example.com",
        "password": "sifre123",
    })
    assert resp.status_code == 400, "Var olan username ile kayıt 400 dönmeli"
    assert "already taken" in resp.json()["detail"].lower()


def test_create_user_duplicate_email(client, test_user):
    """Aynı e-posta ile ikinci kayıt 400 dönmeli."""
    resp = client.post("/users", json={
        "username": "baskakisi",
        "email": test_user["email"],  # zaten var
        "password": "sifre123",
    })
    assert resp.status_code == 400, "Var olan e-posta ile kayıt 400 dönmeli"
    assert "already registered" in resp.json()["detail"].lower()


def test_create_user_missing_field(client):
    """Zorunlu alan eksikse 422 dönmeli."""
    resp = client.post("/users", json={
        "username": "eksikmail",
        # email eksik
        "password": "sifre123",
    })
    assert resp.status_code == 422, "Eksik alan için 422 validation hatası bekleniyor"


def test_get_user_success(client, test_user):
    """Mevcut kullanıcı id'si ile GET isteği 200 ve kullanıcı bilgisi dönmeli."""
    resp = client.get(f"/users/{test_user['id']}")
    assert resp.status_code == 200, f"Mevcut kullanıcı için 200 bekleniyor, alınan {resp.status_code}"
    data = resp.json()
    assert data["id"] == test_user["id"]
    assert data["username"] == test_user["username"]


def test_get_user_not_found(client):
    """Olmayan id ile GET isteği 404 dönmeli."""
    resp = client.get("/users/99999")
    assert resp.status_code == 404, "Olmayan kullanıcı için 404 bekleniyor"


def test_patch_user_is_disabled(client, test_user):
    """is_disabled güncelleme doğru çalışmalı."""
    resp = client.patch(f"/users/{test_user['id']}", json={"is_disabled": True})
    assert resp.status_code == 200, f"PATCH başarısız: {resp.json()}"
    assert resp.json()["is_disabled"] is True, "is_disabled True olarak güncellenmeli"


def test_patch_user_stroller_profile(client, test_user):
    """has_stroller_profile güncelleme doğru çalışmalı."""
    resp = client.patch(f"/users/{test_user['id']}", json={"has_stroller_profile": True})
    assert resp.status_code == 200, f"PATCH başarısız: {resp.json()}"
    assert resp.json()["has_stroller_profile"] is True, "has_stroller_profile True olarak güncellenmeli"
