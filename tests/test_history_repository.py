from __future__ import annotations

from pathlib import Path

import pytest

from src.history_repository import HistoryRepository


@pytest.fixture
def repository(tmp_path: Path) -> HistoryRepository:
    repo = HistoryRepository(tmp_path / "history.db")
    repo.initialize()
    return repo


def _observation(defective: int = 0) -> dict:
    return {"timestamp": "2026-01-02T00:00:00+00:00", "production_line": "Line_A", "temperature": 25.0, "pressure": 100.0, "vibration": 0.5, "humidity": 55.0, "cycle_time": 30.0, "is_defective": defective}


def test_observations_are_queryable_by_date_and_line(repository: HistoryRepository) -> None:
    run_id = repository.start_run(random_seed=42, source_name="synthetic")
    repository.insert_observations(run_id, [_observation(0), _observation(1)])
    repository.finish_run(run_id, record_count=2)
    assert repository.quality_by_day(date_from="2026-01-02", line="Line_A") == [{"date": "2026-01-02", "production_line": "Line_A", "record_count": 2, "defect_rate": 50.0}]


def test_foreign_key_rejects_unknown_run(repository: HistoryRepository) -> None:
    with pytest.raises(Exception):
        repository.insert_observations(999, [_observation()])


def test_model_and_drift_history_are_registered(repository: HistoryRepository) -> None:
    run_id = repository.start_run(random_seed=42, source_name="synthetic")
    model_version_id = repository.register_model(run_id, {"name": "quality_predictor", "version": "20260101_120000", "model_type": "RandomForestClassifier", "saved_at": "2026-01-01T12:00:00+00:00", "model_path": "models/quality.joblib", "threshold": 0.42, "feature_columns": ["temperature"], "training_config": {"random_state": 42}, "metrics": {"f1_1": 0.5, "auc_pr": 0.6}}, "a" * 64)
    assert repository.latest_models()[0]["version"] == "20260101_120000"
    observation_ids = repository.insert_observations(run_id, [_observation(0), _observation(1)])
    repository.record_predictions(model_version_id, observation_ids, [0, 1], [0.1, 0.9], threshold=0.42)
    assert repository.predicted_defects_by_day() == [{"date": "2026-01-02", "production_line": "Line_A", "prediction_count": 2, "predicted_defect_count": 1}]
    latest_metrics = repository.latest_model_metrics()
    assert latest_metrics is not None
    assert latest_metrics["metrics"] == {"auc_pr": 0.6, "f1_1": 0.5}
    repository.record_drift(run_id, {"drift_detected": True, "drifted_features": [{"feature": "temperature", "ks_p_value": 0.01, "ks_drifted": True, "psi": 0.2, "psi_drifted": True, "drifted": True}]}, reference_source="synthetic_reference", live_source="synthetic_shift")
    assert repository.latest_drift()["drift_detected"] == 1


def test_predictions_require_valid_lineage_and_probability(repository: HistoryRepository) -> None:
    run_id = repository.start_run(random_seed=42, source_name="synthetic")
    model_version_id = repository.register_model(run_id, {"name": "quality_predictor", "version": "20260101_120001", "model_type": "RandomForestClassifier", "saved_at": "2026-01-01T12:00:00+00:00", "model_path": "models/quality.joblib", "threshold": 0.42, "feature_columns": ["temperature"], "training_config": {}, "metrics": {}}, "b" * 64)
    observation_id = repository.insert_observations(run_id, [_observation()])[0]
    with pytest.raises(ValueError):
        repository.record_predictions(model_version_id, [observation_id], [1], [1.1], threshold=0.42)
    other_run_id = repository.start_run(random_seed=7, source_name="other")
    other_observation_id = repository.insert_observations(other_run_id, [_observation()])[0]
    with pytest.raises(ValueError, match="model run"):
        repository.record_predictions(model_version_id, [other_observation_id], [1], [0.9], threshold=0.42)
