# Predictive Transit — Implementation Plan

Bu dosya Claude Code için yazılmıştır. Her aşamada bu dosyayı okuyarak implemente et.
Hiçbir şeyi değiştirme, ekstra dosya oluşturma, ekstra bağımlılık ekleme — sadece burada yazanı yap.
Türkçe karakter içeren string'leri olduğu gibi kullan.

---

## Proje Özeti

**Ne yapıyor:** Sivas şehir içi otobüsleri için gerçek zamanlı varış gecikmesi ve durak kalabalık tahmini yapan bir web uygulaması.

**Veri seti:** Sentetik, Sivas Mart 2025, 5 hat (L01-L05), 62 durak, ~13.400 sefer.

**Hackathon metrikleri:**
- Gecikme tahmini: MAE (hedef < 5 dakika)
- Kalabalık tahmini: RMSE (hedef < 8 kisi)
- UX kriteri: tahmin arayüzü 1 saniyeden kisa sürede yüklenmeli

**Yenilikci özellikler:**
- Engelli / bebek arabali kullanicilara otobüs doluluk uyarisi (Accessibility API)
- Yürüyüs süresi vs. otobüs süresi karsilastirmasi — "Otobüsü Yen!" (Gamification)
- ML tahminini kullanici geri bildirimiyle dogrulama (Waze tipi Crowdsourcing)
- Bebek arabasi oturum önbellegi — 90 dakika boyunca ayni soruyu sorma
- Model RAM'de tutulur, tahmin < 100ms (Hackathon UX kriteri: < 1 saniye)

---

## Teknoloji Stack

| Katman | Teknoloji |
|--------|-----------|
| Backend | Python 3.11+, FastAPI 0.111, Uvicorn |
| Veritabani | SQLite, SQLAlchemy 2.0 ORM |
| ML | XGBoost 2.0, scikit-learn 1.4, pandas, numpy |
| Model Serving | joblib .pkl, RAM Singleton (app.state.models) |
| Validation | Pydantic 2.0 |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS v3, Leaflet |
| HTTP | Axios |

---

## Klasör Yapisi

```
predictive-transit/
├── IMPLEMENTATION_PLAN.md
├── requirements.txt
├── .env
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── sessions.py
│   │   ├── predict.py
│   │   ├── stops.py
│   │   ├── accessibility.py
│   │   ├── challenge.py
│   │   └── feedback.py
│   └── ml/
│       ├── train.py
│       ├── predict.py
│       └── models/
│           ├── delay_model.pkl        (train.py calistirinca olusur)
│           ├── crowd_model.pkl        (train.py calistirinca olusur)
│           ├── delay_features.pkl     (train.py calistirinca olusur)
│           ├── crowd_features.pkl     (train.py calistirinca olusur)
│           └── label_encoders.pkl     (train.py calistirinca olusur)
├── data/
│   ├── bus_trips.csv
│   ├── stop_arrivals.csv
│   ├── weather_observations.csv
│   ├── bus_stops.csv
│   └── passenger_flow.csv
└── frontend/
    ├── index.html
    ├── vite.config.ts
    ├── tailwind.config.js
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── context/
        │   └── UserContext.tsx
        ├── hooks/
        │   ├── usePrediction.ts
        │   ├── useUserSession.ts
        │   └── useFeedback.ts
        ├── pages/
        │   ├── MapPage.tsx
        │   └── ProfilePage.tsx
        └── components/
            ├── Map/
            │   ├── MapContainer.tsx
            │   └── BusStopMarker.tsx
            ├── StopPanel/
            │   ├── PredictionCard.tsx
            │   ├── CrowdBar.tsx
            │   └── CrowdConfirmButtons.tsx
            └── Modals/
                ├── StrollerModal.tsx
                ├── AccessibilityAlert.tsx
                ├── BeatTheBusModal.tsx
                └── PostTripModal.tsx
```

---

## requirements.txt

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
pydantic[email]==2.7.1
python-dotenv==1.0.1
passlib[bcrypt]==1.7.4
joblib==1.4.2
xgboost==2.0.3
scikit-learn==1.4.2
pandas==2.2.2
numpy==1.26.4
pytest==8.2.0
httpx==0.27.0
matplotlib==3.8.4
```

---

## .env

```
DATABASE_URL=sqlite:///./predictive_transit.db
ACCESSIBILITY_THRESHOLD=0.80
BUS_CAPACITY=60
SECRET_KEY=changeme-in-production
```

---

## Veritabani Semasi (backend/models.py)

### User tablosu

| Kolon | Tip | Kisit |
|-------|-----|-------|
| id | Integer | PK, autoincrement |
| username | String(50) | unique, not null, index |
| email | String(100) | unique, not null, index |
| hashed_password | String | not null |
| is_disabled | Boolean | default=False, not null |
| has_stroller_profile | Boolean | default=False, not null |
| created_at | DateTime(timezone=True) | server_default=func.now() |

Iliskiler: sessions (UserSession, cascade all delete-orphan), feedbacks (Feedback, cascade all delete-orphan)

### UserSession tablosu

| Kolon | Tip | Kisit |
|-------|-----|-------|
| id | Integer | PK, autoincrement |
| user_id | Integer | FK users.id, not null, index |
| stroller_active_until | DateTime(timezone=True) | nullable |
| last_asked_at | DateTime(timezone=True) | nullable |
| session_date | Date | nullable |

Iliski: user (User)

### Feedback tablosu

| Kolon | Tip | Kisit |
|-------|-----|-------|
| id | Integer | PK, autoincrement |
| user_id | Integer | FK users.id, not null, index |
| trip_id | String | nullable |
| stop_id | String | nullable, index |
| feedback_type | String(30) | not null |
| rating | Integer | nullable, 1-5 |
| comment | Text | nullable |
| is_on_time | Boolean | nullable |
| crowd_actual | String(20) | nullable |
| created_at | DateTime(timezone=True) | server_default=func.now() |

Iliski: user (User)

---

## Pydantic Semalari (backend/schemas.py)

### UserCreate
```python
username: str = Field(..., min_length=3, max_length=50)
email: EmailStr
password: str = Field(..., min_length=6)
is_disabled: bool = False
has_stroller_profile: bool = False
```

### UserUpdate
```python
is_disabled: Optional[bool] = None
has_stroller_profile: Optional[bool] = None
```

### UserResponse
```python
id: int
username: str
email: str
is_disabled: bool
has_stroller_profile: bool
created_at: Optional[datetime]
model_config = {"from_attributes": True}
```

### StrollerSessionUpdate
```python
has_stroller_now: bool
```

### StrollerSessionResponse
```python
user_id: int
stroller_active_until: Optional[datetime]
should_ask: bool
is_active: bool
model_config = {"from_attributes": True}
```

### PredictRequest
```python
stop_id: str
trip_id: Optional[str] = None
stop_sequence: int = Field(..., ge=1)
hour_of_day: int = Field(..., ge=0, le=23)
day_of_week: int = Field(..., ge=0, le=6)
is_weekend: bool = False
cumulative_delay_min: float = 0.0
speed_factor: float = Field(..., ge=0.0, le=1.0)
traffic_level: str = Field(..., pattern="^(low|moderate|high|congested)$")
weather_condition: str = Field(..., pattern="^(clear|cloudy|rain|snow|fog|wind)$")
temperature_c: float
precipitation_mm: float = 0.0
wind_speed_kmh: float = 0.0
is_terminal: bool = False
is_transfer_hub: bool = False
stop_type: str = "regular"
departure_delay_min: float = 0.0
minutes_to_next_bus: float = 15.0
```

### PredictResponse
```python
stop_id: str
predicted_delay_min: float
predicted_passengers_waiting: int
accessibility_warning: bool = False
confidence: str = "medium"   # "low" / "medium" / "high"
```

### AccessibilityRequest
```python
user_id: int
stop_id: str
trip_id: Optional[str] = None
predicted_passengers_waiting: int
```

### AccessibilityResponse
```python
accessibility_warning: bool
message: Optional[str] = None
predicted_occupancy_pct: float
```

### BeatTheBusRequest
```python
user_lat: float
user_lng: float
target_stop_lat: float
target_stop_lng: float
bus_eta_min: float
user_weight_kg: float = 70.0
```

### BeatTheBusResponse
```python
challenge: bool
walking_time_min: Optional[float] = None
bus_time_min: Optional[float] = None
time_saved_min: Optional[float] = None
calories_burned: Optional[float] = None
walking_distance_m: Optional[float] = None
reason: Optional[str] = None
```

### CrowdConfirmRequest
```python
user_id: int
stop_id: str
trip_id: Optional[str] = None
crowd_actual: str = Field(..., pattern="^(empty|as_predicted|crowded)$")
```

### PostTripReviewRequest
```python
user_id: int
trip_id: Optional[str] = None
stop_id: Optional[str] = None
rating: int = Field(..., ge=1, le=5)
is_on_time: Optional[bool] = None
comment: Optional[str] = Field(None, max_length=500)
```

### FeedbackResponse
```python
id: int
feedback_type: str
created_at: Optional[datetime]
model_config = {"from_attributes": True}
```

### StopResponse
```python
stop_id: str
line_id: str
line_name: str
stop_sequence: int
latitude: float
longitude: float
stop_type: str
is_terminal: bool
is_transfer_hub: bool
```

---

## database.py

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./predictive_transit.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## main.py

FastAPI lifespan kullan (on_event deprecated).

Lifespan startup sirasinda:
1. `Base.metadata.create_all(bind=engine)` ile tablolari olustur
2. `backend/ml/models/` klasöründeki pkl dosyalarini joblib ile yükle, `app.state.models` dict'ine kaydet
3. Dosya yoksa `logger.warning` bas, hata verme, fallback ile calismeye devam et

Yüklenecek model dosyalari:
- `delay_model.pkl` -> `app.state.models["delay"]`
- `crowd_model.pkl` -> `app.state.models["crowd"]`
- `delay_features.pkl` -> `app.state.models["delay_features"]`
- `crowd_features.pkl` -> `app.state.models["crowd_features"]`
- `label_encoders.pkl` -> `app.state.models["label_encoders"]`

CORS: `allow_origins=["http://localhost:5173", "http://localhost:3000"]`

Router kayitlari:
```python
app.include_router(users.router,         prefix="/users",         tags=["Kullanicilar"])
app.include_router(sessions.router,      prefix="/users",         tags=["Oturum"])
app.include_router(predict.router,       prefix="",               tags=["Tahmin"])
app.include_router(stops.router,         prefix="/stops",         tags=["Duraklar"])
app.include_router(accessibility.router, prefix="/accessibility",  tags=["Erisebilirlik"])
app.include_router(challenge.router,     prefix="/challenge",     tags=["Gamification"])
app.include_router(feedback.router,      prefix="/feedback",      tags=["Geri Bildirim"])
```

`GET /health` yaniti:
```json
{
  "status": "ok",
  "models": {
    "delay_model": "ready",
    "crowd_model": "not_loaded"
  },
  "predict_service": "active"
}
```

`GET /` yaniti: `{"app": "Predictive Transit API", "docs": "/docs", "health": "/health"}`

---

## Router Detaylari

### routers/users.py

- `POST /users`: UserCreate al, bcrypt ile hash, User olustur, UserResponse döndür. Username veya email zaten varsa 400.
- `GET /users/{user_id}`: UserResponse döndür, yoksa 404.
- `PATCH /users/{user_id}`: UserUpdate al, sadece gelen alanlari güncelle, UserResponse döndür.

### routers/sessions.py

`STROLLER_CACHE_MINUTES = 90`

**GET /users/{user_id}/session:**
- Kullanici yoksa 404
- `has_stroller_profile=False` ise: `should_ask=False`, `is_active=False` döndür
- UserSession yoksa olustur (bos)
- `stroller_active_until` var ve `now()` degerinden büyükse: `should_ask=False`, `is_active=True`
- Aksi halde: `should_ask=True`, `is_active=False`

**PATCH /users/{user_id}/session** (body: StrollerSessionUpdate):
- `has_stroller_now=True`: `stroller_active_until = now() + 90 dakika`, `last_asked_at = now()`
- `has_stroller_now=False`: `stroller_active_until = None`, `last_asked_at = now()`
- StrollerSessionResponse döndür

### routers/predict.py

`POST /predict` (body: PredictRequest) -> PredictResponse

Is akisi:
1. `request.app.state.models` içinden delay ve crowd modellerini al
2. Model yoksa fallback: `predicted_delay_min=8.2`, `predicted_passengers_waiting=34`, `accessibility_warning=False`, `confidence="low"`
3. Feature encoding:
   - traffic: `low=0, moderate=1, high=2, congested=3`
   - weather: `clear=0, cloudy=1, rain=2, fog=3, wind=4, snow=5`
   - stop_type: `regular=0, terminal=1, transfer_hub=2, university=3, hospital=4, market=5, residential=6`
4. `delay_features` listesindeki siraya göre DataFrame olustur, `delay_model.predict()` cagir
5. `crowd_features` listesindeki siraya göre DataFrame olustur (`delay_min` olarak `predicted_delay_min` kullan), `crowd_model.predict()` cagir, `max(0, round(pred))` uygula
6. Confidence: `predicted_passengers_waiting < 20` -> `"high"`, `< 50` -> `"medium"`, else -> `"low"`
7. `accessibility_warning`: `predicted_passengers_waiting >= BUS_CAPACITY(60) * ACCESSIBILITY_THRESHOLD(0.80)` yani `>= 48`

### routers/stops.py

- `GET /stops`: `data/bus_stops.csv` oku, `List[StopResponse]` döndür
- `GET /stops/{stop_id}`: Tek durak, yoksa 404
- CSV yolu için `os.path` ile proje kökünü bul. Pandas ile oku.

### routers/accessibility.py

`GET /accessibility/warning?user_id=X&stop_id=Y&predicted_passengers_waiting=Z`

- User'i DB'den cek, yoksa 404
- UserSession'i DB'den cek, stroller aktif mi kontrol et (`stroller_active_until > now()`)
- `is_eligible = user.is_disabled OR stroller_is_active`
- `threshold = 60 * 0.80 = 48`
- `warning = is_eligible AND predicted_passengers_waiting >= threshold`
- AccessibilityResponse döndür:
  - `accessibility_warning`: True/False
  - `message`: `"Bu otobüs çok dolu, engelli/bebek arabasi alani dolu olabilir."` (sadece warning=True ise)
  - `predicted_occupancy_pct`: `round(predicted_passengers_waiting / 60 * 100, 1)`

### routers/challenge.py

`POST /challenge/beat-the-bus` (body: BeatTheBusRequest)

Haversine fonksiyonu (metre):
```python
import math
def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
```

Is akisi:
1. `distance_m = haversine(user_lat, user_lng, target_stop_lat, target_stop_lng)`
2. `walking_time_min = (distance_m / 1000) / 5.0 * 60`
3. `calories = 3.5 * weight_kg * (walking_time_min / 60)`
4. `time_saved = round(bus_eta_min - walking_time_min, 1)`
5. `walking_time_min < bus_eta_min` ise: `challenge=True`, tüm degerleri döndür
6. Aksi halde: `challenge=False`, `reason="bus_is_faster"`

### routers/feedback.py

**POST /feedback/live-crowd** (body: CrowdConfirmRequest):
- `feedback_type = "crowd_confirm"`
- Feedback tablosuna kaydet, FeedbackResponse döndür

**POST /feedback/post-trip** (body: PostTripReviewRequest):
- `feedback_type = "post_trip_review"`
- Feedback tablosuna kaydet, FeedbackResponse döndür

---

## ML — backend/ml/train.py

### Veri Yükleme

```python
from pathlib import Path
DATA_DIR = Path(__file__).parent.parent.parent / "data"
```

Birlestirme sirasi:
1. `stop_arrivals.csv` ana tablo
2. `bus_trips.csv` LEFT JOIN on `trip_id` (kolonlar: `speed_factor`, `traffic_level`, `departure_delay_min`, `weather_condition`, `temperature_c`, `precipitation_mm`, `wind_speed_kmh`)
3. `bus_stops.csv` LEFT JOIN on `stop_id` (kolonlar: `is_terminal`, `is_transfer_hub`, `stop_type`)
4. `weather_observations.csv`: timestamp parse et, `merge_asof` ile en yakin gözlemi eslesttir (`transit_delay_risk`, `passenger_demand_multiplier` kolonlari için)
5. `passenger_flow.csv`: `stop_id + hour_of_day` üzerinden `avg_passengers_waiting` ortalamasini ekle

### Encoding

```python
traffic_map     = {"low": 0, "moderate": 1, "high": 2, "congested": 3}
weather_map     = {"clear": 0, "cloudy": 1, "rain": 2, "fog": 3, "wind": 4, "snow": 5}
time_bucket_map = {"early_morning": 0, "morning_peak": 1, "midday": 2,
                   "evening_peak": 3, "evening": 4, "night": 5}
```

`stop_type` için sklearn `LabelEncoder` kullan, encoder'i kaydet.

### Model 1 — delay_model

**Hedef:** `delay_min`  
**Metrik:** MAE

Feature listesi (bu sirayla):
```python
DELAY_FEATURES = [
    "hour_of_day", "day_of_week", "is_weekend", "stop_sequence",
    "cumulative_delay_min", "speed_factor", "traffic_level_enc",
    "weather_enc", "temperature_c", "precipitation_mm", "wind_speed_kmh",
    "is_terminal", "is_transfer_hub", "stop_type_enc",
    "departure_delay_min", "minutes_to_next_bus"
]
```

```python
XGBRegressor(n_estimators=300, max_depth=6, learning_rate=0.05,
             subsample=0.8, random_state=42, n_jobs=-1)
TimeSeriesSplit(n_splits=5)
```

### Model 2 — crowd_model

**Hedef:** `passengers_waiting`  
**Metrik:** RMSE  
**Post-process:** `max(0, round(pred))`

Feature listesi (bu sirayla):
```python
CROWD_FEATURES = [
    "hour_of_day", "day_of_week", "is_weekend", "stop_type_enc",
    "minutes_to_next_bus", "weather_enc", "avg_passengers_waiting",
    "time_bucket_enc", "delay_min", "transit_delay_risk",
    "passenger_demand_multiplier"
]
```

```python
XGBRegressor(n_estimators=300, max_depth=5, learning_rate=0.05,
             min_child_weight=3, random_state=42, n_jobs=-1)
```

### Kaydetme

```python
MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

joblib.dump(model,          MODEL_DIR / "delay_model.pkl")
joblib.dump(model_crowd,    MODEL_DIR / "crowd_model.pkl")
joblib.dump(DELAY_FEATURES, MODEL_DIR / "delay_features.pkl")
joblib.dump(CROWD_FEATURES, MODEL_DIR / "crowd_features.pkl")
joblib.dump({"stop_type": le_stop_type}, MODEL_DIR / "label_encoders.pkl")
```

### Feature Importance Grafikleri

Her iki model için matplotlib ile barh grafigi olustur, MODEL_DIR'e kaydet:
- `feature_importance_delay.png`
- `feature_importance_crowd.png`

Script sonunda CV sonuclarini yazdir:
```
Delay MAE (CV): X.XXX +/- X.XXX dk
Crowd RMSE (CV): X.XXX +/- X.XXX kisi
Modeller kaydedildi: backend/ml/models/
```

---

## backend/ml/predict.py

Router'larin kullanabilecegi yardimci fonksiyonlar:

```python
TRAFFIC_MAP = {"low": 0, "moderate": 1, "high": 2, "congested": 3}
WEATHER_MAP = {"clear": 0, "cloudy": 1, "rain": 2, "fog": 3, "wind": 4, "snow": 5}
STOP_TYPE_MAP = {"regular": 0, "terminal": 1, "transfer_hub": 2,
                 "university": 3, "hospital": 4, "market": 5, "residential": 6}
TIME_BUCKET_MAP = {"early_morning": 0, "morning_peak": 1, "midday": 2,
                   "evening_peak": 3, "evening": 4, "night": 5}

def build_delay_features(req, feature_list: list) -> pd.DataFrame:
    # req: PredictRequest
    # feature_list: app.state.models["delay_features"]
    # Encoding uygula, feature_list sırasında DataFrame döndür
    # Eksik feature varsa 0 ile doldur

def build_crowd_features(req, predicted_delay: float, feature_list: list) -> pd.DataFrame:
    # req: PredictRequest
    # predicted_delay: delay modelinden gelen sonuc (delay_min feature'i olarak kullan)
    # avg_passengers_waiting: 34.0 fallback
    # transit_delay_risk: 0.3 fallback
    # passenger_demand_multiplier: 1.0 fallback
    # time_bucket_enc: 2 fallback (midday)
```

---

## Frontend (Asama 4)

### Kurulum

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install leaflet react-leaflet @types/leaflet
npm install axios react-router-dom react-hook-form lucide-react
```

### vite.config.ts — proxy

```ts
server: {
  proxy: {
    '/api': { target: 'http://localhost:8000', rewrite: (path) => path.replace(/^\/api/, '') }
  }
}
```

### MapContainer.tsx

- Sivas merkez: `center=[39.748, 37.014]`, `zoom=13`
- `GET /stops` endpoint'inden durak listesini cek
- Her durak icin `BusStopMarker` render et
- Marker rengi: `is_terminal=true` -> kirmizi, `is_transfer_hub=true` -> turuncu, diger -> mavi
- Tiklaninca: `usePrediction` hook cagir, StopPanel guncelle

### usePrediction.ts hook

- State: `loading`, `prediction`, `error`
- Axios timeout: 2000ms
- Ayni `stop_id` icin son 30 saniye önbellekte tut (`useRef` ile timestamp karsilastir)
- Loading sirasinda skeleton goster

### PredictionCard.tsx

Gösterilecek bilgiler:
- Tahmini gecikme: "~X dk gecikme bekleniyor"
- Kalabalik: progress bar ile görsel
- Confidence badge: `high`=yesil, `medium`=sari, `low`=kirmizi
- `CrowdConfirmButtons` bileseni

### CrowdConfirmButtons.tsx

Uc buton: `[Dogru]`, `[Az Kisi]`, `[Cok Dolu]`
- Tiklaninca `POST /feedback/live-crowd` cagir
- Basarisinda "Geri bildiriminiz icin tesekkürler" toast goster (2 saniye)
- Optimistic update: tiklanan buton hemen secili görünümüne gec

### StrollerModal.tsx

Tetikleyici: `has_stroller_profile=true` VE `should_ask=true`
- Baslik: "Bebek Arabaniz Var mi?"
- Mesaj: "Su an yaniinizda bebek arabaniz var mi?"
- `[Evet, Var]` -> `PATCH /users/{id}/session` (`has_stroller_now=true`)
- `[Hayir]` -> `PATCH /users/{id}/session` (`has_stroller_now=false`)
- Modal kapaninca tahmin paneli acilir

### AccessibilityAlert.tsx

Tetikleyici: `GET /accessibility/warning` -> `accessibility_warning=true`
- Stil: kirmizi border (`border-red-500`), `lucide-react` AlertTriangle ikonu
- Icerik: "Bu otobüs cok dolu — Engelli/bebek arabasi alani dolu olabilir"
- `[Bir Sonraki Otobüsü Bekle]`, `[Yine de Devam Et]` butonlari

### BeatTheBusModal.tsx

Tetikleyici: `POST /challenge/beat-the-bus` -> `challenge=true`
- "{time_saved_min} dakika erken varirsin!"
- "{calories_burned} kalori yakarsin"
- "{walking_distance_m}m yürüyüs"
- Haritada yesil Polyline (yürüyüs rotasi)
- `[Meydan Oku!]` butonu

### PostTripModal.tsx

Tetikleyici: "Yolculugumu Bitirdim" butonuna basilinca

Form alanlari:
- Genel deneyim: 1-5 yildiz (zorunlu)
- "Otobüs zamaninda geldi mi?": Evet / Hayir toggle
- Sürücü davranisi: 1-5 yildiz (opsiyonel)
- Yorum: textarea (opsiyonel, max 500 karakter)
- Gönder -> `POST /feedback/post-trip`

### UX Kurallari

- Tahmin yüklenirken skeleton UI (gri animasyonlu bloklar)
- Axios timeout: 2000ms, asilirsa "Sunucuya ulasilamiyor" mesaji
- Hata durumlarinda Türkce mesaj
- Marker tiklama 200ms debounce
- Optimistic update crowdsource butonlarinda

---

## API Endpoint Tam Listesi

| Method | Path | Router | Aciklama |
|--------|------|--------|----------|
| GET | / | main.py | Uygulama bilgisi |
| GET | /health | main.py | Model + sistem durumu |
| POST | /predict | predict.py | Gecikme + kalabalik tahmini |
| POST | /users | users.py | Kullanici kaydi |
| GET | /users/{id} | users.py | Profil bilgisi |
| PATCH | /users/{id} | users.py | Profil güncelleme |
| GET | /users/{id}/session | sessions.py | Bebek arabasi oturum durumu |
| PATCH | /users/{id}/session | sessions.py | Bebek arabasi oturum güncelleme |
| GET | /stops | stops.py | Tüm durak listesi (Leaflet icin) |
| GET | /stops/{stop_id} | stops.py | Tek durak bilgisi |
| GET | /accessibility/warning | accessibility.py | Doluluk uyarisi |
| POST | /challenge/beat-the-bus | challenge.py | Yürüyüs vs. otobüs |
| POST | /feedback/live-crowd | feedback.py | Kalabalik crowdsource |
| POST | /feedback/post-trip | feedback.py | Yolculuk sonu degerlendirmesi |
| GET | /docs | FastAPI | Swagger UI |

---

## Uygulama Baslatma

```bash
# Backend
cd predictive-transit
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# ML egitimi (CSV'ler data/ klasöründeyken)
python -m backend.ml.train

# Sunucu
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm run dev
```
