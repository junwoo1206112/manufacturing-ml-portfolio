import json
import os
import sys
import tempfile

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.anomaly_detector import AnomalyDetector, detect_anomalies
from src.data_generator import generate_manufacturing_data
from src.model_manager import ModelManager
from src.quality_predictor import QualityPredictor


class TestQualityPredictor:
    def setup_method(self):
        self.df = generate_manufacturing_data(500)

    def test_predictor_initialization(self):
        predictor = QualityPredictor()
        assert predictor.model is not None

    def test_prepare_data(self):
        predictor = QualityPredictor()
        X, y = predictor.prepare_data(self.df)
        assert len(X) == len(self.df)
        assert len(y) == len(self.df)

    def test_train(self):
        predictor = QualityPredictor()
        X, y = predictor.prepare_data(self.df)
        metrics, _ = predictor.train(X, y)
        assert "accuracy" in metrics
        assert "f1_1" in metrics

    def test_train_with_dataframe(self):
        from src.data_pipeline import prepare_training_data
        predictor = QualityPredictor()
        train_data = prepare_training_data(self.df)
        metrics, _ = predictor.train(train_data["full_df"])
        assert "accuracy" in metrics
        assert "f1_1" in metrics

    def test_predict(self):
        predictor = QualityPredictor()
        X, y = predictor.prepare_data(self.df)
        predictor.train(X, y)
        predictions, probabilities = predictor.predict(X.head(10))
        assert len(predictions) == 10
        assert len(probabilities) == 10

    def test_feature_importance(self):
        predictor = QualityPredictor()
        X, y = predictor.prepare_data(self.df)
        predictor.train(X, y)
        importance = predictor.get_feature_importance()
        assert len(importance) > 0
        assert "feature" in importance.columns
        assert "importance" in importance.columns

    def test_defect_class_is_detectable(self):
        predictor = QualityPredictor()
        X, y = predictor.prepare_data(self.df)
        metrics, _ = predictor.train(X, y)
        assert metrics["f1_1"] > 0.0

    def test_explain_prediction_returns_valid_shap_values(self):
        pytest.importorskip("shap")
        predictor = QualityPredictor()
        X, y = predictor.prepare_data(self.df)
        predictor.train(X, y)

        explanation = predictor.explain_prediction(X.head(1))
        assert "expected_value" in explanation
        assert "shap_values" in explanation
        assert len(explanation["shap_values"]) == len(predictor.feature_columns)
        assert "feature_values" in explanation
        assert "feature_columns" in explanation

    def test_save_model_metadata_schema(self):
        predictor = QualityPredictor()
        X, y = predictor.prepare_data(self.df)
        predictor.train(X, y)

        with tempfile.TemporaryDirectory() as tmpdir:
            predictor.model_manager = ModelManager(tmpdir)
            predictor.save_model("test_meta")

            meta_files = [
                p for p in os.listdir(tmpdir) if p.endswith("_meta.json")
            ]
            assert len(meta_files) == 1
            meta_path = os.path.join(tmpdir, meta_files[0])

            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

            required_keys = {
                "schema_version",
                "name",
                "version",
                "saved_at",
                "model_type",
                "model_path",
                "feature_columns",
                "threshold",
                "threshold_metric",
                "class_distribution",
                "training_config",
                "feature_importance",
                "metrics",
            }
            assert required_keys.issubset(meta.keys())
            assert meta["schema_version"] == "2.0"
            assert meta["threshold_metric"] == "f1"
            assert isinstance(meta["feature_columns"], list)
            assert isinstance(meta["feature_importance"], list)
            assert isinstance(meta["metrics"], dict)
            assert {"normal", "defect"}.issubset(meta["class_distribution"].keys())


class TestAnomalyDetector:
    def setup_method(self):
        self.df = generate_manufacturing_data(200)

    def test_detector_fit(self):
        detector = AnomalyDetector()
        detector.fit(self.df)
        assert detector.model is not None

    def test_detector_predict(self):
        detector = AnomalyDetector()
        detector.fit(self.df)
        result = detector.predict(self.df)
        assert "is_anomaly" in result.columns
        assert "anomaly_score" in result.columns

    def test_anomaly_summary(self):
        detector = AnomalyDetector()
        detector.fit(self.df)
        result = detector.predict(self.df)
        summary = detector.get_anomaly_summary(result)
        assert "total_records" in summary
        assert "anomaly_count" in summary

    def test_detect_anomalies_function(self):
        result = detect_anomalies(self.df)
        assert "detector" in result
        assert "dataframe" in result
        assert "summary" in result


class TestModelManager:
    def setup_method(self):
        self.manager = ModelManager()

    def test_save_and_load(self):
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(np.random.rand(100, 5), np.random.randint(0, 2, 100))

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ModelManager(tmpdir)
            path = manager.save_model(model, "test")
            loaded = manager.load_model(path)
            assert loaded is not None

    def test_list_models(self):
        models = self.manager.list_models()
        assert isinstance(models, list)

    def test_save_and_load_isolation_forest(self):
        from sklearn.ensemble import IsolationForest
        model = IsolationForest(n_estimators=10, random_state=42)
        model.fit(np.random.rand(100, 5))

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ModelManager(tmpdir)
            path = manager.save_model(model, "anomaly")
            loaded = manager.load_model(path)
            assert loaded is not None

    def test_compare_models(self):
        results = [
            {"name": "model_a", "accuracy": 0.85},
            {"name": "model_b", "accuracy": 0.90},
        ]
        report = self.manager.compare_models(results)
        assert "최고 모델" in report
