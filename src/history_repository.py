"""SQLite persistence for pipeline execution lineage."""

from __future__ import annotations

import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id INTEGER PRIMARY KEY,
    run_type TEXT NOT NULL CHECK (run_type IN ('training', 'dashboard_demo')),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    random_seed INTEGER,
    source_name TEXT NOT NULL,
    record_count INTEGER,
    error_summary TEXT
);
CREATE TABLE IF NOT EXISTS sensor_observations (
    observation_id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES pipeline_runs(run_id),
    observed_at TEXT NOT NULL,
    production_line TEXT NOT NULL,
    temperature REAL NOT NULL,
    pressure REAL NOT NULL,
    vibration REAL NOT NULL,
    humidity REAL NOT NULL,
    cycle_time REAL NOT NULL,
    actual_is_defective INTEGER NOT NULL CHECK (actual_is_defective IN (0, 1))
);
CREATE INDEX IF NOT EXISTS ix_observation_run_time ON sensor_observations(run_id, observed_at);
CREATE INDEX IF NOT EXISTS ix_observation_line_time ON sensor_observations(production_line, observed_at);
CREATE TABLE IF NOT EXISTS model_versions (
    model_version_id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES pipeline_runs(run_id),
    model_name TEXT NOT NULL,
    version TEXT NOT NULL,
    model_type TEXT NOT NULL,
    trained_at TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    artifact_sha256 TEXT NOT NULL,
    threshold REAL,
    feature_columns_json TEXT NOT NULL,
    training_config_json TEXT NOT NULL,
    UNIQUE(model_name, version)
);
CREATE TABLE IF NOT EXISTS model_metrics (
    model_version_id INTEGER NOT NULL REFERENCES model_versions(model_version_id),
    split_name TEXT NOT NULL CHECK (split_name IN ('validation', 'test')),
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    PRIMARY KEY (model_version_id, split_name, metric_name)
);
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id INTEGER PRIMARY KEY,
    model_version_id INTEGER NOT NULL REFERENCES model_versions(model_version_id),
    observation_id INTEGER NOT NULL REFERENCES sensor_observations(observation_id),
    predicted_at TEXT NOT NULL,
    defect_probability REAL NOT NULL CHECK (defect_probability >= 0 AND defect_probability <= 1),
    predicted_is_defective INTEGER NOT NULL CHECK (predicted_is_defective IN (0, 1)),
    threshold REAL NOT NULL CHECK (threshold >= 0 AND threshold <= 1),
    UNIQUE(model_version_id, observation_id)
);
CREATE INDEX IF NOT EXISTS ix_prediction_model_observation ON predictions(model_version_id, observation_id);
CREATE INDEX IF NOT EXISTS ix_prediction_observed_at ON predictions(predicted_at);
CREATE TABLE IF NOT EXISTS drift_reports (
    drift_report_id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES pipeline_runs(run_id),
    created_at TEXT NOT NULL,
    reference_source TEXT NOT NULL,
    live_source TEXT NOT NULL,
    drift_detected INTEGER NOT NULL CHECK (drift_detected IN (0, 1))
);
CREATE TABLE IF NOT EXISTS drift_feature_results (
    drift_report_id INTEGER NOT NULL REFERENCES drift_reports(drift_report_id),
    feature_name TEXT NOT NULL,
    ks_p_value REAL,
    ks_drifted INTEGER,
    psi REAL,
    psi_drifted INTEGER,
    drifted INTEGER NOT NULL,
    PRIMARY KEY (drift_report_id, feature_name)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HistoryRepository:
    """Small SQLite repository; it supplements, never replaces, model artifacts."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    def start_run(self, *, random_seed: int | None, source_name: str, run_type: str = "training") -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                "INSERT INTO pipeline_runs(run_type, started_at, status, random_seed, source_name) VALUES (?, ?, 'running', ?, ?)",
                (run_type, _now(), random_seed, source_name),
            )
            return int(cursor.lastrowid)

    def finish_run(self, run_id: int, *, record_count: int | None = None, error_summary: str | None = None) -> None:
        status = "failed" if error_summary else "succeeded"
        with self.connection() as conn:
            cursor = conn.execute(
                "UPDATE pipeline_runs SET finished_at=?, status=?, record_count=?, error_summary=? WHERE run_id=?",
                (_now(), status, record_count, error_summary, run_id),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"unknown run_id: {run_id}")

    def insert_observations(self, run_id: int, observations: list[dict[str, Any]]) -> list[int]:
        rows = [(
            run_id, str(item["timestamp"]), item["production_line"], float(item["temperature"]),
            float(item["pressure"]), float(item["vibration"]), float(item["humidity"]),
            float(item["cycle_time"]), int(item["is_defective"]),
        ) for item in observations]
        with self.connection() as conn:
            observation_ids: list[int] = []
            for row in rows:
                cursor = conn.execute(
                "INSERT INTO sensor_observations(run_id, observed_at, production_line, temperature, pressure, vibration, humidity, cycle_time, actual_is_defective) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                row,
                )
                observation_ids.append(int(cursor.lastrowid))
            return observation_ids

    def quality_by_day(self, *, date_from: str | None = None, date_to: str | None = None, line: str | None = None) -> list[dict[str, Any]]:
        clauses, params = ["1=1"], []
        if date_from:
            clauses.append("date(observed_at) >= date(?)"); params.append(date_from)
        if date_to:
            clauses.append("date(observed_at) <= date(?)"); params.append(date_to)
        if line:
            clauses.append("production_line = ?"); params.append(line)
        query = "SELECT date(observed_at) AS date, production_line, COUNT(*) AS record_count, ROUND(AVG(actual_is_defective) * 100, 4) AS defect_rate FROM sensor_observations WHERE " + " AND ".join(clauses) + " GROUP BY date(observed_at), production_line ORDER BY date, production_line"
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def register_model(self, run_id: int, metadata: dict[str, Any], artifact_sha256: str) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                "INSERT INTO model_versions(run_id, model_name, version, model_type, trained_at, artifact_path, artifact_sha256, threshold, feature_columns_json, training_config_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, metadata["name"], metadata["version"], metadata["model_type"], metadata["saved_at"], metadata["model_path"], artifact_sha256, metadata.get("threshold"), json.dumps(metadata.get("feature_columns", [])), json.dumps(metadata.get("training_config", {}))),
            )
            model_version_id = int(cursor.lastrowid)
            conn.executemany(
                "INSERT INTO model_metrics(model_version_id, split_name, metric_name, metric_value) VALUES (?, 'test', ?, ?)",
                [(model_version_id, name, float(value)) for name, value in metadata.get("metrics", {}).items()],
            )
            return model_version_id

    def record_drift(self, run_id: int, report: dict[str, Any], *, reference_source: str, live_source: str) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                "INSERT INTO drift_reports(run_id, created_at, reference_source, live_source, drift_detected) VALUES (?, ?, ?, ?, ?)",
                (run_id, _now(), reference_source, live_source, int(bool(report["drift_detected"]))),
            )
            report_id = int(cursor.lastrowid)
            conn.executemany(
                "INSERT INTO drift_feature_results(drift_report_id, feature_name, ks_p_value, ks_drifted, psi, psi_drifted, drifted) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(report_id, item["feature"], item.get("ks_p_value"), int(bool(item.get("ks_drifted"))), item.get("psi"), int(bool(item.get("psi_drifted"))), int(bool(item["drifted"]))) for item in report["drifted_features"]],
            )
            return report_id

    def record_predictions(
        self,
        model_version_id: int,
        observation_ids: list[int],
        predicted_is_defective: list[int],
        defect_probabilities: list[float],
        *,
        threshold: float,
    ) -> None:
        """Persist only scored observations, preserving their model and source row lineage."""
        if not (len(observation_ids) == len(predicted_is_defective) == len(defect_probabilities)):
            raise ValueError("prediction inputs must have the same length")
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")
        rows = []
        for observation_id, prediction, probability in zip(observation_ids, predicted_is_defective, defect_probabilities):
            if prediction not in (0, 1) or not 0 <= probability <= 1:
                raise ValueError("predictions must be binary and probabilities must be between 0 and 1")
            rows.append((model_version_id, observation_id, _now(), probability, prediction, threshold))
        with self.connection() as conn:
            model_run = conn.execute(
                "SELECT run_id FROM model_versions WHERE model_version_id=?", (model_version_id,)
            ).fetchone()
            if model_run is None:
                raise ValueError(f"unknown model_version_id: {model_version_id}")
            if observation_ids:
                placeholders = ", ".join("?" for _ in observation_ids)
                matched_observations = conn.execute(
                    "SELECT COUNT(*) FROM sensor_observations WHERE run_id=? AND observation_id IN (" + placeholders + ")",
                    [model_run["run_id"], *observation_ids],
                ).fetchone()[0]
                if matched_observations != len(set(observation_ids)):
                    raise ValueError("predictions must reference observations from the model run")
            conn.executemany(
                "INSERT INTO predictions(model_version_id, observation_id, predicted_at, defect_probability, predicted_is_defective, threshold) VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )

    def predicted_defects_by_day(
        self, *, date_from: str | None = None, date_to: str | None = None, line: str | None = None
    ) -> list[dict[str, Any]]:
        clauses, params = ["1=1"], []
        if date_from:
            clauses.append("date(o.observed_at) >= date(?)"); params.append(date_from)
        if date_to:
            clauses.append("date(o.observed_at) <= date(?)"); params.append(date_to)
        if line:
            clauses.append("o.production_line = ?"); params.append(line)
        query = (
            "SELECT date(o.observed_at) AS date, o.production_line, COUNT(*) AS prediction_count, "
            "SUM(p.predicted_is_defective) AS predicted_defect_count "
            "FROM predictions p JOIN sensor_observations o ON o.observation_id = p.observation_id "
            "WHERE " + " AND ".join(clauses) + " GROUP BY date(o.observed_at), o.production_line ORDER BY date, o.production_line"
        )
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def latest_model_metrics(self) -> dict[str, Any] | None:
        with self.connection() as conn:
            model = conn.execute(
                "SELECT model_version_id, model_name, version, trained_at, threshold FROM model_versions ORDER BY model_version_id DESC LIMIT 1"
            ).fetchone()
            if model is None:
                return None
            result = dict(model)
            metrics = conn.execute(
                "SELECT metric_name, metric_value FROM model_metrics WHERE model_version_id=? AND split_name='test' ORDER BY metric_name",
                (model["model_version_id"],),
            ).fetchall()
            result["metrics"] = {row["metric_name"]: row["metric_value"] for row in metrics}
            return result

    def latest_models(self, limit: int = 10) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT model_name, version, model_type, trained_at, threshold, artifact_sha256 FROM model_versions ORDER BY trained_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]

    def latest_drift(self) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT drift_report_id, created_at, reference_source, live_source, drift_detected FROM drift_reports ORDER BY drift_report_id DESC LIMIT 1").fetchone()
            return dict(row) if row else None
