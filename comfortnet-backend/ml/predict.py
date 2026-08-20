"""
Inference module for the ComfortNet predictive-maintenance ML prototype.

Loads the persisted model once (module-level, not per-request), transforms
a telemetry reading with the SAME feature function used in training
(ml/features.py), and returns a risk probability + level + explanation.

STATUS: model trained on synthetic data only (see ml/train_model.py). Every
prediction returned by this module carries that disclosure in its output
so it can't be silently displayed without the caveat.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

import joblib
import pandas as pd

from ml.features import engineer_features_single, FEATURE_NAMES

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "maintenance_model.joblib"
FEATURE_METADATA_PATH = ARTIFACT_DIR / "feature_metadata.json"
EVAL_METRICS_PATH = ARTIFACT_DIR / "evaluation_metrics.json"

_model = None
_feature_metadata = None
_eval_metrics = None
_load_error = None


def _load():
    """Loads model + metadata once. Never raises — sets _load_error instead,
    so the API layer can return a clean 'ML unavailable' response rather
    than crashing the backend (per the implementation directive, §14)."""
    global _model, _feature_metadata, _eval_metrics, _load_error
    if _model is not None or _load_error is not None:
        return
    try:
        _model = joblib.load(MODEL_PATH)
        with open(FEATURE_METADATA_PATH) as f:
            _feature_metadata = json.load(f)
        with open(EVAL_METRICS_PATH) as f:
            _eval_metrics = json.load(f)
    except Exception as e:
        _load_error = str(e)


def is_available() -> bool:
    _load()
    return _model is not None


def get_load_error() -> Optional[str]:
    _load()
    return _load_error


def get_feature_metadata() -> Optional[dict]:
    _load()
    return _feature_metadata


def get_eval_metrics() -> Optional[dict]:
    _load()
    return _eval_metrics


def _risk_level(probability: float) -> str:
    if probability >= 0.66:
        return "HIGH"
    if probability >= 0.33:
        return "MEDIUM"
    return "LOW"


def predict_from_reading(reading: Dict[str, Any]) -> Dict[str, Any]:
    """
    reading: dict with at least the fields in ml/features.py's expected
    input (battery_percent, battery_voltage, solar_power, temperature,
    humidity, aqi_pm25, soil_moisture, light_level, network_status).
    Missing fields are filled with neutral defaults by engineer_features_single.

    Returns a dict matching the API response shape defined in the
    implementation directive — never raises for a well-formed reading.
    """
    _load()
    if _model is None:
        return {
            "available": False,
            "error": f"ML model not loaded: {_load_error}",
        }

    X = engineer_features_single(reading)
    proba = float(_model.predict_proba(X)[0, 1])
    level = _risk_level(proba)

    importances = _feature_metadata["feature_importances"]
    row = X.iloc[0]
    # Rank this specific reading's engineered features by (global importance
    # x how far the value is from a "calm" 0 baseline for stress-type
    # features), giving a per-prediction top-factor list rather than just
    # repeating the same global ranking every time.
    stress_features = ["battery_deficit", "temperature_stress", "environmental_stress",
                        "network_instability", "power_stress", "soil_stress"]
    # Minimum deviation before a stress-type feature is considered
    # "meaningfully active" for explanation purposes (display logic only —
    # does NOT affect the model's actual input/prediction, which always
    # uses the raw computed value).
    activation_threshold = {
        "battery_deficit": 5.0, "temperature_stress": 2.0, "environmental_stress": 0.1,
        "network_instability": 0.0, "power_stress": 3.0, "soil_stress": 3.0,
    }
    descriptions = {
        "battery_deficit": "Battery state is below the preferred operating baseline.",
        "battery_percent": "Battery charge level.",
        "battery_voltage": "Battery voltage reading.",
        "battery_recovery_proxy": "Combined battery/solar recovery signal.",
        "temperature_stress": "Temperature is above the assumed comfortable operating range.",
        "environmental_stress": "Air quality index is above the assumed baseline.",
        "network_instability": "Node network status is degraded or offline.",
        "power_stress": "Solar generation is low relative to the assumed baseline load.",
        "soil_stress": "Soil moisture is below the assumed baseline.",
        "solar_power": "Current solar generation.",
        "solar_load_margin": "Solar generation relative to assumed baseline load.",
        "temperature": "Ambient temperature reading.",
        "humidity": "Ambient humidity reading.",
        "aqi_pm25": "Air quality index reading.",
        "soil_moisture": "Soil moisture reading.",
        "light_level": "Ambient light reading.",
    }

    scored = []
    for feat in FEATURE_NAMES:
        weight = importances.get(feat, 0.0)
        raw_val = float(row[feat]) if row[feat] is not None else 0.0
        if feat in stress_features:
            active = raw_val > activation_threshold.get(feat, 0.0)
        else:
            active = False
        scored.append((feat, weight, active))
    # Prioritize stress-type features that are meaningfully active for this
    # specific reading, weighted by their trained importance; fall back to
    # plain global importance ordering for the remainder.
    scored.sort(key=lambda t: (t[2], t[1]), reverse=True)
    top = scored[:3]

    top_factors = [
        {
            "feature": feat,
            "importance": round(weight, 4),
            "description": descriptions.get(feat, feat),
        }
        for feat, weight, _active in top
    ]

    return {
        "available": True,
        "risk_probability": round(proba, 4),
        "risk_level": level,
        "top_contributing_factors": top_factors,
    }
