"""
/nodes — STATUS: IMPLEMENTED.
Node registration, listing, and detail (with latest telemetry attached).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Node, Campus, Telemetry
from app.schemas import NodeCreate, NodeOut, NodeDetailOut, TelemetryOut

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.post("", response_model=NodeOut)
def create_node(payload: NodeCreate, db: Session = Depends(get_db)):
    campus = db.query(Campus).filter(Campus.id == payload.campus_id).first()
    if not campus:
        raise HTTPException(status_code=404, detail=f"Campus '{payload.campus_id}' does not exist.")

    node_id = payload.id or None
    if node_id and db.query(Node).filter(Node.id == node_id).first():
        raise HTTPException(status_code=409, detail=f"Node '{node_id}' already exists.")

    import uuid
    node = Node(
        id=node_id or uuid.uuid4().hex,
        campus_id=payload.campus_id,
        tree_reference=payload.tree_reference,
        install_status=payload.install_status,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


@router.get("", response_model=List[NodeOut])
def list_nodes(campus_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Node)
    if campus_id:
        q = q.filter(Node.campus_id == campus_id)
    return q.all()


@router.get("/{node_id}", response_model=NodeDetailOut)
def get_node(node_id: str, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")

    latest = (
        db.query(Telemetry)
        .filter(Telemetry.node_id == node_id)
        .order_by(Telemetry.timestamp.desc())
        .first()
    )

    result = NodeDetailOut.model_validate(node)
    if latest:
        result.latest_telemetry = TelemetryOut.model_validate(latest)
    return result
