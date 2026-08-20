"""/alerts — STATUS: IMPLEMENTED."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, Node
from app.schemas import AlertCreate, AlertOut, AlertAcknowledge

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("", response_model=AlertOut)
def create_alert(payload: AlertCreate, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == payload.node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{payload.node_id}' not found.")
    alert = Alert(
        node_id=payload.node_id,
        type=payload.type,
        severity=payload.severity,
        message=payload.message,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("", response_model=List[AlertOut])
def list_alerts(
    node_id: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Alert)
    if node_id:
        q = q.filter(Alert.node_id == node_id)
    if acknowledged is not None:
        if acknowledged:
            q = q.filter(Alert.acknowledged_at.isnot(None))
        else:
            q = q.filter(Alert.acknowledged_at.is_(None))
    return q.order_by(Alert.created_at.desc()).all()


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert(alert_id: str, payload: AlertAcknowledge, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = payload.acknowledged_by
    db.commit()
    db.refresh(alert)
    return alert
