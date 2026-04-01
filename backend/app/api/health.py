"""
Health check endpoint
"""
from fastapi import APIRouter, Request
from datetime import datetime

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(request: Request):
    classifier = request.app.state.classifier
    explainer  = request.app.state.explainer
    return {
        "status":       "healthy",
        "timestamp":    datetime.utcnow().isoformat(),
        "ml_model":     "loaded" if classifier.is_loaded else "not_loaded",
        "shap":         "ready"  if explainer.is_ready  else "not_ready",
    }