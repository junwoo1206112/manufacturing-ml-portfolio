from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.drift_detector import DriftDetector, NUMERIC_FEATURES


@pytest.fixture
def reference_df() -> pd.DataFrame:
    np.random.seed(42)
    n = 1000
    return pd.DataFrame(
        {
            "temperature": np.random.normal(27, 5, n),
            "pressure": np.random.normal(105, 10, n),
            "vibration": np.random.normal(0.5, 0.2, n),
            "humidity": np.random.normal(60, 10, n),
            "cycle_time": np.random.normal(32, 5, n),
            "defect_probability": np.random.uniform(0, 0.3, n),
            "is_defective": np.random.binomial(1, 0.05, n),
            "production_line": np.random.choice(["Line_A", "Line_B", "Line_C"], n),
        }
    )


@pytest.fixture
def detector() -> DriftDetector:
    return DriftDetector(ks_alpha=0.05, psi_threshold=0.1)


class TestDriftDetector:
    def test_ks_detects_drift(self, reference_df: pd.DataFrame, detector: DriftDetector):
        live_df = reference_df.copy()
        live_df["temperature"] = live_df["temperature"] + 5.0

        ks_results = detector.ks_test(reference_df, live_df)
        assert ks_results["temperature"]["drifted"] is True
        assert ks_results["temperature"]["p_value"] < 0.05

    def test_psi_detects_drift(self, reference_df: pd.DataFrame, detector: DriftDetector):
        live_df = reference_df.copy()
        live_df["vibration"] = live_df["vibration"] * 2.0

        psi_results = detector.psi(reference_df, live_df)
        assert psi_results["vibration"]["drifted"] is True
        assert psi_results["vibration"]["psi"] > 0.1

    def test_no_drift_on_identical(self, reference_df: pd.DataFrame, detector: DriftDetector):
        live_df = reference_df.copy()

        ks_results = detector.ks_test(reference_df, live_df)
        psi_results = detector.psi(reference_df, live_df)

        for col in NUMERIC_FEATURES:
            if col in ks_results:
                assert ks_results[col]["p_value"] > 0.05
            if col in psi_results:
                assert psi_results[col]["psi"] < 0.1

    def test_config_override(self):
        custom_detector = DriftDetector(ks_alpha=0.01, psi_threshold=0.2)
        assert custom_detector.ks_alpha == 0.01
        assert custom_detector.psi_threshold == 0.2

    def test_detect_report_structure(
        self, reference_df: pd.DataFrame, detector: DriftDetector
    ):
        live_df = reference_df.copy()
        live_df["temperature"] = live_df["temperature"] + 5.0

        report = detector.detect(reference_df, live_df)
        assert "drifted_features" in report
        assert "drift_detected" in report
        assert "ks_results" in report
        assert "psi_results" in report
        assert report["drift_detected"] is True

    def test_no_drift_on_identical_detect(
        self, reference_df: pd.DataFrame, detector: DriftDetector
    ):
        live_df = reference_df.copy()

        report = detector.detect(reference_df, live_df)
        assert report["drift_detected"] is False
