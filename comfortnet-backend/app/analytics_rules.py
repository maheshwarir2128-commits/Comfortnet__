"""
Rule-based explainable analytics — STATUS: IMPLEMENTED (rule-based only).

THIS IS NOT AI OR MACHINE LEARNING. Per the Master Hackathon Directive
§10 (Phase D) and the v1.0 Spec's locked AI classification, this module
implements simple, fully-explainable threshold/trend logic so the
prototype has a real, honestly-labeled intelligence layer without
claiming a predictive-maintenance ML model that does not exist.

Every threshold below is an ENGINEERING ASSUMPTION for demo purposes,
not a validated setpoint (consistent with the Phase 2 §9 power-threshold
caveat). They are intentionally simple so they can be explained to a
judge in one sentence each.
"""
from typing import List, Optional
from dataclasses import dataclass, field


# --- Thresholds (ASSUMPTIONS — not experimentally validated) ---
BATTERY_CRITICAL = 15.0
BATTERY_WARNING = 30.0
TEMP_HIGH_C = 40.0
AQI_HIGH = 150.0
SOIL_LOW_PERCENT = 15.0


@dataclass
class HealthResult:
    health_score: int
    status: str  # healthy | warning | critical
    contributing_factors: List[str] = field(default_factory=list)


def calculate_health_score(t) -> HealthResult:
    """
    t: a Telemetry ORM row (or any object with the same attribute names).
    Starts at 100 and subtracts explainable point deductions. This is a
    simple weighted-rule score, not a trained model — no accuracy claim
    is made or implied.
    """
    score = 100
    factors: List[str] = []

    if t.battery_percent is not None:
        if t.battery_percent < BATTERY_CRITICAL:
            score -= 40
            factors.append(f"Battery critically low ({t.battery_percent:.0f}% < {BATTERY_CRITICAL:.0f}%)")
        elif t.battery_percent < BATTERY_WARNING:
            score -= 20
            factors.append(f"Battery low ({t.battery_percent:.0f}% < {BATTERY_WARNING:.0f}%)")

    if t.network_status == "offline":
        score -= 25
        factors.append("Network offline")
    elif t.network_status == "degraded":
        score -= 10
        factors.append("Network degraded")

    if t.temperature is not None and t.temperature > TEMP_HIGH_C:
        score -= 15
        factors.append(f"Temperature high ({t.temperature:.1f}°C > {TEMP_HIGH_C:.0f}°C)")

    if t.aqi_pm25 is not None and t.aqi_pm25 > AQI_HIGH:
        score -= 10
        factors.append(f"Air quality poor (index {t.aqi_pm25:.0f} > {AQI_HIGH:.0f})")

    if t.soil_moisture is not None and t.soil_moisture < SOIL_LOW_PERCENT:
        score -= 5
        factors.append(f"Soil moisture low ({t.soil_moisture:.0f}% < {SOIL_LOW_PERCENT:.0f}%)")

    score = max(0, min(100, score))
    if score < 50:
        status = "critical"
    elif score < 80:
        status = "warning"
    else:
        status = "healthy"

    if not factors:
        factors.append("All monitored values within normal assumed ranges")

    return HealthResult(health_score=score, status=status, contributing_factors=factors)


def detect_anomalies(recent: list) -> List[str]:
    """
    recent: list of Telemetry rows, most recent last, oldest first is fine too
    (only the two endpoints are compared). Trend logic is intentionally
    simple: compare the most recent reading to the earliest in the window.
    """
    anomalies: List[str] = []
    if len(recent) < 2:
        return anomalies

    first, last = recent[0], recent[-1]

    if first.battery_percent is not None and last.battery_percent is not None:
        drop = first.battery_percent - last.battery_percent
        if drop > 15:
            anomalies.append(
                f"Abnormal battery drain: dropped {drop:.0f} percentage points across the observed window"
            )

    if last.temperature is not None and first.temperature is not None:
        if last.temperature - first.temperature > 8:
            anomalies.append("Rapid temperature rise detected across the observed window")

    if last.aqi_pm25 is not None and last.aqi_pm25 > AQI_HIGH:
        anomalies.append(f"Air quality spike (index {last.aqi_pm25:.0f})")

    offline_count = sum(1 for r in recent if r.network_status == "offline")
    if offline_count >= max(2, len(recent) // 3):
        anomalies.append("Recurring network instability across the observed window")

    return anomalies


def alert_rules_for_new_reading(t) -> List[dict]:
    """
    Returns a list of alert dicts {type, severity, message} to create for a
    single freshly-ingested telemetry row. This is the same rule-based
    logic as calculate_health_score, applied at ingest time so alerts are
    generated immediately rather than only on dashboard read.
    """
    alerts = []
    if t.battery_percent is not None and t.battery_percent < BATTERY_CRITICAL:
        alerts.append({
            "type": "low_battery",
            "severity": "critical",
            "message": f"Battery at {t.battery_percent:.0f}% — below critical threshold ({BATTERY_CRITICAL:.0f}%).",
        })
    elif t.battery_percent is not None and t.battery_percent < BATTERY_WARNING:
        alerts.append({
            "type": "low_battery",
            "severity": "warning",
            "message": f"Battery at {t.battery_percent:.0f}% — below warning threshold ({BATTERY_WARNING:.0f}%).",
        })

    if t.network_status == "offline":
        alerts.append({
            "type": "network_offline",
            "severity": "warning",
            "message": "Node reporting network status: offline.",
        })

    if t.temperature is not None and t.temperature > TEMP_HIGH_C:
        alerts.append({
            "type": "high_temperature",
            "severity": "warning",
            "message": f"Temperature at {t.temperature:.1f}°C — above assumed high threshold ({TEMP_HIGH_C:.0f}°C).",
        })

    if t.aqi_pm25 is not None and t.aqi_pm25 > AQI_HIGH:
        alerts.append({
            "type": "poor_air_quality",
            "severity": "warning",
            "message": f"Air quality index at {t.aqi_pm25:.0f} — above assumed high threshold ({AQI_HIGH:.0f}).",
        })

    return alerts
