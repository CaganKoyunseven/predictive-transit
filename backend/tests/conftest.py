"""
Ortak test fixture'ları.
Her test fonksiyonu bağımsız, temiz bir DB ve mock ML modelleri ile çalışır.
"""

import os

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock

from backend.database import Base, get_db
from backend.main import app

TEST_DB_PATH = "./test_predictive_transit.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

# Gecikme modelinin döndüreceği varsayılan tahmin (dakika)
DEFAULT_DELAY = 5.0
# Kalabalık modelinin döndüreceği varsayılan yolcu sayısı
DEFAULT_CROWD = 30.0
# Crowding sınıflandırıcısının döndüreceği varsayılan sınıf indeksi
# classes_ = ["busy","crowded","empty","light","moderate"] → index 4 = "moderate"
DEFAULT_CROWDING_IDX = 4


@pytest.fixture(scope="function")
def test_db():
    """
    Her test için izole SQLite veritabanı.
    get_db bağımlılığını override eder; test sonunda tablolar ve dosya silinir.
    """
    # Kalan dosyayı temizle
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def _override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    yield TestSession

    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture(scope="function")
def mock_models():
    """
    Gerçek .pkl yüklemeden sahte ML model objeleri.
    Her fixture çağrısında taze MagicMock nesneleri döner.
    """
    delay_model = MagicMock()
    delay_model.predict.return_value = np.array([DEFAULT_DELAY])

    crowd_model = MagicMock()
    crowd_model.predict.return_value = np.array([DEFAULT_CROWD])

    crowding_model = MagicMock()
    crowding_model.predict.return_value = np.array([DEFAULT_CROWDING_IDX])

    crowding_le = MagicMock()
    crowding_le.classes_ = np.array(["busy", "crowded", "empty", "light", "moderate"])

    return {
        "delay": delay_model,
        "crowd": crowd_model,
        "delay_features": [
            "hour_of_day", "day_of_week", "is_weekend", "stop_sequence",
            "cumulative_delay_min", "speed_factor", "traffic_level_enc",
            "weather_enc", "temperature_c", "precipitation_mm", "wind_speed_kmh",
            "is_terminal", "is_transfer_hub", "stop_type_enc",
            "departure_delay_min", "minutes_to_next_bus",
        ],
        "crowd_features": [
            "hour_of_day", "day_of_week", "is_weekend", "stop_type_enc",
            "minutes_to_next_bus", "weather_enc", "avg_passengers_waiting",
            "time_bucket_enc", "delay_min", "transit_delay_risk",
            "passenger_demand_multiplier",
        ],
        "crowding": crowding_model,
        "crowding_features": [
            "hour_of_day", "day_of_week", "is_weekend", "stop_type_enc",
            "minutes_to_next_bus", "weather_enc", "avg_passengers_waiting",
            "time_bucket_enc", "delay_min", "transit_delay_risk",
            "passenger_demand_multiplier",
        ],
        "crowding_label_encoder": crowding_le,
        "label_encoders": MagicMock(),
    }


@pytest.fixture(scope="function")
def client(test_db, mock_models):
    """
    FastAPI TestClient: test DB + mock ML modelleri birlikte.
    Lifespan başladıktan sonra app.state.models mock ile override edilir.
    """
    with TestClient(app) as c:
        app.state.models = mock_models
        yield c


@pytest.fixture(scope="function")
def test_user(client):
    """DB'ye kayıtlı hazır kullanıcı (stroller profili yok)."""
    resp = client.post("/users", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123",
    })
    assert resp.status_code == 201, f"Test kullanıcısı oluşturulamadı: {resp.json()}"
    return resp.json()


@pytest.fixture(scope="function")
def stroller_user(client):
    """has_stroller_profile=True olan hazır kullanıcı."""
    resp = client.post("/users", json={
        "username": "strolleruser",
        "email": "stroller@example.com",
        "password": "password123",
        "has_stroller_profile": True,
    })
    assert resp.status_code == 201, f"Stroller kullanıcısı oluşturulamadı: {resp.json()}"
    return resp.json()


# Geçerli bir /predict isteği için varsayılan payload
VALID_PREDICT_PAYLOAD = {
    "stop_id": "STP-L01-03",
    "stop_sequence": 3,
    "hour_of_day": 8,
    "day_of_week": 1,
    "is_weekend": False,
    "speed_factor": 0.8,
    "traffic_level": "moderate",
    "weather_condition": "clear",
    "temperature_c": 15.0,
}
