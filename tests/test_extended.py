import pytest
import numpy as np
import pandas as pd
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_generator import generate_manufacturing_data
from src.predictive_maintenance import PredictiveMaintenance
from src.hyperparameter_tuner import HyperparameterTuner
from src.visualizer import ManufacturingVisualizer


class TestPredictiveMaintenance:
    def setup_method(self):
        self.pm = PredictiveMaintenance()

    def test_analyze_healthy_equipment(self):
        sensors = {"vibration": 0.4, "temperature": 25, "pressure": 95}
        result = self.pm.analyze_equipment_health("TEST_001", sensors)
        assert result["health_score"] == 100
        assert result["status"] == "양호"
        assert len(result["alerts"]) == 0

    def test_analyze_warning_equipment(self):
        sensors = {"vibration": 0.65, "temperature": 33, "pressure": 95}
        result = self.pm.analyze_equipment_health("TEST_002", sensors)
        assert result["health_score"] == 70
        assert result["status"] == "주의"
        assert len(result["alerts"]) == 2

    def test_analyze_critical_equipment(self):
        sensors = {"vibration": 0.85, "temperature": 39, "pressure": 125}
        result = self.pm.analyze_equipment_health("TEST_003", sensors)
        assert result["health_score"] == 10
        assert result["status"] == "위험"
        assert len(result["alerts"]) == 3

    def test_health_score_minimum_zero(self):
        sensors = {"vibration": 1.0, "temperature": 50, "pressure": 150}
        result = self.pm.analyze_equipment_health("TEST_004", sensors)
        assert result["health_score"] >= 0

    def test_get_status(self):
        assert self.pm._get_status(85) == "양호"
        assert self.pm._get_status(65) == "주의"
        assert self.pm._get_status(45) == "경고"
        assert self.pm._get_status(20) == "위험"

    def test_predict_maintenance_date(self):
        failure_history = [
            {"date": "2026-01-15", "interval": 800},
            {"date": "2026-03-20", "interval": 750},
        ]
        result = self.pm.predict_maintenance_date("TEST_001", 700, failure_history)
        assert "remaining_hours" in result
        assert "recommended_maintenance_date" in result
        assert "confidence" in result
        assert "reliability_score" in result
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["model"] == "lognormal_reliability"

    def test_predict_maintenance_no_history(self):
        result = self.pm.predict_maintenance_date("TEST_002", 500, [])
        assert result["confidence"] == 0.5
        assert result["model"] == "default"

    def test_generate_maintenance_report(self):
        equipment_list = [
            {"id": "CNC_001", "sensors": {"vibration": 0.4, "temperature": 25, "pressure": 95}},
            {"id": "CNC_002", "sensors": {"vibration": 0.7, "temperature": 35, "pressure": 105}},
        ]
        report = self.pm.generate_maintenance_report(equipment_list)
        assert report["total_equipment"] == 2
        assert "양호" in report["status_summary"]
        assert len(report["equipment_details"]) == 2


class TestHyperparameterTuner:
    def setup_method(self):
        self.tuner = HyperparameterTuner(cv_folds=3)

    def test_get_param_grids(self):
        grids = self.tuner.get_param_grids()
        assert "random_forest" in grids
        assert "gradient_boosting" in grids
        assert "logistic_regression" in grids
        assert "svm" in grids

    def test_get_models(self):
        models = self.tuner.get_models()
        assert len(models) == 4
        for name in ["random_forest", "gradient_boosting", "logistic_regression", "svm"]:
            assert name in models

    def test_evaluate_model(self):
        from sklearn.ensemble import RandomForestClassifier
        X = np.random.rand(200, 5)
        y = np.random.randint(0, 2, 200)
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X[:150], y[:150])
        metrics = self.tuner.evaluate_model(model, X[150:], y[150:])
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert 0 <= metrics["accuracy"] <= 1


class TestManufacturingVisualizer:
    def setup_method(self):
        self.df = generate_manufacturing_data(100)
        self.viz = ManufacturingVisualizer()

    def test_plot_defect_analysis(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = tmpdir + "/"
            self.viz.plot_defect_analysis(self.df, save_path=path)
            assert os.path.exists(os.path.join(tmpdir, "defect_analysis.png"))

    def test_plot_time_series(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = tmpdir + "/"
            self.viz.plot_time_series(self.df, save_path=path)
            assert os.path.exists(os.path.join(tmpdir, "time_series.png"))

    def test_plot_correlation_matrix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = tmpdir + "/"
            self.viz.plot_correlation_matrix(self.df, save_path=path)
            assert os.path.exists(os.path.join(tmpdir, "correlation_matrix.png"))

    def test_create_dashboard_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = tmpdir + "/"
            summary = self.viz.create_dashboard_summary(self.df, save_path=path)
            assert os.path.exists(os.path.join(tmpdir, "dashboard_summary.png"))
            assert "total_records" in summary
            assert "defect_rate" in summary
