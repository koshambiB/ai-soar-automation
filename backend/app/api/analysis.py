"""
Analysis API - ML prediction + SHAP explanation endpoints
"""
from fastapi import APIRouter, HTTPException, Request
import logging

from ..core.database import get_connection, get_cursor
from ..analysis.feature_extractor import FeatureExtractor
from ..explainability.shap_explainer import generate_full_explanation

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analysis"])

_extractor = FeatureExtractor()


@router.post("/analysis/predict")
def predict(body: dict, request: Request):
    """
    Run ML prediction + SHAP explanation on a raw alert dict.
    Used for real-time analysis of incoming alerts.
    """
    classifier = request.app.state.classifier
    explainer  = request.app.state.explainer

    try:
        features   = _extractor.extract_features(body)
        ml_result  = classifier.predict(features)
        shap_result = explainer.explain(features)

        return {
            "alert_id":    body.get("alert_id", "UNKNOWN"),
            "features":    features,
            "ml_result":   ml_result,
            "explanation": shap_result,
        }

    except Exception as e:
        logger.error(f"predict failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{alert_id}")
def get_analysis(alert_id: str, request: Request):
    """
    Re-run ML + SHAP on a stored alert and return full explanation.
    Called when analyst clicks an alert to view details.
    """
    classifier = request.app.state.classifier
    explainer  = request.app.state.explainer

    try:
        with get_connection() as conn:
            cur = get_cursor(conn)
            cur.execute("SELECT * FROM alerts WHERE alert_id = %s", [alert_id])
            row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        # Reconstruct alert from raw_data
        raw  = row.get("raw_data") or {}
        alert = {
            "alert_id":   row["alert_id"],
            "severity":   row["severity"],
            "alert_type": row["alert_type"],
            "timestamp":  str(row["alert_timestamp"]),
            "source":     raw.get("source", {}),
            "indicators": raw.get("indicators", {}),
            "context":    raw.get("context", {}),
            "metrics":    raw.get("metrics", {}),
            "tags":       raw.get("tags", []),
            "metadata":   raw.get("metadata", {}),
            "affected_assets": raw.get("affected_assets", []),
        }

        features    = _extractor.extract_features(alert)
        ml_result   = classifier.predict(features)
        shap_result = explainer.explain(features)

        rule_result = {
            "risk_level":      row.get("risk_level", "info"),
            "rule_score":      row.get("rule_score", 0),
            "matched_rules":   [],
            "recommendations": [],
        }

        full_explanation = generate_full_explanation(
            alert, features, ml_result, shap_result, rule_result
        )

        # Persist explanation + ml prediction back to DB
        with get_connection() as conn:
            cur = get_cursor(conn)
            cur.execute(
                """
                UPDATE alerts
                SET ml_prediction = %s,
                    ml_confidence = %s,
                    explanation   = %s
                WHERE alert_id = %s
                """,
                [
                    ml_result.get("risk_level"),
                    ml_result.get("confidence"),
                    full_explanation,
                    alert_id,
                ]
            )

        return {
            "alert_id":          alert_id,
            "rule_risk_level":   rule_result["risk_level"],
            "rule_score":        rule_result["rule_score"],
            "ml_risk_level":     ml_result.get("risk_level"),
            "ml_confidence":     ml_result.get("confidence"),
            "ml_probabilities":  ml_result.get("probabilities", {}),
            "top_features":      shap_result.get("top_features", []),
            "explanation_text":  shap_result.get("explanation_text", ""),
            "full_explanation":  full_explanation,
            "shap_available":    shap_result.get("shap_available", False),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/model/info")
def model_info(request: Request):
    """Return model metadata - shown in dashboard ML panel."""
    classifier = request.app.state.classifier
    return {
        "ml_available": classifier.is_loaded,
        "metadata":     classifier.metadata,
    }