from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
    VotingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    auc,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight

from src.config import DATA_DIR, ML_CONFIG
from src.logging_config import get_logger
from src.model_manager import ModelManager

logger = get_logger(__name__)


def _compute_class_weights(y: np.ndarray) -> Dict[int, float]:
    classes = np.unique(y)
    weights = compute_class_weight(class_weight="balanced", classes=classes, y=y)
    return dict(zip(classes, weights))


def _to_scalar(value: Any, index: int = 1) -> float:
    """Convert TreeExplainer/KernelExplainer expected value to float."""
    if isinstance(value, np.ndarray):
        return float(value.item() if value.ndim == 0 else value[index])
    if isinstance(value, list):
        return float(value[index])
    return float(value)


class QualityPredictor:
    def __init__(self, model_type: str = "random_forest") -> None:
        self.model_type: str = model_type
        self.model: Any = self._create_model(model_type)
        self.feature_columns: List[str] = [
            "temperature",
            "pressure",
            "vibration",
            "humidity",
            "cycle_time",
        ]
        self.model_manager: ModelManager = ModelManager()
        self.threshold: float = 0.5
        self.metrics: Dict[str, Any] = {}
        self.class_distribution: Dict[str, int] = {}
        self.training_config: Dict[str, Any] = {}

    def _create_model(self, model_type: str) -> Any:
        models = {
            "random_forest": RandomForestClassifier(
                **ML_CONFIG["models"]["random_forest"],
                random_state=ML_CONFIG["random_state"],
            ),
            "gradient_boosting": GradientBoostingClassifier(
                **ML_CONFIG["models"]["gradient_boosting"],
                random_state=ML_CONFIG["random_state"],
            ),
            "logistic_regression": LogisticRegression(
                **ML_CONFIG["models"]["logistic_regression"],
                random_state=ML_CONFIG["random_state"],
            ),
            "ensemble": self._create_ensemble(),
        }
        return models.get(model_type, models["random_forest"])

    def _create_ensemble(self) -> VotingClassifier:
        rf = RandomForestClassifier(
            n_estimators=100, random_state=42, class_weight="balanced"
        )
        gb = GradientBoostingClassifier(n_estimators=100, random_state=42)
        lr = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")

        return VotingClassifier(
            estimators=[("rf", rf), ("gb", gb), ("lr", lr)], voting="soft"
        )

    def prepare_data(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.Series]:
        X = df[self.feature_columns]
        y = df["is_defective"]
        return X, y

    def _fit_with_sample_weight(self, X: pd.DataFrame, y: pd.Series) -> None:
        if isinstance(self.model, GradientBoostingClassifier):
            class_weights = _compute_class_weights(y.values)
            sample_weight = np.array([class_weights[label] for label in y])
            self.model.fit(X, y, sample_weight=sample_weight)
        else:
            self.model.fit(X, y)

    def _tune_threshold(self, y_true: np.ndarray, y_proba: np.ndarray) -> float:
        metric_name = ML_CONFIG.get("threshold_metric", "f1")
        thresholds = np.arange(0.05, 0.95, 0.01)
        best_score = -1.0
        best_threshold = 0.5

        for t in thresholds:
            preds = (y_proba >= t).astype(int)
            if metric_name == "f1":
                score = f1_score(y_true, preds, zero_division=0)
            elif metric_name == "f2":
                p = precision_score(y_true, preds, zero_division=0)
                r = recall_score(y_true, preds, zero_division=0)
                score = (5 * p * r) / (4 * p + r) if (4 * p + r) > 0 else 0.0
            else:
                score = f1_score(y_true, preds, zero_division=0)

            if score > best_score:
                best_score = score
                best_threshold = t

        return float(best_threshold)

    def _compute_metrics(
        self, y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray
    ) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision_0": float(
                precision_score(y_true, y_pred, pos_label=0, zero_division=0)
            ),
            "recall_0": float(
                recall_score(y_true, y_pred, pos_label=0, zero_division=0)
            ),
            "f1_0": float(f1_score(y_true, y_pred, pos_label=0, zero_division=0)),
            "precision_1": float(
                precision_score(y_true, y_pred, pos_label=1, zero_division=0)
            ),
            "recall_1": float(
                recall_score(y_true, y_pred, pos_label=1, zero_division=0)
            ),
            "f1_1": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
            "precision_macro": float(
                precision_score(y_true, y_pred, average="macro", zero_division=0)
            ),
            "recall_macro": float(
                recall_score(y_true, y_pred, average="macro", zero_division=0)
            ),
            "f1_macro": float(
                f1_score(y_true, y_pred, average="macro", zero_division=0)
            ),
            "precision_weighted": float(
                precision_score(y_true, y_pred, average="weighted", zero_division=0)
            ),
            "recall_weighted": float(
                recall_score(y_true, y_pred, average="weighted", zero_division=0)
            ),
            "f1_weighted": float(
                f1_score(y_true, y_pred, average="weighted", zero_division=0)
            ),
            "auc_roc": float(roc_auc_score(y_true, y_proba)),
        }

        precision_curve, recall_curve, _ = precision_recall_curve(y_true, y_proba)
        metrics["auc_pr"] = float(auc(recall_curve, precision_curve))

        return metrics

    def train(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> Tuple[Dict[str, Any], Tuple[pd.DataFrame, pd.Series]]:
        if y is None and isinstance(X, pd.DataFrame):
            X, y = self.prepare_data(X)

        X_train, X_temp, y_train, y_temp = train_test_split(
            X,
            y,
            test_size=0.3,
            random_state=ML_CONFIG["random_state"],
            stratify=y,
        )
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp,
            y_temp,
            test_size=0.5,
            random_state=ML_CONFIG["random_state"],
            stratify=y_temp,
        )

        self._fit_with_sample_weight(X_train, y_train)

        val_proba = self.model.predict_proba(X_val)[:, 1]
        self.threshold = self._tune_threshold(y_val, val_proba)

        test_proba = self.model.predict_proba(X_test)[:, 1]
        y_pred = (test_proba >= self.threshold).astype(int)

        self.metrics = self._compute_metrics(y_test, y_pred, test_proba)

        class_counts = np.bincount(y_train.astype(int), minlength=2)
        self.class_distribution = {
            "normal": int(class_counts[0]),
            "defect": int(class_counts[1]),
        }
        self.training_config = {
            "model_type": self.model_type,
            "threshold_metric": ML_CONFIG.get("threshold_metric", "f1"),
            "random_state": ML_CONFIG["random_state"],
        }

        logger.info("Optimized threshold: %.4f", self.threshold)
        logger.info("\n=== Classification Report ===")
        logger.info(
            "\n%s",
            classification_report(
                y_test, y_pred, target_names=["정상", "불량"], digits=4
            ),
        )
        logger.info("AUC-ROC: %.4f", self.metrics["auc_roc"])
        logger.info("AUC-PR:  %.4f", self.metrics["auc_pr"])

        return self.metrics, (X_test, y_test)

    def predict(
        self, X: Union[pd.DataFrame, np.ndarray]
    ) -> Tuple[np.ndarray, np.ndarray]:
        probabilities = self.model.predict_proba(X)
        positive_proba = probabilities[:, 1]
        predictions = (positive_proba >= self.threshold).astype(int)
        return predictions, probabilities

    def get_feature_importance(self) -> pd.DataFrame:
        if hasattr(self.model, "feature_importances_"):
            importance = self.model.feature_importances_
        elif hasattr(self.model, "estimators_"):
            importances: List[np.ndarray] = []
            for est in self.model.estimators_:
                if hasattr(est, "feature_importances_"):
                    importances.append(est.feature_importances_)
            importance = (
                np.mean(importances, axis=0)
                if importances
                else np.zeros(len(self.feature_columns))
            )
        else:
            return pd.DataFrame(
                {
                    "feature": self.feature_columns,
                    "importance": [0] * len(self.feature_columns),
                }
            )

        feature_importance = pd.DataFrame(
            {"feature": self.feature_columns, "importance": importance}
        ).sort_values("importance", ascending=False)
        return feature_importance

    def explain_prediction(
        self, X_sample: Union[pd.DataFrame, np.ndarray]
    ) -> Dict[str, Any]:
        import shap
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        from sklearn.tree import DecisionTreeClassifier

        if isinstance(X_sample, np.ndarray):
            X_sample = pd.DataFrame(X_sample, columns=self.feature_columns)

        X_sample = X_sample[self.feature_columns]

        if isinstance(
            self.model, (RandomForestClassifier, GradientBoostingClassifier, DecisionTreeClassifier)
        ):
            explainer = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(X_sample)
            if isinstance(shap_values, list):
                shap_values = shap_values[1]
            expected_value = _to_scalar(explainer.expected_value)
        else:
            background = pd.DataFrame(
                np.zeros((10, len(self.feature_columns))),
                columns=self.feature_columns,
            )
            explainer = shap.KernelExplainer(self.model.predict_proba, background)
            shap_values = explainer.shap_values(X_sample)
            if isinstance(shap_values, list):
                shap_values = shap_values[1]
            expected_value = _to_scalar(explainer.expected_value)

        if isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
            shap_values = shap_values[..., 1]

        return {
            "expected_value": expected_value,
            "shap_values": shap_values[0].tolist() if len(shap_values) > 0 else [],
            "feature_values": X_sample.iloc[0].to_dict(),
            "feature_columns": self.feature_columns,
        }

    def save_model(self, name: str = "quality_predictor") -> str:
        feature_importance = self.get_feature_importance()
        metadata = {
            "model_type": self.model_type,
            "feature_columns": self.feature_columns,
            "threshold": self.threshold,
            "threshold_metric": ML_CONFIG.get("threshold_metric", "f1"),
            "class_distribution": self.class_distribution,
            "training_config": self.training_config,
            "feature_importance": feature_importance.to_dict("records"),
            "metrics": self.metrics,
        }
        return self.model_manager.save_model(self.model, name, metadata)

    def load_model(self, filepath: str) -> None:
        self.model = self.model_manager.load_model(filepath)


def run_quality_prediction(df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    print("=== 품질 예측 모델 학습 ===")

    if df is None:
        csv_path = DATA_DIR / "manufacturing_data.csv"
        df = pd.read_csv(csv_path)

    predictor = QualityPredictor(model_type="random_forest")

    print("\n모델 학습 중...")
    assert df is not None
    metrics, (X_test, y_test) = predictor.train(df)

    print("\n=== 특성 중요도 ===")
    importance = predictor.get_feature_importance()
    for _, row in importance.iterrows():
        print(f"  {row['feature']}: {row['importance']:.4f}")

    predictor.save_model()

    print("\n=== 예측 테스트 ===")
    test_data = pd.DataFrame(
        {
            "temperature": [25, 38, 30],
            "pressure": [100, 95, 105],
            "vibration": [0.5, 0.8, 0.4],
            "humidity": [60, 70, 55],
            "cycle_time": [30, 35, 28],
        }
    )

    predictions, probabilities = predictor.predict(test_data)

    for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
        status = "불량" if pred == 1 else "정상"
        print(f"  샘플 {i+1}: {status} (확률: {prob[1]*100:.2f}%)")

    print("\n=== SHAP 설명 (샘플 1) ===")
    explanation = predictor.explain_prediction(test_data.iloc[[0]])
    for feature, value in zip(
        explanation["feature_columns"], explanation["shap_values"]
    ):
        print(f"  {feature}: {value:.4f}")

    return metrics


if __name__ == "__main__":
    run_quality_prediction()
