"""
SHAP Explainability for SOAR ML Predictions
---------------------------------------------
Explains WHY the model predicted a given risk level.
Returns top features driving the decision, suitable for analyst display.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)


class SHAPExplainer:
    """
    Wraps SHAP TreeExplainer for Random Forest models.
    
    Usage:
        explainer = SHAPExplainer()
        explainer.load(classifier)   # pass loaded SOARClassifier
        explanation = explainer.explain(feature_dict)
    """

    def __init__(self):
        self.explainer = None
        self.feature_names = []
        self.is_ready = False

    def load(self, classifier) -> bool:
        """
        Initialize SHAP explainer from a loaded SOARClassifier.
        Must be called after classifier.load().
        """
        try:
            import shap
            if not classifier.is_loaded:
                logger.warning("Classifier not loaded, cannot init SHAP explainer")
                return False

            self.explainer = shap.TreeExplainer(classifier.model)
            self.feature_names = classifier.get_feature_names()
            self.is_ready = True
            logger.info("SHAP explainer initialized successfully")
            return True

        except Exception as e:
            logger.error(f"SHAP explainer init failed: {e}")
            return False

    def explain(self, features: dict, top_n: int = 5) -> dict:
        """
        Generate SHAP explanation for a single prediction.

        Args:
            features : feature dict (same as passed to classifier.predict)
            top_n    : number of top features to return

        Returns:
            dict:
                top_features     - list of {feature, value, impact, direction}
                explanation_text - human-readable summary string
                shap_available   - False if explainer not ready
        """
        if not self.is_ready:
            return {
                "top_features": [],
                "explanation_text": "Explainability not available.",
                "shap_available": False,
            }

        try:
            # Build feature vector in correct order
            vec = []
            for col in self.feature_names:
                val = features.get(col, 0)
                if val is None or (isinstance(val, float) and np.isnan(val)):
                    val = 0.0
                vec.append(float(val))

            X = np.array(vec).reshape(1, -1)

            # Get SHAP values - shape: (n_classes, 1, n_features)
            shap_values = self.explainer.shap_values(X)

            # Sum absolute SHAP values across all classes to get overall feature importance
            # shap_values is list of arrays, one per class
            if isinstance(shap_values, list):
                # Multi-class: sum abs values across classes
                combined = np.sum([np.abs(sv) for sv in shap_values], axis=0)[0]
            else:
                combined = np.abs(shap_values[0])

            # Pair feature names with importance scores
            feature_importance = list(zip(self.feature_names, combined))
            feature_importance.sort(key=lambda x: x[1], reverse=True)

            # Build top_n result
            top_features = []
            for feat_name, importance in feature_importance[:top_n]:
                feat_value = features.get(feat_name, 0)
                top_features.append({
                    "feature":   feat_name,
                    "value":     round(float(feat_value), 4),
                    "impact":    round(float(importance), 4),
                    "direction": "increases_risk" if feat_value > 0 else "neutral",
                })

            # Human-readable summary
            if top_features:
                top = top_features[0]
                explanation_text = (
                    f"Primary driver: '{top['feature']}' (value={top['value']}, "
                    f"impact={top['impact']:.3f}). "
                    f"Top {len(top_features)} features contributed most to this prediction."
                )
            else:
                explanation_text = "No significant features identified."

            return {
                "top_features":      top_features,
                "explanation_text":  explanation_text,
                "shap_available":    True,
            }

        except Exception as e:
            logger.error(f"SHAP failed: {e}")
            return {
                "shap_available": False,
                "top_features": []
            }


def generate_full_explanation(
    alert: dict,
    features: dict,
    ml_result: dict,
    shap_result: dict,
    rule_result: dict,
) -> str:
    """
    Combine rule engine + ML + SHAP into one analyst-readable explanation.
    This is what gets stored in the DB `explanation` column.
    """
    lines = []

    alert_id   = alert.get("alert_id", "UNKNOWN")
    alert_type = alert.get("alert_type", "unknown")
    severity   = alert.get("severity", "unknown")

    lines.append(f"=== SOAR Analysis: {alert_id} ===")
    lines.append(f"Alert Type : {alert_type}")
    lines.append(f"Severity   : {severity}")
    lines.append("")

    # Rule engine section
    risk_level = rule_result.get("risk_level", "info")
    rule_score = rule_result.get("rule_score", 0)
    matched    = rule_result.get("matched_rules", [])
    lines.append(f"[Rule Engine]")
    lines.append(f"  Risk Level : {risk_level.upper()}")
    lines.append(f"  Score      : {rule_score}/100")
    lines.append(f"  Matched    : {', '.join(matched) if matched else 'None'}")
    lines.append("")

    # ML section
    if ml_result.get("ml_available"):
        ml_risk  = ml_result.get("risk_level", "N/A")
        ml_conf  = ml_result.get("confidence", 0)
        lines.append(f"[ML Prediction]")
        lines.append(f"  Predicted  : {ml_risk.upper()}")
        lines.append(f"  Confidence : {ml_conf:.1%}")
        probs = ml_result.get("probabilities", {})
        if probs:
            prob_str = ", ".join(f"{k}={v:.2f}" for k, v in sorted(probs.items()))
            lines.append(f"  Probs      : {prob_str}")
        lines.append("")

    # SHAP section
    if shap_result.get("shap_available"):
        lines.append(f"[Explainability - Top Features]")
        for feat in shap_result.get("top_features", []):
            lines.append(
                f"  {feat['feature']:35s} value={feat['value']:.3f}  impact={feat['impact']:.4f}"
            )
        lines.append("")
        lines.append(f"  {shap_result.get('explanation_text', '')}")
        lines.append("")

    # Recommendations
    recs = rule_result.get("recommendations", [])
    if recs:
        lines.append(f"[Recommended Actions]")
        for rec in recs:
            lines.append(f"  - {rec}")

    return "\n".join(lines)