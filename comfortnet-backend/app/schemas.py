"""
Pydantic schemas for request/response validation. Mirrors app/models.py.
No sensor accuracy, price, or performance figures are encoded here —
these are structural/type definitions only.
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


# ---------- Campus ----------

class CampusCreate(BaseModel):
    name: str
    contact_org: Optional[str] = None


class CampusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    contact_org: Optional[str] = None
    created_at: datetime


# ---------- Node ----------

class NodeCreate(BaseModel):
    id: Optional[str] = Field(
        default=None,
        description="Optional explicit node id (e.g. 'tree-01'). If omitted, a UUID is generated.",
    )
    campus_id: str
    tree_reference: str
    install_status: str = Field(
        default="proposed",
        description="One of: planned, proposed, installed. Defaults to 'proposed' — "
        "no physical node has been installed anywhere.",
    )


class NodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    campus_id: str
    tree_reference: str
    install_status: str
    last_seen_at: Optional[datetime] = None
    created_at: datetime


class NodeDetailOut(NodeOut):
    latest_telemetry: Optional["TelemetryOut"] = None


# ---------- Telemetry ----------

class TelemetryIn(BaseModel):
    node_id: str
    timestamp: Optional[datetime] = Field(
        default=None, description="Defaults to server-received time if omitted."
    )
    battery_percent: Optional[float] = None
    battery_voltage: Optional[float] = None
    solar_power: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    aqi_pm25: Optional[float] = None
    soil_moisture: Optional[float] = None
    light_level: Optional[float] = None
    network_status: Optional[str] = None
    source: str = Field(
        default="simulated",
        description="Always 'simulated' today — no real sensor hardware exists yet.",
    )


class TelemetryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    node_id: str
    timestamp: datetime
    battery_percent: Optional[float] = None
    battery_voltage: Optional[float] = None
    solar_power: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    aqi_pm25: Optional[float] = None
    soil_moisture: Optional[float] = None
    light_level: Optional[float] = None
    network_status: Optional[str] = None
    source: str


NodeDetailOut.model_rebuild()


# ---------- Alerts ----------

class AlertCreate(BaseModel):
    node_id: str
    type: str
    severity: str = "info"
    message: str


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    node_id: str
    type: str
    severity: str
    message: str
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


class AlertAcknowledge(BaseModel):
    acknowledged_by: Optional[str] = Field(
        default=None, description="User id acknowledging the alert. Optional in this dev build."
    )


# ---------- Analytics ----------

class CampusSummaryOut(BaseModel):
    campus_id: str
    node_count: int
    nodes_reporting: int
    average_battery_percent: Optional[float] = None
    open_alert_count: int
    note: str = "All figures derived from simulated telemetry. No deployed hardware exists."


class NodeHealthOut(BaseModel):
    node_id: str
    implemented: bool = False
    status: str = "NOT_IMPLEMENTED"
    message: str = (
        "Predictive Maintenance AI (Phase 3) has not been built. This endpoint is a "
        "placeholder so the API contract in the Phase 2 spec is honored without "
        "pretending a health prediction exists."
    )


# ---------- Auth (placeholder) ----------

class LoginRequest(BaseModel):
    email: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "placeholder"
    warning: str = (
        "THIS IS NOT REAL AUTHENTICATION. No password check, no signature, no "
        "expiry is enforced. Do not use this token model beyond local demo purposes."
    )
