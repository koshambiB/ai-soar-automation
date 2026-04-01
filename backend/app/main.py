"""
backend/app/main.py
--------------------
FastAPI application entry point.
Loads ML model + SHAP on startup, mounts all routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .models.ml_model import SOARClassifier
from .explainability.shap_explainer import SHAPExplainer
from .api import alerts, analysis, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── Shared singletons (loaded once at startup) ────────────────────────────────
classifier = SOARClassifier()
explainer  = SHAPExplainer()

app = FastAPI(
    title="AI-SOAR API",
    description="Security Orchestration, Automation and Response - AI Backend",
    version="1.0.0",
)

# ── CORS (allow React dev server) ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    logger.info("Loading ML model...")
    ok = classifier.load()
    if ok:
        explainer.load(classifier)
        logger.info("ML model + SHAP explainer ready")
    else:
        logger.warning("ML model not found - predictions will be unavailable")

    # Make singletons available to routers via app state
    app.state.classifier = classifier
    app.state.explainer  = explainer


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router,   prefix="/api/v1")
app.include_router(alerts.router,   prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"status": "ok", "service": "AI-SOAR API", "version": "1.0.0"}