# Predictive Transit — Proje Raporu

**Tarih:** 2026-04-18  
**Kapsam:** Sivas şehir içi otobüsleri için gerçek zamanlı gecikme, kalabalık ve crowding sınıflandırması yapan web uygulaması

---

## 1. Genel Mimari

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (React 19 + TypeScript + Vite)                │
│  localhost:5173                                         │
│  Leaflet harita · Tailwind CSS · Axios /api proxy       │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP (Vite proxy /api → :8000)
┌────────────────────▼────────────────────────────────────┐
│  Backend (FastAPI + Uvicorn)                            │
│  localhost:8000                                         │
│  SQLite DB · XGBoost ML · CSV verisi                   │
└──────┬──────────┬──────────┬───────────────────────────┘
       │          │          │
  SQLite DB   ML modeller   Dış API'ler
  (.db)       (.pkl)        Open-Meteo · OSRM
```

---

## 2. Teknoloji Stack

### Backend
| Teknoloji | Versiyon | Kullanım |
|-----------|----------|----------|
| Python | 3.11+ | Runtime |
| FastAPI | 0.111.0 | REST API framework |
| Uvicorn | 0.29.0 | ASGI server |
| SQLAlchemy | 2.0.30 | ORM |
| SQLite | — | Veritabanı |
| Pydantic | 2.7.1 | Request/response validation |
| XGBoost | 2.0.3 | ML model (gecikme + kalabalık + crowding sınıflandırması) |
| scikit-learn | 1.4.2 | LabelEncoder, TimeSeriesSplit, StratifiedKFold, MAE |
| pytest | 8.2.0 | Test framework |
| pytest-cov | 7.1.0 | Test coverage raporlama |
| pandas | 2.2.2 | CSV işleme, feature engineering |
| numpy | 1.26.4 | Sayısal işlemler |
| joblib | 1.4.2 | Model serileştirme (.pkl) |
| httpx | 0.27.0 | OSRM ve Open-Meteo HTTP istekleri |
| passlib + bcrypt | 1.7.4 + 4.0.1 | Şifre hash (pinned: bcrypt ≥5 uyumsuz) |
| matplotlib | 3.8.4 | Feature importance grafikleri |
| python-dotenv | 1.0.1 | .env yönetimi |

### Frontend
| Teknoloji | Versiyon | Kullanım |
|-----------|----------|----------|
| React | 19.2.4 | UI framework |
| TypeScript | ~6.0.2 | Tip güvenliği |
| Vite | 8.0.4 | Build tool + dev proxy |
| Tailwind CSS | 3.4.19 | Utility-first styling |
| Leaflet + react-leaflet | 1.9.4 + 5.0.0 | Harita |
| Axios | 1.15.0 | HTTP client |
| React Router DOM | 7.14.1 | SPA routing |
| lucide-react | 1.8.0 | İkonlar |
| react-hook-form | 7.72.1 | Form yönetimi |

---

## 3. Veri Seti

Tüm veriler **tamamen sentetik** olup Sivas Mart 2025 için üretilmiştir.

| Dosya | Satır Sayısı | İçerik |
|-------|-------------|--------|
| `bus_stops.csv` | 62 | 5 hat, 62 durak — stop_id, koordinat, stop_type, is_terminal |
| `bus_trips.csv` | 13.440 | Sefer planlaması — departure, duration, delay, occupancy, weather |
| `stop_arrivals.csv` | 4.478 | Durak bazlı varış gecikmesi kayıtları — delay_min, passengers_waiting |
| `weather_observations.csv` | 300 | Saatlik hava gözlemi — transit_delay_risk, passenger_demand_multiplier |
| `passenger_flow.csv` | 3.568 | Saatlik yolcu akışı — stop + hour_of_day → avg_passengers_waiting |

**Koordinatlar:** `bus_stops.csv` içindeki latitude/longitude kolonları gerçek Sivas koordinatlarını içeriyor (elle girilmiş). Durak isimleri ise mock (otomatik üretilmiş Türkçe isimler: "Devlet Hastanesi", "Terminal", vb.).

---

## 4. Makine Öğrenmesi

### Eğitim Pipeline (`backend/ml/train.py`)

**Veri birleştirme adımları:**
1. `stop_arrivals.csv` ana tablo
2. `bus_trips.csv` LEFT JOIN (speed_factor, traffic_level, weather verileri)
3. `bus_stops.csv` LEFT JOIN (is_terminal, is_transfer_hub, stop_type)
4. `weather_observations.csv` → `merge_asof` ile zaman eşleştirme (transit_delay_risk, passenger_demand_multiplier)
5. `passenger_flow.csv` → stop_id + hour_of_day üzerinden avg_passengers_waiting

**Encoding:**
- `traffic_level`: low=0, moderate=1, high=2, congested=3
- `weather_condition`: clear=0, cloudy=1, rain=2, fog=3, wind=4, snow=5
- `stop_type`: sklearn LabelEncoder (kaydedilip inference'ta kullanılır)
- `time_bucket`: early_morning=0 ... night=5

---

### Model 1 — Gecikme Tahmini (`delay_model.pkl`)

**Hedef değişken:** `delay_min` (dakika cinsinden varış gecikmesi)  
**Algoritma:** XGBRegressor  
**Hiperparametreler:** n_estimators=300, max_depth=6, learning_rate=0.05, subsample=0.8  
**Validasyon:** TimeSeriesSplit (5 fold) — zaman sıralı bölme  
**Metrik:** MAE

**Feature listesi (sırasıyla):**
```
hour_of_day, day_of_week, is_weekend, stop_sequence,
cumulative_delay_min, speed_factor, traffic_level_enc,
weather_enc, temperature_c, precipitation_mm, wind_speed_kmh,
is_terminal, is_transfer_hub, stop_type_enc,
departure_delay_min, minutes_to_next_bus
```

**Elde edilen sonuç:**
> Delay MAE (CV): **0.110 ± 0.072 dakika**  
> Hedef: < 5 dakika → ✅ **KARŞILANDI** (hedefin ~45x altında)

**Not:** Bu düşük MAE'nin temel sebebi sentetik verinin az varyansa sahip olması. Gerçek dünya verisinde bu değer daha yüksek olurdu.

---

### Model 2 — Kalabalık Tahmini (`crowd_model.pkl`)

**Hedef değişken:** `passengers_waiting` (bekleme sayısı, tam sayı)  
**Algoritma:** XGBRegressor  
**Hiperparametreler:** n_estimators=300, max_depth=5, learning_rate=0.05, min_child_weight=3  
**Post-processing:** `max(0, round(pred))` — negatif değer önleme  
**Metrik:** RMSE

**Feature listesi (sırasıyla):**
```
hour_of_day, day_of_week, is_weekend, stop_type_enc,
minutes_to_next_bus, weather_enc, avg_passengers_waiting,
time_bucket_enc, delay_min, transit_delay_risk,
passenger_demand_multiplier
```

**Not:** `delay_min` feature'ı gecikme modelinin tahmininden geliyor (pipeline bağımlılığı).

**Elde edilen sonuç:**
> Crowd RMSE (CV): **8.900 ± 1.873 kişi**  
> Hedef: < 8 kişi → ❌ **KARŞILANAMADI** (8.9 vs hedef 8.0)

---

### Model 3 — Crowding Sınıflandırması (`crowding_model.pkl`)

**Hedef değişken:** `crowding_level` — 5 sınıf: `empty / light / moderate / busy / crowded`  
**Kaynak tablo:** `passenger_flow.csv` (3.568 satır)  
**Algoritma:** XGBClassifier  
**Hiperparametreler:** n_estimators=300, max_depth=5, learning_rate=0.05  
**Validasyon:** StratifiedKFold (5 fold, shuffle=True)  
**Metrik:** Accuracy + Classification Report  
**Feature listesi:** Model 2 ile aynı 11 feature (CROWD_FEATURES)

**Kaydedilen dosyalar:**
- `crowding_model.pkl` — sınıflandırıcı
- `crowding_features.pkl` — feature listesi
- `crowding_label_encoder.pkl` — int → string etiket çevirici

**Elde edilen sonuç:**
> Crowding Accuracy (CV): **1.0000 ± 0.0000**  
> **Not:** Sentetik verinin deterministik pattern içermesinden kaynaklanıyor; etiketler `avg_passengers_waiting` aralıklarıyla doğrudan eşleşiyor.

**`/predict` response'una eklenen alan:**
```json
"crowding_label": "busy"
```

---

### Model Serving

- 8 model dosyası startup'ta `joblib.load()` ile RAM'e yüklenir (`app.state.models`)
- Her tahmin isteği: `predict()` < 100ms (RAM singleton)
- Model yoksa fallback: delay=8.2 dk, crowd=34 kişi, confidence="low", crowding_label="moderate"
- `/health` endpoint'i: core modeller yüklüyse `predict_service="active"`, yoksa `"degraded"`

---

## 5. Backend API Endpoint Listesi

| Method | Path | Gerçek/Mock | Açıklama |
|--------|------|-------------|----------|
| GET | `/` | — | API bilgisi |
| GET | `/health` | Gerçek | Model yükleme durumu |
| POST | `/predict` | **Gerçek (XGBoost)** | Gecikme + kalabalık + crowding_label tahmini |
| POST | `/users` | Gerçek (SQLite) | Kullanıcı kaydı |
| GET | `/users/{id}` | Gerçek (SQLite) | Profil bilgisi |
| PATCH | `/users/{id}` | Gerçek (SQLite) | Profil güncelleme |
| GET | `/users/{id}/session` | Gerçek (SQLite) | Bebek arabası oturum durumu |
| PATCH | `/users/{id}/session` | Gerçek (SQLite) | Bebek arabası güncelleme |
| GET | `/stops` | CSV | Durak listesi (bus_stops.csv) |
| GET | `/stops/{stop_id}` | CSV | Tek durak bilgisi |
| GET | `/stops/{stop_id}/upcoming` | **Simüle** | Yaklaşan otobüsler |
| GET | `/accessibility/warning` | Gerçek (SQLite) | Doluluk uyarısı |
| POST | `/challenge/beat-the-bus` | Gerçek (hesaplama) | Yürüyüş vs otobüs |
| POST | `/feedback/live-crowd` | Gerçek (SQLite) | Kalabalık doğrulama |
| POST | `/feedback/post-trip` | Gerçek (SQLite) | Yolculuk değerlendirmesi |
| GET | `/bus-positions` | **Simüle** | Canlı otobüs konumları |
| GET | `/routes/all/shapes` | **OSRM API** | Hat geometrileri |
| GET | `/routes/{line_id}/shape` | **OSRM API** | Tek hat geometrisi |
| GET | `/weather` | **Open-Meteo API** | Anlık Sivas hava durumu |

---

## 6. Dış API'ler

### Open-Meteo (Hava Durumu)
- **URL:** `https://api.open-meteo.com/v1/forecast?latitude=39.75&longitude=37.01&current=temperature_2m,precipitation,windspeed_10m,weather_code`
- **Ücretsiz, API key gerektirmez**
- Sivas'ın anlık sıcaklık, yağış, rüzgar ve WMO hava kodu döndürür
- WMO kodları → ML vocabularisi (clear/cloudy/rain/snow/fog/wind)
- Sunucu taraflı 5 dakikalık cache
- `/predict` çağrılarına gerçek hava koşulları otomatik eklenir

### OSRM (Rota Çizimi)
- **URL:** `https://router.project-osrm.org/route/v1/driving/`
- **Ücretsiz, API key gerektirmez**
- Durak koordinatlarını gerçek yollara snap eder
- Yol üzerinde polyline koordinatları döndürür (binalardan geçmez)
- Sunucu taraflı kalıcı cache (server ömrü boyunca)
- Her hat için bir kez çağrılır, sonra cache'den döner (~0.3s)

---

## 7. Mock / Simüle Edilmiş Veriler

### Durak İsimleri (Mock)
`bus_stops.csv`'de durak isimleri yok. `route_shapes.py` stop_type'a göre otomatik Türkçe isim üretiyor:
- `terminal` → "Merkez Terminal", "Sanayi Garaj" vb.
- `hospital` → "Devlet Hastanesi", "Numune Hastanesi", "Sağlık Merkezi"
- `university` → "Üniversite", "Kampüs", "Fakülte", "Yurt"
- `market` → "Çarşı", "Pazar", "Alışveriş Merkezi"
- `residential` → "Mahalle", "Konutlar", "Siteler"
- `regular` → "Durak"

### Canlı Otobüs Konumları (Simüle)
`GET /bus-positions` gerçek GPS verisi yok. `bus_trips.csv`'deki sefer saatlerine bakarak:
- Şu an hareket halinde olan seferleri tespit eder (departure_time + duration ile)
- Otobüsün güzergah üzerindeki ilerlemesini `progress = elapsed / total_duration` ile hesaplar
- **OSRM road polyline üzerinde** interpolasyon yapar (düz çizgi değil)
- Her hat için 1-3 simüle otobüs döndürür

### Yaklaşan Otobüsler (Simüle)
`GET /stops/{stop_id}/upcoming` gerçek AVM verisi yok. `bus_trips.csv` sefer saatlerinden:
- Şu anki saate göre sonraki 3 seferi hesaplar
- Durak sırasına orantılı varış tahmini yapar (`stop_sequence / total_stops`)
- Gerçek zamanlama değil, planlanmış saate göre

---

## 8. Veritabanı Şeması (SQLite)

### `users`
| Kolon | Tip | Kısıt |
|-------|-----|-------|
| id | Integer | PK, autoincrement |
| username | String(50) | unique, indexed |
| email | String(100) | unique, indexed |
| hashed_password | String | bcrypt hash |
| is_disabled | Boolean | default=False |
| has_stroller_profile | Boolean | default=False |
| created_at | DateTime | server_default=now() |

### `user_sessions`
| Kolon | Tip | Açıklama |
|-------|-----|----------|
| id | Integer | PK |
| user_id | FK | users.id, cascade delete |
| stroller_active_until | DateTime | 90dk oturum süresi |
| last_asked_at | DateTime | Son soru zamanı |
| session_date | Date | Günlük oturum |

### `feedbacks`
| Kolon | Tip | Açıklama |
|-------|-----|----------|
| id | Integer | PK |
| user_id | FK | users.id |
| feedback_type | String(30) | "crowd_confirm" / "post_trip_review" |
| crowd_actual | String(20) | "empty" / "as_predicted" / "crowded" |
| rating | Integer | 1-5 yıldız |
| is_on_time | Boolean | Zamanında geldi mi |
| comment | Text | Max 500 karakter |

---

## 9. Frontend Sayfaları ve Bileşenleri

### Sayfalar
| Sayfa | Path | İçerik |
|-------|------|--------|
| MapPage | `/` | Harita + durak tıklama + tahmin paneli |
| ProfilePage | `/profile` | Kullanıcı ayarları + hesap kurtarma |

### Harita Katmanları (`MapContainer.tsx`)
1. **OpenStreetMap tile layer** — gerçek harita
2. **Route polylines** — OSRM'den gelen yol üzeri hatlar (5 renk)
3. **Stop markers** — OSRM'e snap edilmiş konumlarda renkli daireler; terminaller için kalıcı isim etiketi
4. **BusStopMarker** — popup'ta yaklaşan otobüs listesi (simüle)
5. **BusMarker** — 🚌 emoji ikonlu canlı otobüsler (simüle, OSRM polyline üzerinde)

### Kullanıcı Akışı
```
Durak tıkla
    → has_stroller_profile=true VE should_ask=true?
        → Evet: StrollerModal açılır (Bebek arabası var mı?)
            → Evet/Hayır: PATCH /users/{id}/session
        → Hayır: direkt tahmin
    → POST /predict (XGBoost)
    → PredictionCard göster
        → CrowdBar (progress bar)
        → AccessibilityAlert (eğer doluluk ≥ %80 VE kullanıcı uygunsa)
        → CrowdConfirmButtons (kalabalık crowdsource)
        → "Beat the Bus" butonu → BeatTheBusModal
        → "Trip Complete" butonu → PostTripModal
```

### Hook'lar
| Hook | Açıklama |
|------|----------|
| `usePrediction.ts` | POST /predict çağrısı; 30s cache; gerçek weather fetch |
| `useUserSession.ts` | GET/PATCH /users/{id}/session |
| `useFeedback.ts` | POST /feedback/live-crowd ve /post-trip |

---

## 10. Yenilikçi Özellikler (Plana Göre)

| Özellik | Durum | Açıklama |
|---------|-------|----------|
| ML gecikme tahmini | ✅ Çalışıyor | XGBoost, MAE=0.11 dk |
| ML kalabalık tahmini | ✅ Çalışıyor | XGBoost, RMSE=8.9 kişi |
| ML crowding sınıflandırması | ✅ Çalışıyor | XGBClassifier, Accuracy=%100, 5 sınıf |
| Gerçek zamanlı hava durumu | ✅ Çalışıyor | Open-Meteo API, ücretsiz |
| Erişilebilirlik uyarısı (engelli/stroller) | ✅ Çalışıyor | SQLite oturum + doluluk eşiği |
| Bebek arabası 90dk oturum önbelleği | ✅ Çalışıyor | Tekrar soru sormaz |
| "Otobüsü Yen!" gamification | ✅ Çalışıyor | Haversine, kalori, mini harita |
| Kalabalık crowdsource (Waze tipi) | ✅ Çalışıyor | Feedback DB'ye kaydediliyor |
| Yolculuk sonu değerlendirme | ✅ Çalışıyor | 5 yıldız + yorum |
| Hesap kurtarma | ✅ Çalışıyor | ID + username ile |
| Canlı otobüs konumları | ✅ Çalışıyor (simüle) | Gerçek GPS yok |
| OSRM yol üzeri hatlar | ✅ Çalışıyor | Binalardan geçmiyor |
| Durak isim etiketleri | ✅ Çalışıyor (mock) | Gerçek isimler yok |

---

## 11. Hackathon Kriterleri Değerlendirmesi

### Kriter 1 — Gecikme MAE < 5 dakika
**Sonuç:** 0.110 ± 0.072 dakika → ✅ **KARŞILANDI**  
**Not:** Hedefin ~45 katı iyi. Sentetik verinin düşük gürültüsünden kaynaklıyor; gerçek veride bu değer artabilir.

### Kriter 2 — Kalabalık RMSE < 8 kişi
**Sonuç:** 8.900 ± 1.873 kişi → ❌ **KARŞILANAMADI** (0.9 kişi fark)  
**Sebep:** Yolcu sayısı tahmininde hava durumu ve gecikme etkileşimi yeterince öğrenilememiş olabilir.  
**Olası iyileştirme:** Feature engineering (saatlik hava-gecikme etkileşim terimleri), daha derin ağaç.

### Kriter 3 — Tahmin arayüzü < 1 saniye
**Sonuç:** Model RAM'de, tahmin < 100ms → ✅ **KARŞILANDI**  
**Ancak:** Durak tıklamada hem tahmin hem de hava durumu isteği paralel gidiyor; toplam ≈ 200-400ms.

### Ek — Crowding Sınıflandırması
**Sonuç:** Accuracy %100 (CV) → ✅ **KARŞILANDI**  
**Not:** Sentetik verinin deterministik yapısından kaynaklanıyor. `/predict` response'unda `crowding_label` alanı olarak (empty / light / moderate / busy / crowded) sunuluyor.

---

## 12. Eksikler / Gerçek Olmayan Kısımlar

| Eksik | Açıklama |
|-------|----------|
| Gerçek GPS | Otobüs konumları sefer saatinden simüle edilmiş |
| Gerçek durak isimleri | Mock Türkçe isimler; CSV'de yok |
| Gerçek yolcu sayısı | Sentetik `passenger_flow.csv` |
| Gerçek gecikme geçmişi | Sentetik `stop_arrivals.csv` |
| Crowdsource geri bildirimi model'e yansımıyor | Feedback DB'ye kaydediliyor ama model yeniden eğitilmiyor — bkz. Bölüm 15 |
| Authentication | Şifre hash var ama JWT/token yok; userId localStorage'da düz tutuluyor |
| HTTPS | Production deployment yok |
| Gerçek Sivas GTFS verisi | Mevcut değil, CSV sentetik |

---

## 13. Test Suite

### Yapı

```
backend/tests/
├── conftest.py          # Ortak fixture'lar
├── test_users.py        # POST/GET/PATCH /users  (8 test)
├── test_sessions.py     # GET/PATCH /users/{id}/session  (7 test)
├── test_predict.py      # POST /predict  (7 test)
├── test_accessibility.py# GET /accessibility/warning  (6 test)
├── test_challenge.py    # POST /challenge/beat-the-bus  (6 test)
├── test_feedback.py     # POST /feedback/*  (7 test)
├── test_stops.py        # GET /stops  (6 test)
├── test_health.py       # GET / ve /health  (4 test)
└── test_ml_pipeline.py  # .pkl dosyaları + model davranışı  (7 test)
```

**Toplam: 58 test — 58 passed ✅**

### Tasarım Kararları

| Konu | Yaklaşım |
|------|----------|
| Veritabanı izolasyonu | Her test kendi `test_predictive_transit.db` dosyasını alır, test sonrası silinir |
| ML modelleri | `MagicMock` ile sahte `predict()` — gerçek `.pkl` yüklenmez |
| `app.state.models` | `client` fixture'da lifespan sonrası mock ile override edilir |
| Dış API'ler | `weather.py`, `bus_positions.py`, `route_shapes.py` router'ları test kapsamı dışında (HTTP mock gerekirdi) |
| Timezone | SQLite naive datetime döndürür; `accessibility.py`'deki karşılaştırma buna göre düzeltildi |
| Test bağımsızlığı | Her fixture `scope="function"` — testler arası durum geçişmez |

### Coverage Özeti

| Kategori | Cover |
|----------|------:|
| `schemas.py`, `models.py`, challenge, feedback | **%100** |
| predict, accessibility, sessions router'ları | **%95–96** |
| `main.py`, users router | **%88–94** |
| stops router | **%82** |
| `ml/predict.py` | **%68** |
| weather, bus_positions, route_shapes | **%30–37** (dış HTTP mock yok) |
| **Toplam** | **%81** |

### Çalıştırma

```bash
# Tüm testler
python -m pytest

# Coverage ile
python -m pytest --cov=backend --cov-report=term-missing
```

---

## 14. Sunucu Başlatma

### Aktif Servisler

| Servis | URL | Not |
|--------|-----|-----|
| Web Uygulaması (React) | **http://localhost:8000** | Frontend build + FastAPI tek port |
| API Docs (Swagger) | http://localhost:8000/docs | FastAPI auto-generated |
| API Health | http://localhost:8000/health | Model yükleme durumu |

> Frontend artık ayrı bir dev server gerektirmiyor.  
> React build dosyaları (`frontend/dist/`) FastAPI tarafından servis ediliyor.

### Mimari (Tek Port)

```
Tarayıcı → http://localhost:8000/
    GET /          → frontend/dist/index.html  (React SPA)
    GET /assets/*  → frontend/dist/assets/*    (JS/CSS)
    GET /api/*     → FastAPI router (prefix /api otomatik soyulur)
    GET /health    → FastAPI health endpoint
    GET /docs      → Swagger UI
```

### Başlatma Komutları

```bash
# 1. Frontend build (kod değişince yeniden çalıştır)
cd frontend
npm run build

# 2. Backend (proje kökünden) — tek komut yeterli
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### ML Modeli Yeniden Eğitme

```bash
python -m backend.ml.train
```

**Önemli:** Backend başlar başlamaz `/routes/all/shapes` ilk çağrısı OSRM'e gider (~5 saniye). Sonraki çağrılar cache'den ~0.3 saniyede döner. Axios timeout 30 saniyeye ayarlanmış.

---

## 15. Olası İyileştirmeler

### Crowdsource → Model Geri Besleme Pipeline'ı

Şu an `POST /feedback/live-crowd` ile toplanan `crowd_actual` verisi DB'ye kaydediliyor ama ML modeli bu bilgiden haberdar olmuyor. Üç geliştirme seçeneği:

| Yaklaşım | Açıklama | Zorluk |
|----------|----------|--------|
| **Periyodik yeniden eğitim** | Geceleri feedback verisini `passenger_flow.csv`'ye ekleyip `python -m backend.ml.train` cron ile çalıştır | Düşük |
| **Incremental learning** | `XGBClassifier.fit(..., xgb_model=mevcut_model)` ile sadece yeni veriyle modeli güncelle; pkl dosyasını yerinde yenile | Orta |
| **Online learning** | Her feedback geldiğinde anlık model güncellemesi — XGBoost bu modu doğrudan desteklemiyor, SGD tabanlı alternatif gerekir | Yüksek |

Hackathon kapsamı için periyodik yeniden eğitim yeterli: feedback tablosunu sorgu ile `passenger_flow.csv` formatına dönüştür, mevcut CSV ile birleştir, `train.py`'ı çalıştır.

### Diğer Olası Geliştirmeler

| Konu | Açıklama |
|------|----------|
| JWT Authentication | Şu an userId localStorage'da düz tutuluyor; Bearer token ile güvenli hale getirilebilir |
| Gerçek GPS entegrasyonu | Sivas Belediyesi açık veri API'si varsa `/bus-positions` simülasyonu gerçek veriye bağlanabilir |
| Gerçek GTFS verisi | Belediyeden GTFS feed alınırsa tüm sentetik CSV'ler replace edilebilir |
| Feedback → CSV dönüşümü | `crowd_actual` değerlerini `avg_passengers_waiting` olarak normalize edip eğitim verisine eklemek için ETL script yazılabilir |
| HTTP mock ile %100 coverage | `weather.py`, `bus_positions.py`, `route_shapes.py` için `unittest.mock.patch("httpx.AsyncClient.get")` ile test yazılabilir |

---

## 16. Açık Sorular (Grup İncelemesi Gerekli)

### L04 Hat Güzergahı Boşluğu

**Sorun:** Haritada mor L04 (Esentepe - Meydan) hattında STP-L04-09 ile STP-L04-10 arasında görsel bir boşluk / sapma oluşuyor.

**Koordinatlar:**
- STP-L04-09: `39.741955, 36.964926`
- STP-L04-10: `39.733895, 36.978536` (~1.5 km doğu/güneydoğu atlama)

**Muhtemel sebep:** Bu iki durak arasındaki alan "Altıntabağın Tepesi (1365 m)" dağlık bölgesine denk geliyor. OSRM yol buluyor fakat dağı dolaşan uzun bir güzergah çiziyor; bu da görsel sapma izlenimi veriyor.

**Soru grup için:** STP-L04-10'un gerçek konumu ne olmalı? Elimizde gerçek hat güzergahı bilgisi var mı? Durağı şehir içi bir noktaya (örn. `39.740, 36.975` civarı) taşımak sorunu çözer mi?
