from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, StratifiedKFold
from sklearn.svm import SVC


logger = logging.getLogger(__name__)


class HyperparameterTuner:
    def __init__(self, cv_folds: int = 5, random_state: int = 42):
        self.cv_folds = cv_folds
        self.random_state = random_state
        self.cv = StratifiedKFold(
            n_splits=cv_folds, shuffle=True, random_state=random_state
        )

    def get_param_grids(self) -> Dict[str, Dict[str, Any]]:
        return {
            "random_forest": {
                "n_estimators": [50, 100, 200],
                "max_depth": [5, 10, 15, None],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4],
            },
            "gradient_boosting": {
                "n_estimators": [50, 100, 200],
                "learning_rate": [0.01, 0.05, 0.1, 0.2],
                "max_depth": [3, 5, 7],
                "min_samples_split": [2, 5],
            },
            "logistic_regression": {
                "C": [0.01, 0.1, 1.0, 10.0],
                "penalty": ["l2"],
                "solver": ["lbfgs"],
            },
            "svm": {
                "C": [0.1, 1.0, 10.0],
                "kernel": ["rbf", "linear"],
                "gamma": ["scale", "auto"],
            },
        }

    def get_models(self) -> Dict[str, Any]:
        return {
            "random_forest": RandomForestClassifier(random_state=self.random_state),
            "gradient_boosting": GradientBoostingClassifier(
                random_state=self.random_state
            ),
            "logistic_regression": LogisticRegression(
                max_iter=1000, random_state=self.random_state
            ),
            "svm": SVC(probability=True, random_state=self.random_state),
        }

    def tune_model(
        self,
        model_name: str,
        X_train: np.ndarray,
        y_train: np.ndarray,
        method: str = "grid",
    ) -> Tuple[Any, Dict[str, Any]]:
        models = self.get_models()
        param_grids = self.get_param_grids()

        if model_name not in models:
            raise ValueError(f"Unknown model: {model_name}")

        model = models[model_name]
        param_grid = param_grids[model_name]

        if method == "grid":
            search = GridSearchCV(
                model, param_grid, cv=self.cv, scoring="accuracy", n_jobs=-1, verbose=0
            )
        elif method == "random":
            search = RandomizedSearchCV(
                model,
                param_grid,
                n_iter=20,
                cv=self.cv,
                scoring="accuracy",
                n_jobs=-1,
                random_state=self.random_state,
                verbose=0,
            )
        else:
            raise ValueError(f"Unknown method: {method}")

        search.fit(X_train, y_train)

        return search.best_estimator_, search.best_params_

    def evaluate_model(
        self, model: Any, X_test: np.ndarray, y_test: np.ndarray
    ) -> Dict[str, float]:
        y_pred = model.predict(X_test)

        return {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(
                y_test, y_pred, average="weighted", zero_division=0
            ),
            "recall": recall_score(
                y_test, y_pred, average="weighted", zero_division=0
            ),
            "f1_score": f1_score(y_test, y_pred, average="weighted", zero_division=0),
        }

    def compare_all_models(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        for model_name in self.get_models().keys():
            logger.info("튜닝 중: %s...", model_name)
            try:
                best_model, best_params = self.tune_model(
                    model_name, X_train, y_train, method="random"
                )
                metrics = self.evaluate_model(best_model, X_test, y_test)

                result: Dict[str, Any] = {
                    "name": model_name,
                    "model": best_model,
                    "best_params": best_params,
                    **metrics,
                }
                results.append(result)

                logger.info("  정확도: %.4f", metrics["accuracy"])
                logger.info("  F1: %.4f", metrics["f1_score"])

            except Exception as e:
                logger.warning("  %s 튜닝 에러: %s", model_name, e)

        return results


def tune_and_compare(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> List[Dict[str, Any]]:
    tuner = HyperparameterTuner()
    return tuner.compare_all_models(X_train, y_train, X_test, y_test)
