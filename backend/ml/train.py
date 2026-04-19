"""
Predictive Transit - ML Training Script
Calistirma: python -m backend.ml.train
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import TimeSeriesSplit, StratifiedKFold
from sklearn.metrics import mean_absolute_error, accuracy_score, classification_report as cls_report
from xgboost import XGBRegressor, XGBClassifier

# --- Paths ---
DATA_DIR = Path(__file__).parent.parent.parent
MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

# --- Feature lists (plan'daki sırayla) ---
DELAY_FEATURES = [
    "hour_of_day", "day_of_week", "is_weekend", "stop_sequence",
    "cumulative_delay_min", "speed_factor", "traffic_level_enc",
    "weather_enc", "temperature_c", "precipitation_mm", "wind_speed_kmh",
    "is_terminal", "is_transfer_hub", "stop_type_enc",
    "departure_delay_min", "minutes_to_next_bus"
]

CROWD_FEATURES = [
    "hour_of_day", "day_of_week", "is_weekend", "stop_type_enc",
    "minutes_to_next_bus", "weather_enc", "avg_passengers_waiting",
    "time_bucket_enc", "delay_min", "transit_delay_risk",
    "passenger_demand_multiplier"
]

# --- Encoding maps ---
traffic_map = {"low": 0, "moderate": 1, "high": 2, "congested": 3}
weather_map = {"clear": 0, "cloudy": 1, "rain": 2, "fog": 3, "wind": 4, "snow": 5}
time_bucket_map = {
    "early_morning": 0, "morning_peak": 1, "midday": 2,
    "evening_peak": 3, "evening": 4, "night": 5
}

# ── 1. Veri Yükleme ────────────────────────────────────────────────────────────
print("Veri yükleniyor...")

# CSV dosyaları proje kökünde; data/ alt klasörünü de dene
def _find_csv(name: str) -> Path:
    """Önce data/ alt klasörüne bak, yoksa proje kökünde ara."""
    sub = DATA_DIR / "data" / name
    if sub.exists():
        return sub
    root = DATA_DIR / name
    if root.exists():
        return root
    raise FileNotFoundError(f"{name} bulunamadı. Beklenen: {sub} veya {root}")

stop_arrivals   = pd.read_csv(_find_csv("stop_arrivals.csv"))
bus_trips       = pd.read_csv(_find_csv("bus_trips.csv"))
bus_stops       = pd.read_csv(_find_csv("bus_stops.csv"))
weather_obs     = pd.read_csv(_find_csv("weather_observations.csv"))
passenger_flow  = pd.read_csv(_find_csv("passenger_flow.csv"))

print(f"  stop_arrivals: {len(stop_arrivals):,} satır")
print(f"  bus_trips:     {len(bus_trips):,} satır")
print(f"  bus_stops:     {len(bus_stops):,} satır")
print(f"  weather_obs:   {len(weather_obs):,} satır")
print(f"  passenger_flow:{len(passenger_flow):,} satır")

# ── 2. Birleştirme ─────────────────────────────────────────────────────────────
print("Tablolar birleştiriliyor...")

# 2a. stop_arrivals + bus_trips (departure_delay_min, temperature_c, precipitation_mm, wind_speed_kmh)
trip_cols = ["trip_id", "departure_delay_min", "temperature_c", "precipitation_mm", "wind_speed_kmh"]
df = stop_arrivals.merge(bus_trips[trip_cols].drop_duplicates("trip_id"), on="trip_id", how="left")

# 2b. + bus_stops (is_terminal, is_transfer_hub; stop_type zaten stop_arrivals'da var)
stop_cols = ["stop_id", "is_terminal", "is_transfer_hub"]
df = df.merge(bus_stops[stop_cols].drop_duplicates("stop_id"), on="stop_id", how="left")

# 2c. weather_observations — merge_asof ile en yakın gözlemi eşleştir
weather_obs["timestamp"] = pd.to_datetime(weather_obs["timestamp"])
df["planned_arrival"] = pd.to_datetime(df["planned_arrival"])
df = df.sort_values("planned_arrival").reset_index(drop=True)

weather_sorted = (
    weather_obs[["timestamp", "transit_delay_risk", "passenger_demand_multiplier"]]
    .sort_values("timestamp")
    .reset_index(drop=True)
)
df = pd.merge_asof(
    df, weather_sorted,
    left_on="planned_arrival",
    right_on="timestamp",
    direction="nearest"
)

# 2d. passenger_flow — stop_id + hour_of_day üzerinden avg_passengers_waiting
flow_agg = (
    passenger_flow
    .groupby(["stop_id", "hour_of_day"])["avg_passengers_waiting"]
    .mean()
    .reset_index()
)
df = df.merge(flow_agg, on=["stop_id", "hour_of_day"], how="left")

# ── 3. Encoding & Doldurma ─────────────────────────────────────────────────────
print("Feature encoding yapılıyor...")

df["traffic_level_enc"]  = df["traffic_level"].map(traffic_map).fillna(1).astype(int)
df["weather_enc"]        = df["weather_condition"].map(weather_map).fillna(0).astype(int)
df["time_bucket_enc"]    = df["time_bucket"].map(time_bucket_map).fillna(2).astype(int)

le_stop_type = LabelEncoder()
df["stop_type_enc"] = le_stop_type.fit_transform(df["stop_type"].fillna("regular"))

# Sayısal sütunları doldur
fill_defaults = {
    "is_terminal": 0,
    "is_transfer_hub": 0,
    "transit_delay_risk": 0.3,
    "passenger_demand_multiplier": 1.0,
    "departure_delay_min": 0.0,
    "temperature_c": 15.0,
    "precipitation_mm": 0.0,
    "wind_speed_kmh": 0.0,
    "avg_passengers_waiting": 34.0,
}
for col, val in fill_defaults.items():
    if col in df.columns:
        df[col] = df[col].fillna(val)

df["is_terminal"]   = df["is_terminal"].astype(int)
df["is_transfer_hub"] = df["is_transfer_hub"].astype(int)
df["is_weekend"]    = df["is_weekend"].astype(int)

# ── 4. Model 1 — delay_model ───────────────────────────────────────────────────
print("\nGecikme modeli eğitiliyor...")

df_delay = df.dropna(subset=["delay_min"]).copy()
X_delay  = df_delay[DELAY_FEATURES].fillna(0)
y_delay  = df_delay["delay_min"]

tscv = TimeSeriesSplit(n_splits=5)
model_delay = XGBRegressor(
    n_estimators=300, max_depth=6, learning_rate=0.05,
    subsample=0.8, random_state=42, n_jobs=-1
)

delay_mae_scores = []
for fold, (train_idx, val_idx) in enumerate(tscv.split(X_delay), 1):
    X_tr, X_val = X_delay.iloc[train_idx], X_delay.iloc[val_idx]
    y_tr, y_val = y_delay.iloc[train_idx], y_delay.iloc[val_idx]
    model_delay.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
    pred = model_delay.predict(X_val)
    mae = mean_absolute_error(y_val, pred)
    delay_mae_scores.append(mae)
    print(f"  Fold {fold}: MAE = {mae:.3f} dk")

# Son eğitim tüm veri üzerinde
model_delay.fit(X_delay, y_delay)

delay_mae_mean = float(np.mean(delay_mae_scores))
delay_mae_std  = float(np.std(delay_mae_scores))

# ── 5. Model 2 — crowd_model ───────────────────────────────────────────────────
print("\nKalabalık modeli eğitiliyor...")

df_crowd = df.dropna(subset=["passengers_waiting"]).copy()
X_crowd  = df_crowd[CROWD_FEATURES].fillna(0)
y_crowd  = df_crowd["passengers_waiting"]

model_crowd = XGBRegressor(
    n_estimators=300, max_depth=5, learning_rate=0.05,
    min_child_weight=3, random_state=42, n_jobs=-1
)

crowd_rmse_scores = []
for fold, (train_idx, val_idx) in enumerate(tscv.split(X_crowd), 1):
    X_tr, X_val = X_crowd.iloc[train_idx], X_crowd.iloc[val_idx]
    y_tr, y_val = y_crowd.iloc[train_idx], y_crowd.iloc[val_idx]
    model_crowd.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
    pred = np.maximum(0, np.round(model_crowd.predict(X_val)))
    rmse = float(np.sqrt(np.mean((y_val.values - pred) ** 2)))
    crowd_rmse_scores.append(rmse)
    print(f"  Fold {fold}: RMSE = {rmse:.3f} kişi")

# Son eğitim tüm veri üzerinde
model_crowd.fit(X_crowd, y_crowd)

crowd_rmse_mean = float(np.mean(crowd_rmse_scores))
crowd_rmse_std  = float(np.std(crowd_rmse_scores))

# ── 6. Model 3 — crowding_model (Classification) ──────────────────────────────
print("\nCrowding sınıflandırma modeli eğitiliyor...")

pf = pd.read_csv(_find_csv("passenger_flow.csv"))

pf["weather_enc"]     = pf["weather_condition"].map(weather_map).fillna(0).astype(int)
pf["time_bucket_enc"] = pf["time_bucket"].map(time_bucket_map).fillna(2).astype(int)
pf["stop_type_enc"]   = pf["stop_type"].map({
    "regular": 0, "terminal": 1, "transfer_hub": 2,
    "university": 3, "hospital": 4, "market": 5, "residential": 6,
}).fillna(0).astype(int)
pf["is_weekend"]                  = pf["is_weekend"].astype(int)
pf["minutes_to_next_bus"]         = 15.0
pf["delay_min"]                   = 0.0
pf["transit_delay_risk"]          = 0.3
pf["passenger_demand_multiplier"] = 1.0

CROWDING_FEATURES = CROWD_FEATURES  # aynı feature listesi

X_crowding = pf[CROWDING_FEATURES].fillna(0)
y_crowding  = pf["crowding_level"]

le_crowding      = LabelEncoder()
y_crowding_enc   = le_crowding.fit_transform(y_crowding)

model_crowding = XGBClassifier(
    n_estimators=300, max_depth=5, learning_rate=0.05,
    random_state=42, n_jobs=-1, eval_metric="mlogloss",
)

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
crowding_acc_scores = []
for fold, (train_idx, val_idx) in enumerate(skf.split(X_crowding, y_crowding_enc), 1):
    X_tr, X_val = X_crowding.iloc[train_idx], X_crowding.iloc[val_idx]
    y_tr, y_val = y_crowding_enc[train_idx], y_crowding_enc[val_idx]
    model_crowding.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
    pred = model_crowding.predict(X_val)
    acc  = accuracy_score(y_val, pred)
    crowding_acc_scores.append(acc)
    print(f"  Fold {fold}: Accuracy = {acc:.4f}")

model_crowding.fit(X_crowding, y_crowding_enc)

crowding_acc_mean = float(np.mean(crowding_acc_scores))
crowding_acc_std  = float(np.std(crowding_acc_scores))

y_pred_crowding = model_crowding.predict(X_crowding)
print("\nCrowding Classification Report:")
print(cls_report(y_crowding_enc, y_pred_crowding, target_names=le_crowding.classes_))

# ── 7. Kaydetme ────────────────────────────────────────────────────────────────
print("\nModeller kaydediliyor...")

joblib.dump(model_delay,                          MODEL_DIR / "delay_model.pkl")
joblib.dump(model_crowd,                          MODEL_DIR / "crowd_model.pkl")
joblib.dump(DELAY_FEATURES,                       MODEL_DIR / "delay_features.pkl")
joblib.dump(CROWD_FEATURES,                       MODEL_DIR / "crowd_features.pkl")
joblib.dump({"stop_type": le_stop_type},          MODEL_DIR / "label_encoders.pkl")
joblib.dump(model_crowding,                       MODEL_DIR / "crowding_model.pkl")
joblib.dump(CROWDING_FEATURES,                    MODEL_DIR / "crowding_features.pkl")
joblib.dump(le_crowding,                          MODEL_DIR / "crowding_label_encoder.pkl")

# ── 8. Feature Importance Grafikleri ──────────────────────────────────────────
def plot_importance(model, feature_names, title, filename):
    importances = model.feature_importances_
    indices = np.argsort(importances)
    fig, ax = plt.subplots(figsize=(10, max(5, len(feature_names) * 0.5)))
    ax.barh(range(len(indices)), importances[indices], align="center")
    ax.set_yticks(range(len(indices)))
    ax.set_yticklabels([feature_names[i] for i in indices])
    ax.set_xlabel("Importance")
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(MODEL_DIR / filename, dpi=100)
    plt.close(fig)
    print(f"  Grafik kaydedildi: {filename}")

plot_importance(model_delay, DELAY_FEATURES,
                "Delay Model — Feature Importance",
                "feature_importance_delay.png")
plot_importance(model_crowd, CROWD_FEATURES,
                "Crowd Model — Feature Importance",
                "feature_importance_crowd.png")

# ── 9. Sonuç ──────────────────────────────────────────────────────────────────
print(f"\nDelay MAE (CV):       {delay_mae_mean:.3f} +/- {delay_mae_std:.3f} dk")
print(f"Crowd RMSE (CV):      {crowd_rmse_mean:.3f} +/- {crowd_rmse_std:.3f} kişi")
print(f"Crowding Accuracy (CV): {crowding_acc_mean:.4f} +/- {crowding_acc_std:.4f}")
print("Modeller kaydedildi: backend/ml/models/")
