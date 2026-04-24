# Predictive Transit
## Anadolu Hackathon 2026 | Case 2 — Real-Time Bus Prediction

**Team:** Ctrl-Alt-Defeat
**Result:** 🥈 **6th in category · 14th overall**
**Leaderboard:** https://dashboard.hackaton.sivas.edu.tr/leaderboard

---

### What We Built

A real-time web application for Sivas city buses that predicts arrival delays and stop crowding using machine learning, displayed on an interactive map.

**Live at:** `http://<vm-ip>:8000`

---

### ML Results

| Model | Metric | Result | Target | Status |
|-------|--------|--------|--------|--------|
| Delay prediction (XGBoost) | MAE | **0.110 ± 0.072 min** | < 5 min | ✅ Met |
| Crowd prediction (XGBoost) | RMSE | **7.475 ± 0.509 people** | < 8 people | ✅ Met |
| Crowding classification (XGBoost) | Accuracy | **100%** | — | ✅ |
| Prediction UI response | Latency | **< 100ms** | < 1s | ✅ Met |

---

### Features

- **Delay & crowd prediction** — XGBoost models, real weather from Open-Meteo
- **Live map** — 5 bus lines on real roads (OSRM), animated bus positions, stop markers
- **Route congestion opacity** — polyline darkness reflects live delay + occupancy
- **Stop & place search** — search by stop ID or location name, fly to stop
- **Accessibility warning** — crowding alert for wheelchair/stroller users only
- **Beat the Bus** — walking vs bus challenge with calorie estimate
- **Crowd crowdsourcing** — Waze-style real feedback collection
- **Weather badge** — live temperature + condition from Open-Meteo

---

### Quick Start

```bash
# Unzip and enter project
cd predictive-transit

# Install dependencies
pip install -r requirements.txt

# Start server (frontend + backend on one port)
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser.

---

### Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Leaflet |
| Backend | FastAPI, Uvicorn, SQLite, SQLAlchemy |
| ML | XGBoost, scikit-learn, pandas |
| External APIs | Open-Meteo (weather), OSRM (road routing) |

---

### Dataset

All data is **fully synthetic**, generated for Sivas March 2025.

| File | Rows | Description |
|------|------|-------------|
| `bus_stops.csv` | 62 | 5 lines, 62 stops — coordinates, stop_type |
| `bus_trips.csv` | 13,440 | Trip schedule — departure, delay, occupancy, weather |
| `stop_arrivals.csv` | 4,478 | Per-stop arrival delay — delay_min, passengers_waiting |
| `weather_observations.csv` | 300 | Hourly weather — transit_delay_risk, demand multiplier |
| `passenger_flow.csv` | 3,568 | Hourly crowd stats — avg_passengers_waiting, crowding_level |

---

### Project Structure

```
predictive-transit/
├── backend/
│   ├── main.py               # FastAPI app, static file serving
│   ├── routers/              # API endpoints
│   └── ml/
│       ├── train.py          # Model training
│       ├── predict.py        # Inference helpers
│       └── models/           # Trained .pkl files
├── frontend/
│   ├── src/                  # React source
│   └── dist/                 # Built files (served by FastAPI)
├── bus_stops.csv
├── bus_trips.csv
├── stop_arrivals.csv
├── weather_observations.csv
├── passenger_flow.csv
├── requirements.txt
└── PROJECT_REPORT.md         # Full technical report
```

---

### API

| Endpoint | Description |
|----------|-------------|
| `POST /api/predict` | Delay + crowd + crowding label prediction |
| `GET /api/bus-positions` | Simulated live bus positions |
| `GET /api/routes/all/shapes` | Route geometries (OSRM road-snapped) |
| `GET /api/weather` | Live Sivas weather (Open-Meteo) |
| `GET /api/stops/{id}/upcoming` | Upcoming buses for a stop |
| `GET /health` | Service health + model status |
| `GET /docs` | Swagger UI |
