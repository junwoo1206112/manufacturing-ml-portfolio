from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from src.logging_config import get_logger

logger = get_logger(__name__)


class AnomalyDetector:
    def __init__(self, contamination: float = 0.05) -> None:
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
        )
        self.scaler = StandardScaler()
        self.feature_columns: List[str] = []

    def fit(
        self, df: pd.DataFrame, feature_columns: Optional[List[str]] = None
    ) -> "AnomalyDetector":
        if feature_columns is None:
            feature_columns = ["temperature", "pressure", "vibration", "humidity"]
        self.feature_columns = [c for c in feature_columns if c in df.columns]

        X = df[self.feature_columns].to_numpy()
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)

        logger.info("Anomaly detector fitted on %d features", len(self.feature_columns))
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        X = df[self.feature_columns].to_numpy()
        X_scaled = self.scaler.transform(X)

        predictions = self.model.predict(X_scaled)
        scores = self.model.decision_function(X_scaled)

        df["anomaly_label"] = predictions
        df["anomaly_score"] = scores
        df["is_anomaly"] = (predictions == -1).astype(int)

        return df

    def get_anomaly_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        total = len(df)
        anomalies = int(df["is_anomaly"].sum())

        summary: Dict[str, Any] = {
            "total_records": total,
            "anomaly_count": anomalies,
            "anomaly_rate": float(anomalies / total * 100),
            "normal_count": int(total - anomalies),
        }

        if "production_line" in df.columns:
            line_anomalies = (
                df.groupby("production_line")["is_anomaly"]
                .agg(["sum", "count", "mean"])
                .to_dict("index")
            )
            summary["by_line"] = {
                k: {"count": int(v["sum"]), "rate": float(v["mean"] * 100)}
                for k, v in line_anomalies.items()
            }

        return summary

    def get_top_anomalies(self, df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
        return df.nsmallest(n, "anomaly_score")


def detect_anomalies(
    df: pd.DataFrame, feature_columns: Optional[List[str]] = None
) -> Dict[str, Any]:
    detector = AnomalyDetector()
    detector.fit(df, feature_columns)
    result_df = detector.predict(df)
    summary = detector.get_anomaly_summary(result_df)
    top_anomalies = detector.get_top_anomalies(result_df)

    return {
        "detector": detector,
        "dataframe": result_df,
        "summary": summary,
        "top_anomalies": top_anomalies,
    }
