"""
Feature engineering — shared identically between training
(ml/train_model.py) and live inference (ml/predict.py, called from
app/routers/ml.py) so there is no train/inference skew.

Every feature here is computed from fields that exist in the real backend
Telemetry schema (app/models.py: battery_percent, battery_voltage,
solar_power, temperature, humidity, aqi_pm25, soil_moisture, light_level,
network_status). No feature here is the label itself or a disguised copy
of it — each is an independently-motivated engineered signal (e.g.
"how far below a healthy baseline is the battery"), consistent with
avoiding the leakage pattern the implementation directive warned about.
"""
from typing import Dict, Any
import numpy as np
import pandas as pd

FEATURE_NAMES = [
    "battery_percent",
    "battery_voltage",
    "solar_power",
    "temperature",
    "humidity",
    "aqi_pm25",
    "soil_moisture",
    "light_level",
    "battery_deficit",
    "solar_load_margin",
    "temperature_stress",
    "environmental_stress",
    "network_instability",
    "battery_recovery_proxy",
    "power_stress",
    "soil_stress",
]

# ASSUMPTIONS used purely to define engineered feature baselines — not
# datasheet values, not the same numbers used to generate the label.
HEALTHY_BATTERY_BASELINE = 60.0
SOLAR_BASELINE_W = 40.0
TEMP_STRESS_BASELINE_C = 35.0
AQI_STRESS_BASELINE = 100.0
ASSUMED_LOAD_PROXY_W = 8.0
SOIL_STRESS_BASELINE = 20.0

_NETWORK_INSTABILITY_MAP = {"online": 0.0, "degraded": 0.5, "offline": 1.0}


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    df must contain: battery_percent, battery_voltage, solar_power,
    temperature, humidity, aqi_pm25, soil_moisture, light_level,
    network_status. Returns a new DataFrame with FEATURE_NAMES columns,
    in that exact order.
    """
    out = pd.DataFrame(index=df.index)

    out["battery_percent"] = df["battery_percent"].astype(float)
    out["battery_voltage"] = df["battery_voltage"].astype(float)
    out["solar_power"] = df["solar_power"].astype(float)
    out["temperature"] = df["temperature"].astype(float)
    out["humidity"] = df["humidity"].astype(float)
    out["aqi_pm25"] = df["aqi_pm25"].astype(float)
    out["soil_moisture"] = df["soil_moisture"].astype(float)
    out["light_level"] = df["light_level"].astype(float)

    out["battery_deficit"] = (HEALTHY_BATTERY_BASELINE - out["battery_percent"]).clip(lower=0)
    out["solar_load_margin"] = out["solar_power"] - SOLAR_BASELINE_W
    out["temperature_stress"] = (out["temperature"] - TEMP_STRESS_BASELINE_C).clip(lower=0)
    out["environmental_stress"] = ((out["aqi_pm25"] - AQI_STRESS_BASELINE) / 100.0).clip(lower=0)
    out["network_instability"] = df["network_status"].map(_NETWORK_INSTABILITY_MAP).fillna(0.0)
    out["battery_recovery_proxy"] = out["battery_percent"] * (out["solar_power"] / 100.0)
    out["power_stress"] = (ASSUMED_LOAD_PROXY_W - out["solar_power"] / 12.0).clip(lower=0)
    out["soil_stress"] = (SOIL_STRESS_BASELINE - out["soil_moisture"]).clip(lower=0)

    return out[FEATURE_NAMES]


def engineer_features_single(reading: Dict[str, Any]) -> pd.DataFrame:
    """Convenience wrapper for a single live telemetry reading (dict-like,
    e.g. a SQLAlchemy Telemetry row's __dict__ or a Pydantic model dump)."""
    row = {
        "battery_percent": reading.get("battery_percent"),
        "battery_voltage": reading.get("battery_voltage"),
        "solar_power": reading.get("solar_power"),
        "temperature": reading.get("temperature"),
        "humidity": reading.get("humidity"),
        "aqi_pm25": reading.get("aqi_pm25"),
        "soil_moisture": reading.get("soil_moisture"),
        "light_level": reading.get("light_level"),
        "network_status": reading.get("network_status") or "online",
    }
    # Fill missing numeric telemetry with neutral/healthy-ish defaults rather
    # than crashing — a live node may not report every field every reading.
    defaults = {
        "battery_percent": 80.0, "battery_voltage": 13.5, "solar_power": 50.0,
        "temperature": 28.0, "humidity": 55.0, "aqi_pm25": 45.0,
        "soil_moisture": 40.0, "light_level": 600.0,
    }
    for k, v in defaults.items():
        if row[k] is None:
            row[k] = v
    df = pd.DataFrame([row])
    return engineer_features(df)
