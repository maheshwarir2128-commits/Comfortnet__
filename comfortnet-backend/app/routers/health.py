"""GET /health — STATUS: IMPLEMENTED."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": db_status,
            "mqtt_broker": "not_implemented",
            "predictive_maintenance_ai": "ml_prototype_synthetic_data_only_not_field_validated",
            "physical_hardware": "not_implemented",
        },
        "note": (
            "This is a Phase 2 software foundation. No physical node, MQTT "
            "broker, or MQTT-based hardware pipeline is connected. A predictive-maintenance "
            "ML prototype exists (RandomForestClassifier) but is trained and evaluated on "
            "synthetic telemetry only — not field-validated, not production-ready. See /ml/status."
        ),
    }
