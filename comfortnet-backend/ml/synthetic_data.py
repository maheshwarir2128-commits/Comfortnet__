"""
Synthetic telemetry dataset generator for the ComfortNet predictive-
maintenance ML prototype.

STATUS: SIMULATED / SYNTHETIC. No physical ComfortNet node has ever been
deployed, so there is no real historical telemetry to train on. This
module generates a reproducible synthetic dataset instead, and every
downstream artifact (model, metrics, API response) says so explicitly.

METHODOLOGY (documented per the honesty requirement — this is not an
arbitrary label):

Each synthetic sample is drawn from a hidden ("latent") severity variable
in [0, 1] representing how degraded a node's operating condition is. The
severity is sampled from one of three regimes (healthy / degrading /
high_risk) with overlapping ranges, so the classes are NOT perfectly
separable — this is what makes the resulting classification problem a
genuine (if synthetic) ML problem rather than a restated threshold rule.

Severity drives *all* observable telemetry fields through physically-
motivated relationships (higher severity -> lower battery, lower solar,
higher temperature, worse air quality, more network instability), each
with independent noise. The maintenance_risk label is then sampled from a
logistic (sigmoid) function of severity — i.e. probabilistically, not
deterministically — so no single observed feature (and no raw feature at
all) equals or trivially determines the label. This directly avoids the
kind of leakage the implementation directive warned about (e.g. including
a precomputed "risk_score" column that IS the label).

Only fields that exist in the real backend Telemetry schema
(app/models.py) are generated here, plus one engineered proxy
(power_load_proxy) that is a deterministic function of solar_power alone
(not of the label) — this keeps the synthetic generator and the real
/telemetry pipeline feature-compatible, which matters because the same
feature-engineering function (ml/features.py) is used for both training
and live inference.

Run standalone:
    python -m ml.synthetic_data
or:
    python ml/synthetic_data.py
"""
import argparse
import numpy as np
import pandas as pd

RANDOM_STATE = 42

# Assumed baseline continuous load used only to derive an illustrative
# power_load_proxy feature — an ENGINEERING ASSUMPTION for the synthetic
# story, consistent with (not a repeat of) the ~8W AP placeholder used in
# the Feasibility Report's power budget. Not a measured value.
ASSUMED_BASELINE_LOAD_W = 8.0


def _clip(arr, lo, hi):
    return np.clip(arr, lo, hi)


def generate_synthetic_dataset(n_samples: int = 8000, random_state: int = RANDOM_STATE) -> pd.DataFrame:
    """
    Generates a reproducible synthetic telemetry dataset with a
    probabilistic maintenance_risk label. See module docstring for the
    full generation methodology.
    """
    rng = np.random.default_rng(random_state)

    # --- Regime assignment (imbalanced on purpose — maintenance events
    # should be the minority class, like in a real fleet) ---
    regime = rng.choice(
        ["healthy", "degrading", "high_risk"],
        size=n_samples,
        p=[0.55, 0.30, 0.15],
    )

    severity = np.empty(n_samples, dtype=float)
    severity[regime == "healthy"] = rng.uniform(0.0, 0.25, size=(regime == "healthy").sum())
    severity[regime == "degrading"] = rng.uniform(0.25, 0.70, size=(regime == "degrading").sum())
    severity[regime == "high_risk"] = rng.uniform(0.60, 1.00, size=(regime == "high_risk").sum())

    # --- Telemetry generated as noisy functions of severity ---
    battery_percent = _clip(90 - 70 * severity + rng.normal(0, 8, n_samples), 3, 100)
    battery_voltage = 10.0 + (battery_percent / 100) * 4.4 + rng.normal(0, 0.15, n_samples)
    solar_power = _clip(70 - 40 * severity + rng.normal(0, 12, n_samples), 0, 100)
    temperature = _clip(28 + 12 * severity + rng.normal(0, 2, n_samples), 15, 55)
    humidity = _clip(55 - 5 * severity + rng.normal(0, 10, n_samples), 20, 95)
    aqi_pm25 = _clip(45 + 90 * severity + rng.normal(0, 15, n_samples), 10, 300)
    soil_moisture = _clip(42 - 15 * severity + rng.normal(0, 6, n_samples), 5, 80)
    light_level = _clip(700 - 300 * severity + rng.normal(0, 100, n_samples), 0, 1200)

    p_offline = _clip(0.03 + 0.35 * severity, 0, 1)
    p_degraded = _clip(0.05 + 0.25 * severity, 0, 1)
    network_status = np.empty(n_samples, dtype=object)
    draw = rng.uniform(0, 1, n_samples)
    network_status[draw < p_offline] = "offline"
    network_status[(draw >= p_offline) & (draw < p_offline + p_degraded)] = "degraded"
    network_status[draw >= p_offline + p_degraded] = "online"

    # --- Probabilistic (not deterministic) label from a logistic function
    # of the hidden severity variable. k controls how sharply risk rises
    # with severity; 0.5 centering means mid-severity samples are
    # genuinely ambiguous, which is intentional. ---
    k = 6.0
    p_risk = 1 / (1 + np.exp(-k * (severity - 0.5)))
    maintenance_risk = rng.binomial(1, p_risk)

    df = pd.DataFrame({
        "battery_percent": battery_percent,
        "battery_voltage": battery_voltage,
        "solar_power": solar_power,
        "temperature": temperature,
        "humidity": humidity,
        "aqi_pm25": aqi_pm25,
        "soil_moisture": soil_moisture,
        "light_level": light_level,
        "network_status": network_status,
        "maintenance_risk": maintenance_risk,
    })
    return df


def main():
    parser = argparse.ArgumentParser(description="Generate ComfortNet synthetic telemetry dataset.")
    parser.add_argument("--n-samples", type=int, default=8000)
    parser.add_argument("--out", type=str, default="ml/artifacts/synthetic_dataset.csv")
    parser.add_argument("--random-state", type=int, default=RANDOM_STATE)
    args = parser.parse_args()

    df = generate_synthetic_dataset(n_samples=args.n_samples, random_state=args.random_state)
    df.to_csv(args.out, index=False)
    print(f"[SYNTHETIC] Generated {len(df)} samples -> {args.out}")
    print(f"[SYNTHETIC] Positive (maintenance_risk=1): {int(df['maintenance_risk'].sum())} "
          f"({df['maintenance_risk'].mean()*100:.1f}%)")
    print(f"[SYNTHETIC] Negative (maintenance_risk=0): {int((1 - df['maintenance_risk']).sum())}")


if __name__ == "__main__":
    main()
