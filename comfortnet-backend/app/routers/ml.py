"""
/ml — Predictive-maintenance ML prototype endpoints.

STATUS: IMPLEMENTED — a real RandomForestClassifier trained on synthetic
telemetry (see ml/train_model.py, actually executed; metrics in
ml/artifacts/evaluation_metrics.json are real outputs of that run).

NOT field-validated. NOT trained on real hardware data (none exists).
Every response below carries synthetic_data_only=true and
field_validated=false explicitly, so this cannot be silently displayed
without the caveat traveling with it.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Node, Telemetry
from ml.predict import predict_from_reading, is_available, get_load_error, get_feature_metadata, get_eval_metrics

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/status")
def ml_status():
    available = is_available()
    metrics = get_eval_metrics() if available else None
    return {
        "ml_available": available,
        "model_loaded": available,
        "load_error": None if available else get_load_error(),
        "model_type": "RandomForestClassifier",
        "training_data": "synthetic_telemetry",
        "field_validated": False,
        "production_ready": False,
        "quick_metrics": {
            "accuracy": metrics["accuracy"],
            "recall": metrics["recall"],
            "roc_auc": metrics["roc_auc"],
        } if metrics else None,
        "note": "ML PROTOTYPE — trained on synthetic telemetry only. No physical ComfortNet node has been deployed.",
    }


@router.get("/model-info")
def model_info():
    if not is_available():
        raise HTTPException(status_code=503, detail=f"ML model not available: {get_load_error()}")
    meta = get_feature_metadata()
    return {
        "model_type": "RandomForestClassifier",
        "feature_names": meta["feature_names"],
        "feature_importances": meta["feature_importances"],
        "importance_note": meta["importance_note"],
        "training_data": "synthetic_telemetry",
        "field_validated": False,
    }


@router.get("/evaluation")
def evaluation():
    if not is_available():
        raise HTTPException(status_code=503, detail=f"ML model not available: {get_load_error()}")
    metrics = get_eval_metrics()
    return {
        **metrics,
        "note": (
            "These metrics are real outputs of an actual train/test split on synthetic "
            "telemetry (see ml/train_model.py) — not invented numbers. They measure "
            "performance on synthetic data only, not real-world/field accuracy."
        ),
    }


@router.post("/predict/{node_id}")
def predict(node_id: str, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")

    if not is_available():
        raise HTTPException(status_code=503, detail=f"ML model not available: {get_load_error()}")

    latest = (
        db.query(Telemetry)
        .filter(Telemetry.node_id == node_id)
        .order_by(Telemetry.timestamp.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail=f"No telemetry recorded yet for node '{node_id}'.")

    reading = {
        "battery_percent": latest.battery_percent,
        "battery_voltage": latest.battery_voltage,
        "solar_power": latest.solar_power,
        "temperature": latest.temperature,
        "humidity": latest.humidity,
        "aqi_pm25": latest.aqi_pm25,
        "soil_moisture": latest.soil_moisture,
        "light_level": latest.light_level,
        "network_status": latest.network_status,
    }
    result = predict_from_reading(reading)
    if not result.get("available"):
        raise HTTPException(status_code=503, detail=result.get("error", "ML prediction unavailable"))

    return {
        "node_id": node_id,
        "model": "RandomForestClassifier",
        "prediction_type": "synthetic_data_maintenance_risk",
        "risk_probability": result["risk_probability"],
        "risk_level": result["risk_level"],
        "top_contributing_factors": result["top_contributing_factors"],
        "based_on_telemetry_timestamp": latest.timestamp.isoformat(),
        "synthetic_data_only": True,
        "field_validated": False,
        "production_ready": False,
        "method": "supervised_machine_learning",
        "note": "ML PROTOTYPE — trained on synthetic telemetry. Not field-validated. Not production-ready.",
    }
