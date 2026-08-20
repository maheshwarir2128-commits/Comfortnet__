"""
Trains the ComfortNet predictive-maintenance ML prototype on synthetic
telemetry and saves the model artifact + metadata.

STATUS: SIMULATED / SYNTHETIC DATA ONLY. Trained and evaluated entirely
on the generator in ml/synthetic_data.py. No physical ComfortNet node has
ever produced real telemetry. Metrics printed/saved by this script are
REAL — they come from an actual train/test split and an actual fitted
model, not invented numbers — but they measure performance on synthetic
data, which is not the same as real-world validation.

Run:
    python -m ml.train_model
or:
    python ml/train_model.py
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
)
import joblib

from ml.synthetic_data import generate_synthetic_dataset, RANDOM_STATE
from ml.features import engineer_features, FEATURE_NAMES

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "maintenance_model.joblib"
FEATURE_METADATA_PATH = ARTIFACT_DIR / "feature_metadata.json"
EVAL_METRICS_PATH = ARTIFACT_DIR / "evaluation_metrics.json"


def train(n_samples: int = 8000, random_state: int = RANDOM_STATE) -> dict:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("ComfortNet Predictive-Maintenance ML — SYNTHETIC DATA TRAINING")
    print("=" * 60)

    raw = generate_synthetic_dataset(n_samples=n_samples, random_state=random_state)
    X = engineer_features(raw)
    y = raw["maintenance_risk"]

    print(f"\nSynthetic dataset:")
    print(f"  Samples:              {len(raw)}")
    print(f"  Positive risk cases:  {int(y.sum())} ({y.mean()*100:.1f}%)")
    print(f"  Negative cases:       {int((1 - y).sum())} ({(1 - y.mean())*100:.1f}%)")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=random_state, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=5,
        random_state=random_state,
        class_weight="balanced",
    )

    t0 = time.time()
    model.fit(X_train, y_train)
    train_seconds = time.time() - t0

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "train_seconds": round(train_seconds, 3),
        "model_type": "RandomForestClassifier",
        "n_estimators": 200,
        "max_depth": 8,
        "random_state": random_state,
        "data_source": "synthetic_telemetry",
        "field_validated": False,
        "production_ready": False,
    }

    print("\nModel: RandomForestClassifier")
    print("\nMetrics (on held-out synthetic test set):")
    print(f"  Accuracy:  {metrics['accuracy']:.4f}")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall:    {metrics['recall']:.4f}")
    print(f"  F1:        {metrics['f1']:.4f}")
    print(f"  ROC-AUC:   {metrics['roc_auc']:.4f}")
    print(f"\nConfusion matrix [[TN, FP], [FN, TP]]:\n{np.array(metrics['confusion_matrix'])}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['no_risk', 'maintenance_risk'], zero_division=0)}")

    print("Why recall matters here: a false negative means a node heading toward "
          "failure is scored as fine — the operational cost of missing a real risk "
          "case is higher than the cost of an unnecessary inspection (false positive), "
          "so recall is weighted via class_weight='balanced' and should be watched "
          "at least as closely as accuracy.")

    # --- Explainability: feature importances (NOT causal attribution) ---
    importances = dict(zip(FEATURE_NAMES, model.feature_importances_.tolist()))
    importances_sorted = dict(sorted(importances.items(), key=lambda kv: kv[1], reverse=True))

    joblib.dump(model, MODEL_PATH)

    feature_metadata = {
        "feature_names": FEATURE_NAMES,
        "feature_importances": importances_sorted,
        "importance_note": "Model feature importance — not causal attribution.",
        "model_path": str(MODEL_PATH.name),
    }
    with open(FEATURE_METADATA_PATH, "w") as f:
        json.dump(feature_metadata, f, indent=2)

    with open(EVAL_METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nSaved model artifact:      {MODEL_PATH}")
    print(f"Saved feature metadata:    {FEATURE_METADATA_PATH}")
    print(f"Saved evaluation metrics:  {EVAL_METRICS_PATH}")
    print("\nSTATUS: EXECUTED SUCCESSFULLY — these metrics are real outputs of an "
          "actual train/test run on synthetic data, not invented numbers. They do "
          "NOT represent real-world/field-validated accuracy.")

    return metrics


if __name__ == "__main__":
    train()
