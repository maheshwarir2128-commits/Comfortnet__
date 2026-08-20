"""
/campuses — STATUS: IMPLEMENTED.

ADDITION NOTE: the Phase 2 §6 API contract listed /auth, /nodes,
/telemetry, /alerts, /analytics, /health, but not /campuses explicitly.
Campuses are required by the §7 schema (nodes and users both have a
campus_id FK) and by the locked B2B multi-tenant business model in the
v1.0 Spec §4 — nodes cannot be created without a campus to belong to.
This router is a minimal supporting addition, not a change to any locked
decision. Flagging it here rather than adding it silently.
"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Campus
from app.schemas import CampusCreate, CampusOut

router = APIRouter(prefix="/campuses", tags=["campuses"])


@router.post("", response_model=CampusOut)
def create_campus(payload: CampusCreate, db: Session = Depends(get_db)):
    campus = Campus(name=payload.name, contact_org=payload.contact_org)
    db.add(campus)
    db.commit()
    db.refresh(campus)
    return campus


@router.get("", response_model=List[CampusOut])
def list_campuses(db: Session = Depends(get_db)):
    return db.query(Campus).all()
