"""
ORM models corresponding to the Phase 2 Architecture Specification, §7
(Database Design). Table/field choices here implement that design; they do
not change it. Two additions beyond §7 are called out explicitly below,
since the person's instructions require flagging anything not already
locked rather than deciding it silently.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Campus(Base):
    """
    Per Phase 2 §7. Not explicitly listed as its own API resource in the
    Phase 2 §6 API contract, but required to exist so nodes/users can be
    scoped to a campus (B2B multi-tenant model, per the locked business
    model in the v1.0 Spec §4). A minimal /campuses router was added to
    support this — see app/routers/campuses.py and the Phase 2
    Implementation Report for why.
    """
    __tablename__ = "campuses"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    contact_org = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    nodes = relationship("Node", back_populates="campus", cascade="all, delete-orphan")
    users = relationship("User", back_populates="campus")


class User(Base):
    """Per Phase 2 §7. Auth against this table is a placeholder — see auth.py."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    campus_id = Column(String, ForeignKey("campuses.id"), nullable=True)
    role = Column(String, nullable=False, default="student")  # student | admin | security
    email = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    campus = relationship("Campus", back_populates="users")


class Node(Base):
    """
    Per Phase 2 §7. install_status defaults to "proposed" because, per the
    v1.0 Spec and Feasibility Report, no physical node has been built or
    installed anywhere — this default reflects reality, it is not a
    placeholder to be quietly changed later without a real install event.
    """
    __tablename__ = "nodes"

    id = Column(String, primary_key=True)  # e.g. "tree-01" — see DEVELOPMENT CHOICE note in seed.py
    campus_id = Column(String, ForeignKey("campuses.id"), nullable=False)
    tree_reference = Column(String, nullable=False)
    install_status = Column(String, nullable=False, default="proposed")  # planned | proposed | installed
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    campus = relationship("Campus", back_populates="nodes")
    telemetry = relationship("Telemetry", back_populates="node", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="node", cascade="all, delete-orphan")
    camera_events = relationship("CameraEvent", back_populates="node", cascade="all, delete-orphan")
    maintenance_records = relationship("MaintenanceRecord", back_populates="node", cascade="all, delete-orphan")


class Telemetry(Base):
    """
    Per Phase 2 §4 (telemetry schema) and §7. `source` is always
    "simulated" today — see app/config.py — because no real sensor exists.
    Nothing in this backend can currently produce a "real" reading.
    """
    __tablename__ = "telemetry"

    id = Column(String, primary_key=True, default=_uuid)
    node_id = Column(String, ForeignKey("nodes.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    battery_percent = Column(Float, nullable=True)
    battery_voltage = Column(Float, nullable=True)
    solar_power = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    aqi_pm25 = Column(Float, nullable=True)
    soil_moisture = Column(Float, nullable=True)
    light_level = Column(Float, nullable=True)
    network_status = Column(String, nullable=True)  # online | degraded | offline
    source = Column(String, nullable=False, default="simulated")
    created_at = Column(DateTime(timezone=True), default=_now)

    node = relationship("Node", back_populates="telemetry")


class Alert(Base):
    """
    Per Phase 2 §7. Alerts today are created by a simple threshold rule on
    telemetry ingest (see routers/telemetry.py) — this is rule-based logic,
    not AI, and is not the Phase 3 predictive-maintenance feature.
    """
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=_uuid)
    node_id = Column(String, ForeignKey("nodes.id"), nullable=False, index=True)
    type = Column(String, nullable=False)  # e.g. low_battery, offline, sos
    severity = Column(String, nullable=False, default="info")  # info | warning | critical
    message = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String, ForeignKey("users.id"), nullable=True)

    node = relationship("Node", back_populates="alerts")


class CameraEvent(Base):
    """
    Per Phase 2 §7 and §11. STATUS: schema only — NOT wired to any API
    endpoint and NOT populated by anything, because no camera hardware or
    capture pipeline exists (per the v1.0 Spec, camera is motion-triggered
    and proposed, not built). Table exists so a future phase has a place
    to write to, consistent with how §7 described it.
    """
    __tablename__ = "camera_events"

    id = Column(String, primary_key=True, default=_uuid)
    node_id = Column(String, ForeignKey("nodes.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    storage_ref = Column(String, nullable=True)
    reviewed = Column(Boolean, default=False)
    retention_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    node = relationship("Node", back_populates="camera_events")


class MaintenanceRecord(Base):
    """
    Per Phase 2 §7: 'this table's data source (Phase 3 model) does not
    exist yet; schema is defined ahead of the model.' STATUS: schema only —
    NOT populated by anything. Predictive Maintenance AI (Phase 3) is
    explicitly out of scope for this implementation step.
    """
    __tablename__ = "maintenance_records"

    id = Column(String, primary_key=True, default=_uuid)
    node_id = Column(String, ForeignKey("nodes.id"), nullable=False, index=True)
    predicted_at = Column(DateTime(timezone=True), nullable=True)
    predicted_days_to_maintenance = Column(Float, nullable=True)
    actual_action_taken = Column(String, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    node = relationship("Node", back_populates="maintenance_records")
