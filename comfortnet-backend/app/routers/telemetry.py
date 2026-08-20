"""
/telemetry — STATUS: IMPLEMENTED.
Ingests telemetry (from the simulator today — no real sensor exists),
runs rule-based alert checks on ingest, and serves latest/historical reads.
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Node, Telemetry, Alert
from app.schemas import TelemetryIn, TelemetryOut
from app.analytics_rules import alert_rules_for_new_reading

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("", response_model=TelemetryOut)
def ingest_telemetry(payload: TelemetryIn, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == payload.node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{payload.node_id}' not found. Register it via POST /nodes first.")

    ts = payload.timestamp or datetime.now(timezone.utc)

    record = Telemetry(
        node_id=payload.node_id,
        timestamp=ts,
        battery_percent=payload.battery_percent,
        battery_voltage=payload.battery_voltage,
        solar_power=payload.solar_power,
        temperature=payload.temperature,
        humidity=payload.humidity,
        aqi_pm25=payload.aqi_pm25,
        soil_moisture=payload.soil_moisture,
        light_level=payload.light_level,
        network_status=payload.network_status,
        source=payload.source or "simulated",
    )
    db.add(record)

    node.last_seen_at = ts

    # Rule-based (NOT AI) alert generation on ingest.
    for rule in alert_rules_for_new_reading(record):
        db.add(Alert(node_id=payload.node_id, **rule))

    db.commit()
    db.refresh(record)
    return record


@router.get("/{node_id}/latest", response_model=TelemetryOut)
def latest_telemetry(node_id: str, db: Session = Depends(get_db)):
    record = (
        db.query(Telemetry)
        .filter(Telemetry.node_id == node_id)
        .order_by(Telemetry.timestamp.desc())
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail=f"No telemetry recorded yet for node '{node_id}'.")
    return record


@router.get("/{node_id}", response_model=List[TelemetryOut])
def historical_telemetry(
    node_id: str,
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    limit: int = Query(default=50, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Telemetry).filter(Telemetry.node_id == node_id)
    if start:
        q = q.filter(Telemetry.timestamp >= start)
    if end:
        q = q.filter(Telemetry.timestamp <= end)
    return q.order_by(Telemetry.timestamp.desc()).limit(limit).all()
