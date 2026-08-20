"""
/analytics — STATUS: IMPLEMENTED for campus summary + rule-based node
health/anomalies. Predictive-maintenance ML remains NOT IMPLEMENTED — see
NodeHealthOut.note for the explicit disclosure returned in every response.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Node, Telemetry, Alert
from app.schemas import CampusSummaryOut
from app.schemas_analytics import NodeHealthOut, NodeAnomaliesOut
from app.analytics_rules import calculate_health_score, detect_anomalies

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/campus/{campus_id}/summary", response_model=CampusSummaryOut)
def campus_summary(campus_id: str, db: Session = Depends(get_db)):
    nodes = db.query(Node).filter(Node.campus_id == campus_id).all()
    node_ids = [n.id for n in nodes]

    latest_by_node = {}
    for nid in node_ids:
        latest = (
            db.query(Telemetry)
            .filter(Telemetry.node_id == nid)
            .order_by(Telemetry.timestamp.desc())
            .first()
        )
        if latest:
            latest_by_node[nid] = latest

    batteries = [t.battery_percent for t in latest_by_node.values() if t.battery_percent is not None]
    avg_battery = sum(batteries) / len(batteries) if batteries else None

    open_alerts = (
        db.query(Alert)
        .filter(Alert.node_id.in_(node_ids), Alert.acknowledged_at.is_(None))
        .count()
        if node_ids
        else 0
    )

    return CampusSummaryOut(
        campus_id=campus_id,
        node_count=len(nodes),
        nodes_reporting=len(latest_by_node),
        average_battery_percent=avg_battery,
        open_alert_count=open_alerts,
    )


@router.get("/node/{node_id}/health", response_model=NodeHealthOut)
def node_health(node_id: str, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")

    latest = (
        db.query(Telemetry)
        .filter(Telemetry.node_id == node_id)
        .order_by(Telemetry.timestamp.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail=f"No telemetry recorded yet for node '{node_id}'.")

    result = calculate_health_score(latest)
    return NodeHealthOut(
        node_id=node_id,
        health_score=result.health_score,
        status=result.status,
        contributing_factors=result.contributing_factors,
    )


@router.get("/node/{node_id}/anomalies", response_model=NodeAnomaliesOut)
def node_anomalies(node_id: str, window: int = 10, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")

    recent = (
        db.query(Telemetry)
        .filter(Telemetry.node_id == node_id)
        .order_by(Telemetry.timestamp.asc())
        .all()[-window:]
    )
    anomalies = detect_anomalies(recent)
    return NodeAnomaliesOut(node_id=node_id, anomalies=anomalies)
