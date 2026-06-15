from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict

import yaml


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent

DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
VISUALIZATIONS_DIR = BASE_DIR / "visualizations"
CONFIG_DIR = BASE_DIR / "config"

DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
VISUALIZATIONS_DIR.mkdir(exist_ok=True)

DEFAULT_DATA_CONFIG: Dict[str, Any] = {
    "num_records": 5000,
    "start_date": "2026-01-01",
    "random_seed": 42,
    "train_ratio": 0.7,
    "val_ratio": 0.15,
    "test_ratio": 0.15,
}

DEFAULT_PRODUCTION_LINES: Dict[str, Dict[str, Any]] = {
    "Line_A": {
        "name": "전자부품 라인",
        "temp_range": (22, 38),
        "pressure_range": (95, 115),
        "vibration_range": (0.3, 0.9),
        "humidity_range": (45, 75),
        "cycle_time_range": (25, 40),
        "defect_baseline": 0.04,
    },
    "Line_B": {
        "name": "기계부품 라인",
        "temp_range": (18, 32),
        "pressure_range": (100, 125),
        "vibration_range": (0.2, 0.7),
        "humidity_range": (40, 65),
        "cycle_time_range": (30, 50),
        "defect_baseline": 0.03,
    },
    "Line_C": {
        "name": "소비재 라인",
        "temp_range": (20, 35),
        "pressure_range": (90, 110),
        "vibration_range": (0.4, 0.8),
        "humidity_range": (50, 80),
        "cycle_time_range": (20, 35),
        "defect_baseline": 0.05,
    },
}

DEFAULT_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "vibration": {"warning": 0.6, "critical": 0.8},
    "temperature": {"warning": 32, "critical": 38},
    "pressure": {"warning": 110, "critical": 120},
}

DEFAULT_ML_CONFIG: Dict[str, Any] = {
    "test_size": 0.2,
    "random_state": 42,
    "cv_folds": 5,
    "threshold_metric": "f1",
    "models": {
        "random_forest": {"n_estimators": 100, "max_depth": 10, "class_weight": "balanced"},
        "gradient_boosting": {"n_estimators": 100, "learning_rate": 0.1},
        "logistic_regression": {"max_iter": 1000, "class_weight": "balanced"},
    },
}

DEFAULT_DASHBOARD_CONFIG: Dict[str, Any] = {
    "host": "0.0.0.0",
    "port": 5001,
    "debug": True,
}

DEFAULT_DRIFT_CONFIG: Dict[str, Any] = {
    "ks_alpha": 0.05,
    "psi_threshold": 0.1,
    "reference_window": 5000,
}


def _load_yaml_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        logger.warning("YAML 설정 로드 실패: %s", path, exc_info=True)
        return {}


def _normalize_ranges(lines_config: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for line_id, line in lines_config.items():
        line = dict(line)
        for key in line:
            if key.endswith("_range") and isinstance(line[key], list) and len(line[key]) == 2:
                line[key] = tuple(line[key])
        normalized[line_id] = line
    return normalized


def _deep_merge(default: Any, override: Any) -> Any:
    if isinstance(default, dict) and isinstance(override, dict):
        result = dict(default)
        for key, value in override.items():
            result[key] = _deep_merge(result.get(key), value)
        return result
    return override if override is not None else default


raw_config = _load_yaml_config(CONFIG_DIR / "config.yaml")

DATA_CONFIG = _deep_merge(DEFAULT_DATA_CONFIG, raw_config.get("data"))
PRODUCTION_LINES = _normalize_ranges(
    _deep_merge(DEFAULT_PRODUCTION_LINES, raw_config.get("production_lines"))
)
THRESHOLDS = _deep_merge(DEFAULT_THRESHOLDS, raw_config.get("thresholds"))
ML_CONFIG = _deep_merge(DEFAULT_ML_CONFIG, raw_config.get("ml"))
DASHBOARD_CONFIG = _deep_merge(DEFAULT_DASHBOARD_CONFIG, raw_config.get("dashboard"))
DRIFT_CONFIG = _deep_merge(DEFAULT_DRIFT_CONFIG, raw_config.get("drift"))

DATA_FILE = DATA_DIR / "manufacturing_data.csv"
EQUIPMENT_FILE = CONFIG_DIR / "equipment.json"
LATEST_MODEL_PATH = MODELS_DIR / "quality_predictor_latest.joblib"
LATEST_MODEL_META_PATH = MODELS_DIR / "quality_predictor_latest_meta.json"
