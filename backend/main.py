import logging
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from backend.database import Base, engine
from backend.routers import (
    accessibility,
    bus_positions,
    challenge,
    feedback,
    predict,
    route_shapes,
    sessions,
    stops,
    users,
    weather,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR  = Path(__file__).parent / "ml" / "models"
DIST_DIR   = Path(__file__).parent.parent / "frontend" / "dist"


class StripApiPrefixMiddleware(BaseHTTPMiddleware):
    """Frontend /api/... çağrılarını FastAPI route'larıyla eşleştirmek için prefix soyar."""
    async def dispatch(self, request: Request, call_next):
        if request.scope["path"].startswith("/api/"):
            request.scope["path"] = request.scope["path"][4:]
            request.scope["raw_path"] = request.scope["path"].encode("latin-1")
        return await call_next(request)

# Maps app.state.models key -> pkl filename
MODEL_FILES = {
    "delay":                  "delay_model.pkl",
    "crowd":                  "crowd_model.pkl",
    "delay_features":         "delay_features.pkl",
    "crowd_features":         "crowd_features.pkl",
    "label_encoders":         "label_encoders.pkl",
    "crowding":               "crowding_model.pkl",
    "crowding_features":      "crowding_features.pkl",
    "crowding_label_encoder": "crowding_label_encoder.pkl",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")

    app.state.models = {}
    for key, filename in MODEL_FILES.items():
        path = MODEL_DIR / filename
        if path.exists():
            try:
                app.state.models[key] = joblib.load(path)
                logger.info("Model loaded: %s", filename)
            except Exception as exc:
                logger.warning("Failed to load model %s: %s", filename, exc)
        else:
            logger.warning("Model file not found: %s", path)

    yield
    # ── Shutdown (no-op) ─────────────────────────────────────────────────────


app = FastAPI(
    title="Predictive Transit API",
    description="Real-time bus arrival delay and crowd prediction for Sivas city transit.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(StripApiPrefixMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router,          prefix="/users",         tags=["Users"])
app.include_router(sessions.router,       prefix="/users",         tags=["Sessions"])
app.include_router(predict.router,        prefix="",               tags=["Prediction"])
app.include_router(stops.router,          prefix="/stops",         tags=["Stops"])
app.include_router(accessibility.router,  prefix="/accessibility", tags=["Accessibility"])
app.include_router(challenge.router,      prefix="/challenge",     tags=["Gamification"])
app.include_router(feedback.router,       prefix="/feedback",      tags=["Feedback"])
app.include_router(bus_positions.router,  prefix="/bus-positions", tags=["Canlı Otobüsler"])
app.include_router(route_shapes.router,   prefix="/routes",        tags=["Hat Güzergahları"])
app.include_router(weather.router,        prefix="/weather",       tags=["Hava Durumu"])


@app.get("/api-info", tags=["Root"])
def root():
    return {"app": "Predictive Transit API", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["Root"])
def health(req: Request):
    loaded = getattr(req.app.state, "models", {})
    models_status = {
        filename.replace(".pkl", ""): ("ready" if key in loaded else "not_loaded")
        for key, filename in MODEL_FILES.items()
    }
    has_core = all(k in loaded for k in ("delay", "crowd", "delay_features", "crowd_features"))
    return {
        "status": "ok",
        "models": models_status,
        "predict_service": "active" if has_core else "degraded",
    }


# ── Frontend (SPA) ────────────────────────────────────────────────────────────
if DIST_DIR.exists():
    _assets_dir = DIST_DIR / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="static-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        target = DIST_DIR / full_path
        if target.is_file():
            return FileResponse(str(target))
        return FileResponse(str(DIST_DIR / "index.html"))
