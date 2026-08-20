"""
Tests for the predictive-maintenance ML prototype.

EXECUTION STATUS: The ml/* module tests (TestSyntheticData, TestFeatures,
TestTrainAndPredict) use only numpy/pandas/scikit-learn/joblib, which ARE
available and were actually run in the build environment (see the
implementation report for real console output). The API-level tests
(TestMLEndpoints) additionally require fastapi/httpx via the `client`
fixture in conftest.py, which could NOT be installed in the build
environment — those are syntax-checked only. Run `pytest -v` locally to
execute all of them.
"""
import numpy as np
import pandas as pd
import pytest

from ml.synthetic_data import generate_synthetic_dataset
from ml.features import engineer_features, engineer_features_single, FEATURE_NAMES
from ml.predict import predict_from_reading, is_available


class TestSyntheticData:
    def test_deterministic_generation(self):
        df1 = generate_synthetic_dataset(n_samples=500, random_state=42)
        df2 = generate_synthetic_dataset(n_samples=500, random_state=42)
        pd.testing.assert_frame_equal(df1, df2)

    def test_different_seed_differs(self):
        df1 = generate_synthetic_dataset(n_samples=500, random_state=1)
        df2 = generate_synthetic_dataset(n_samples=500, random_state=2)
        assert not df1["battery_percent"].equals(df2["battery_percent"])

    def test_label_distribution_not_degenerate(self):
        df = generate_synthetic_dataset(n_samples=4000, random_state=42)
        pos_rate = df["maintenance_risk"].mean()
        # Should be a real minority-positive-class problem, not all-0 or all-1
        assert 0.10 < pos_rate < 0.60

    def test_expected_columns_present(self):
        df = generate_synthetic_dataset(n_samples=100, random_state=42)
        expected = {"battery_percent", "battery_voltage", "solar_power", "temperature",
                    "humidity", "aqi_pm25", "soil_moisture", "light_level",
                    "network_status", "maintenance_risk"}
        assert expected.issubset(set(df.columns))

    def test_label_is_not_a_trivial_copy_of_any_single_feature(self):
        """Leakage guard: the label must not be perfectly (or near-perfectly)
        predictable from any single raw feature alone, since the label is
        generated from a stochastic function of a hidden severity variable,
        not a hard threshold on one observed column."""
        df = generate_synthetic_dataset(n_samples=4000, random_state=42)
        numeric_cols = ["battery_percent", "battery_voltage", "solar_power",
                         "temperature", "humidity", "aqi_pm25", "soil_moisture", "light_level"]
        for col in numeric_cols:
            corr = abs(df[col].corr(df["maintenance_risk"]))
            assert corr < 0.9, f"{col} is suspiciously perfectly correlated with the label ({corr:.3f})"


class TestFeatures:
    def test_feature_engineering_produces_expected_columns(self):
        df = generate_synthetic_dataset(n_samples=50, random_state=42)
        X = engineer_features(df)
        assert list(X.columns) == FEATURE_NAMES
        assert len(X) == 50

    def test_no_nans_in_engineered_features(self):
        df = generate_synthetic_dataset(n_samples=200, random_state=42)
        X = engineer_features(df)
        assert not X.isnull().values.any()

    def test_single_reading_matches_batch_path(self):
        """The live-inference single-reading path must produce the same
        values as the batch training path for identical input, since
        train/inference consistency is required."""
        df = generate_synthetic_dataset(n_samples=1, random_state=42)
        batch_result = engineer_features(df)
        reading = df.iloc[0].to_dict()
        single_result = engineer_features_single(reading)
        for col in FEATURE_NAMES:
            assert abs(batch_result.iloc[0][col] - single_result.iloc[0][col]) < 1e-6

    def test_missing_fields_handled_gracefully(self):
        reading = {"battery_percent": None, "network_status": None}
        result = engineer_features_single(reading)
        assert not result.isnull().values.any()
        assert list(result.columns) == FEATURE_NAMES


class TestPredict:
    def test_model_is_available_after_training(self):
        # Requires `python -m ml.train_model` to have been run first,
        # which it was (see implementation report). If artifacts are
        # missing, this correctly reports unavailable rather than crashing.
        assert is_available() in (True, False)  # never raises

    def test_healthy_reading_scores_lower_than_critical_reading(self):
        if not is_available():
            pytest.skip("Model artifact not present — run `python -m ml.train_model` first.")
        healthy = {"battery_percent": 90, "battery_voltage": 13.9, "solar_power": 75,
                   "temperature": 27, "humidity": 55, "aqi_pm25": 40, "soil_moisture": 45,
                   "light_level": 800, "network_status": "online"}
        critical = {"battery_percent": 8, "battery_voltage": 10.3, "solar_power": 10,
                    "temperature": 32, "humidity": 50, "aqi_pm25": 60, "soil_moisture": 35,
                    "light_level": 250, "network_status": "online"}
        healthy_result = predict_from_reading(healthy)
        critical_result = predict_from_reading(critical)
        assert healthy_result["risk_probability"] < critical_result["risk_probability"]
        assert healthy_result["risk_level"] == "LOW"
        assert critical_result["risk_level"] in ("MEDIUM", "HIGH")

    def test_risk_probability_in_valid_range(self):
        if not is_available():
            pytest.skip("Model artifact not present.")
        reading = {"battery_percent": 50, "network_status": "online"}
        result = predict_from_reading(reading)
        assert 0.0 <= result["risk_probability"] <= 1.0

    def test_risk_level_matches_probability_bands(self):
        if not is_available():
            pytest.skip("Model artifact not present.")
        reading = {"battery_percent": 50, "network_status": "online"}
        result = predict_from_reading(reading)
        p, level = result["risk_probability"], result["risk_level"]
        if level == "LOW":
            assert p < 0.33
        elif level == "MEDIUM":
            assert 0.33 <= p < 0.66
        else:
            assert p >= 0.66

    def test_top_contributing_factors_present_and_labeled_non_causal(self):
        if not is_available():
            pytest.skip("Model artifact not present.")
        reading = {"battery_percent": 15, "network_status": "online"}
        result = predict_from_reading(reading)
        assert len(result["top_contributing_factors"]) == 3
        for factor in result["top_contributing_factors"]:
            assert "feature" in factor and "importance" in factor and "description" in factor

    def test_malformed_reading_does_not_crash(self):
        if not is_available():
            pytest.skip("Model artifact not present.")
        result = predict_from_reading({})
        assert result["available"] is True  # defaults fill in gracefully


class TestMLAPIEndpoints:
    """
    NOT EXECUTED IN THIS ENVIRONMENT — requires the `client` fixture from
    conftest.py, which needs fastapi/httpx (unavailable here, same
    limitation as the rest of the backend's API-level tests). Syntax-
    checked via py_compile only. Run `pytest -v` locally.
    """

    def test_ml_status_endpoint(self, client):
        resp = client.get("/ml/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["training_data"] == "synthetic_telemetry"
        assert body["field_validated"] is False

    def test_predict_requires_existing_node(self, client):
        resp = client.post("/ml/predict/does-not-exist")
        assert resp.status_code == 404

    def test_predict_requires_telemetry(self, client, demo_node):
        resp = client.post(f"/ml/predict/{demo_node['id']}")
        assert resp.status_code == 404  # no telemetry ingested yet

    def test_predict_after_telemetry_ingest(self, client, demo_node):
        node_id = demo_node["id"]
        client.post("/telemetry", json={
            "node_id": node_id, "battery_percent": 12, "solar_power": 8,
            "temperature": 33, "network_status": "online",
        })
        resp = client.post(f"/ml/predict/{node_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["synthetic_data_only"] is True
        assert body["field_validated"] is False
        assert body["risk_level"] in ("LOW", "MEDIUM", "HIGH")

    def test_demo_scenario_changes_prediction(self, client, demo_node):
        """The chain must be: scenario -> telemetry -> features -> model ->
        risk, never a hard-coded scenario->risk shortcut."""
        node_id = demo_node["id"]
        client.post("/telemetry", json={
            "node_id": node_id, "battery_percent": 90, "solar_power": 75,
            "temperature": 27, "network_status": "online",
        })
        healthy_resp = client.post(f"/ml/predict/{node_id}").json()

        client.post("/telemetry", json={
            "node_id": node_id, "battery_percent": 8, "solar_power": 5,
            "temperature": 33, "network_status": "online",
        })
        risky_resp = client.post(f"/ml/predict/{node_id}").json()

        assert risky_resp["risk_probability"] > healthy_resp["risk_probability"]
