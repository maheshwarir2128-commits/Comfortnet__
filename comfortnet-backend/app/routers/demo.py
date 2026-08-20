"""
/demo — STATUS: IMPLEMENTED. Demo-only scenario control, per the Master
Directive Phase G ("the demo must never depend on luck"). This lets a
presenter deterministically trigger a scenario; the simulator script polls
GET /demo/scenario before generating each reading and adjusts accordingly.

This endpoint has NO effect on any real hardware (none exists) — it only
changes what the simulator generates. It is intentionally a single global
scenario (applies to whichever nodes the simulator is driving), not a
per-node scheduling system, to keep the presenter control dead simple.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/demo", tags=["demo"])

ALLOWED_SCENARIOS = [
    "normal",
    "low_battery",
    "sensor_anomaly",
    "network_failure",
    "sos_event",
    "recovery",
]

# In-memory only — resets on backend restart. Fine for a live demo;
# not intended to be a durable state store.
_state = {"scenario": "normal"}


class ScenarioIn(BaseModel):
    scenario: str


@router.get("/scenario")
def get_scenario():
    return {"scenario": _state["scenario"], "allowed": ALLOWED_SCENARIOS}


@router.post("/scenario")
def set_scenario(payload: ScenarioIn):
    if payload.scenario not in ALLOWED_SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario '{payload.scenario}'. Allowed: {ALLOWED_SCENARIOS}",
        )
    _state["scenario"] = payload.scenario
    return {"scenario": _state["scenario"], "message": f"Demo scenario set to '{payload.scenario}'."}
