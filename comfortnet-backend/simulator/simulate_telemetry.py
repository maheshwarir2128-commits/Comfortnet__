"""
ComfortNet simulated telemetry generator — STATUS: SIMULATED, by design.

No physical hardware exists (per the v1.0 System Specification and Phase 2
Architecture Specification). This script generates realistic-looking,
time-evolving telemetry for demo nodes and POSTs it to the backend's
/telemetry endpoint over HTTP, exactly like a Raspberry Pi gateway would
in the proposed (not built) architecture — except every value here is
generated, not measured.

Every posted record carries source="simulated" (enforced by the backend
schema default) so this is traceable in the database itself, not just in
UI copy.

DEMO-FIRST DESIGN (per the Master Hackathon Directive, Phase B/G):
- A full simulated day/night cycle is compressed into CYCLE_MINUTES of
  real time (default 10 minutes) so solar/battery behavior is visibly
  dynamic during a live demo, rather than needing a literal 24 hours.
- The current demo scenario is polled from the backend (GET /demo/scenario)
  before each tick, so a presenter can deterministically trigger
  LOW BATTERY / SENSOR ANOMALY / NETWORK FAILURE / SOS EVENT / RECOVERY
  via POST /demo/scenario without restarting anything.

Run with:  python simulator/simulate_telemetry.py
Configure via environment variables (see README.md).
"""
import math
import os
import time
import random
import sys
from datetime import datetime, timezone

import requests

BASE_URL = os.getenv("COMFORTNET_API_BASE", "http://localhost:8000")
NODE_IDS = os.getenv("COMFORTNET_SIM_NODES", "tree-01,tree-02,tree-03").split(",")
TICK_SECONDS = float(os.getenv("COMFORTNET_SIM_TICK_SECONDS", "5"))
CYCLE_MINUTES = float(os.getenv("COMFORTNET_SIM_CYCLE_MINUTES", "10"))

START_TIME = time.time()

# Per-node running state so values evolve smoothly rather than jumping randomly.
STATE = {
    node_id: {
        "battery_percent": random.uniform(70, 95),
        "temperature": 29.0,
        "humidity": 55.0,
        "aqi_pm25": 45.0,
        "soil_moisture": 40.0,
        "network_status": "online",
    }
    for node_id in NODE_IDS
}

# Tracks the previously-seen scenario so one-shot actions (like posting a
# single SOS alert) fire once on transition, not every tick.
_last_scenario = {"value": "normal"}


def get_current_scenario() -> str:
    try:
        resp = requests.get(f"{BASE_URL}/demo/scenario", timeout=2)
        resp.raise_for_status()
        return resp.json().get("scenario", "normal")
    except Exception:
        # Backend unreachable — fall back to normal rather than crashing the loop.
        return "normal"


def simulated_hour_of_day() -> float:
    """Maps elapsed real seconds onto a 0-24 simulated-hour cycle of length CYCLE_MINUTES."""
    elapsed = time.time() - START_TIME
    cycle_seconds = CYCLE_MINUTES * 60
    fraction = (elapsed % cycle_seconds) / cycle_seconds
    return fraction * 24.0


def solar_baseline(hour: float) -> float:
    """
    Simple daylight curve: 0 at night, peaking at simulated noon.
    ASSUMPTION for demo purposes only — not derived from the Feasibility
    Report's sun-hour figures, which describe daily *energy*, not an
    instantaneous curve shape.
    """
    if hour < 6 or hour > 19:
        return 0.0
    # Sine hump between 6 and 19 (13-hour daylight window for a visible demo arc)
    x = (hour - 6) / (19 - 6)
    return max(0.0, math.sin(x * math.pi)) * 100.0


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def step_node(node_id: str, scenario: str):
    s = STATE[node_id]
    hour = simulated_hour_of_day()
    solar = solar_baseline(hour) * random.uniform(0.85, 1.0)

    # --- Battery: charges when solar > a nominal load threshold, else discharges ---
    charge_rate = 0.6
    discharge_rate = 0.3
    if solar > 25:
        s["battery_percent"] = clamp(s["battery_percent"] + charge_rate * random.uniform(0.5, 1.5), 5, 100)
    else:
        s["battery_percent"] = clamp(s["battery_percent"] - discharge_rate * random.uniform(0.5, 1.5), 5, 100)

    # --- Slow-moving environmental values (smooth random walk) ---
    s["temperature"] = clamp(s["temperature"] + random.uniform(-0.3, 0.3), 22, 36)
    s["humidity"] = clamp(s["humidity"] + random.uniform(-1.5, 1.5), 30, 90)
    s["aqi_pm25"] = clamp(s["aqi_pm25"] + random.uniform(-4, 4), 20, 100)
    s["soil_moisture"] = clamp(s["soil_moisture"] + random.uniform(-0.5, 0.5), 15, 70)
    s["network_status"] = "online"

    # --- Deterministic demo scenario overrides ---
    if scenario == "low_battery":
        s["battery_percent"] = clamp(s["battery_percent"] - random.uniform(3, 6), 3, 20)
        solar *= 0.4
    elif scenario == "sensor_anomaly":
        s["temperature"] = clamp(s["temperature"] + random.uniform(8, 14), 22, 55)
        s["aqi_pm25"] = clamp(s["aqi_pm25"] + random.uniform(80, 150), 20, 300)
    elif scenario == "network_failure":
        s["network_status"] = "offline"
    elif scenario == "recovery":
        # Nudge everything back toward healthy baseline.
        s["battery_percent"] = clamp(s["battery_percent"] + random.uniform(2, 5), 3, 100)
        s["temperature"] += (29.0 - s["temperature"]) * 0.2
        s["aqi_pm25"] += (45.0 - s["aqi_pm25"]) * 0.3
        s["network_status"] = "online"
    # "sos_event" does not change telemetry — it's handled as a one-shot
    # alert in maybe_fire_sos_event(), since SOS is an event, not a reading.

    light_level = clamp(solar * 12 + random.uniform(-20, 20), 0, 1200)

    return {
        "node_id": node_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "battery_percent": round(s["battery_percent"], 1),
        "battery_voltage": round(10.0 + (s["battery_percent"] / 100) * 4.4, 2),  # illustrative only, not a real discharge curve
        "solar_power": round(solar, 1),
        "temperature": round(s["temperature"], 1),
        "humidity": round(s["humidity"], 1),
        "aqi_pm25": round(s["aqi_pm25"], 1),
        "soil_moisture": round(s["soil_moisture"], 1),
        "light_level": round(light_level, 0),
        "network_status": s["network_status"],
        "source": "simulated",
    }


def maybe_fire_sos_event(scenario: str, node_id: str):
    """One-shot: posts a single critical SOS alert the moment the scenario
    transitions into 'sos_event' for this simulator run. Does not repeat
    every tick while the scenario stays set."""
    if scenario == "sos_event" and _last_scenario["value"] != "sos_event":
        try:
            requests.post(
                f"{BASE_URL}/alerts",
                json={
                    "node_id": node_id,
                    "type": "sos",
                    "severity": "critical",
                    "message": "SOS triggered (SIMULATED demo event — in-app SOS UI is the only real SOS path today).",
                },
                timeout=3,
            )
            print(f"[SIMULATED] SOS alert posted for {node_id}")
        except Exception as e:
            print(f"[SIMULATED] Could not post SOS alert: {e}")


def main():
    print(f"[SIMULATED] ComfortNet telemetry simulator starting.")
    print(f"[SIMULATED] Backend: {BASE_URL} | Nodes: {NODE_IDS} | Tick: {TICK_SECONDS}s | Cycle: {CYCLE_MINUTES}min")
    print("[SIMULATED] All data generated here is synthetic. No physical hardware is involved.")

    try:
        health = requests.get(f"{BASE_URL}/health", timeout=3)
        print(f"[SIMULATED] Backend health check: {health.status_code} {health.json().get('status')}")
    except Exception as e:
        print(f"[SIMULATED] WARNING: could not reach backend at {BASE_URL} ({e}). "
              f"Start it first: uvicorn app.main:app --reload")

    while True:
        scenario = get_current_scenario()
        for node_id in NODE_IDS:
            payload = step_node(node_id, scenario)
            maybe_fire_sos_event(scenario, node_id)
            try:
                resp = requests.post(f"{BASE_URL}/telemetry", json=payload, timeout=3)
                if resp.status_code >= 400:
                    print(f"[SIMULATED] {node_id}: backend rejected telemetry ({resp.status_code}): {resp.text[:200]}")
                else:
                    print(f"[SIMULATED] {node_id}: batt={payload['battery_percent']}% "
                          f"solar={payload['solar_power']}W temp={payload['temperature']}C "
                          f"net={payload['network_status']} scenario={scenario}")
            except Exception as e:
                print(f"[SIMULATED] {node_id}: could not reach backend ({e})")
        _last_scenario["value"] = scenario
        time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[SIMULATED] Simulator stopped.")
        sys.exit(0)
