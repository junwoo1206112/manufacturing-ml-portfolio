from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.config import LATEST_MODEL_META_PATH, LATEST_MODEL_PATH, MODELS_DIR
from src.logging_config import get_logger

logger = get_logger(__name__)

ALLOWED_MODEL_TYPES = {
    "RandomForestClassifier",
    "GradientBoostingClassifier",
    "LogisticRegression",
    "SVC",
    "VotingClassifier",
    "DecisionTreeClassifier",
    "IsolationForest",
}


class ModelManager:
    def __init__(self, model_dir: Optional[Union[str, Path]] = None) -> None:
        self.model_dir = Path(model_dir) if model_dir else MODELS_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def save_model(
        self, model: Any, name: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = f"{name}_v{version}.joblib"
        model_path = self.model_dir / model_name

        import joblib

        joblib.dump(model, model_path)

        meta: Dict[str, Any] = {
            "name": name,
            "version": version,
            "saved_at": datetime.now().isoformat(),
            "model_type": type(model).__name__,
            "model_path": str(model_path),
            "schema_version": "2.0",
            **(metadata or {}),
        }

        meta_path = self.model_dir / f"{name}_v{version}_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        shutil.copy2(model_path, LATEST_MODEL_PATH)
        shutil.copy2(meta_path, LATEST_MODEL_META_PATH)
        logger.info("Latest model alias updated: %s", LATEST_MODEL_PATH)

        logger.info("Model saved: %s", model_path)
        return str(model_path)

    def load_model(self, model_path: Union[str, Path], validate: bool = True) -> Any:
        import joblib

        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {model_path}")

        file_size = path.stat().st_size
        if file_size > 100 * 1024 * 1024:
            raise ValueError(f"파일 크기가 너무 큽니다: {file_size / 1024 / 1024:.1f}MB")

        model = joblib.load(model_path)

        if validate:
            model_type = type(model).__name__
            if model_type not in ALLOWED_MODEL_TYPES:
                raise TypeError(
                    f"허용되지 않은 모델 타입: {model_type}. "
                    f"허용: {ALLOWED_MODEL_TYPES}"
                )

            if not hasattr(model, "predict"):
                raise AttributeError("모델에 predict 메서드가 없습니다.")

        logger.info("Model loaded: %s", model_path)
        return model

    def compute_checksum(self, model_path: Union[str, Path]) -> str:
        sha256 = hashlib.sha256()
        with open(model_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def list_models(self, name: Optional[str] = None) -> List[Dict[str, Any]]:
        models: List[Dict[str, Any]] = []
        for p in self.model_dir.glob("*_meta.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except (UnicodeDecodeError, json.JSONDecodeError):
                logger.warning("Skipping unreadable metadata file: %s", p)
                continue
            if name is None or meta.get("name") == name:
                models.append(meta)
        return sorted(models, key=lambda x: x["version"], reverse=True)

    def get_latest_model(self, name: str) -> Optional[Dict[str, Any]]:
        models = self.list_models(name)
        return models[0] if models else None

    def delete_model(self, model_path: Union[str, Path]) -> None:
        p = Path(model_path)
        if p.exists():
            os.remove(p)
            meta_path = p.parent / (p.stem + "_meta.json")
            if meta_path.exists():
                os.remove(meta_path)
            logger.info("Model deleted: %s", model_path)

    def compare_models(self, results: List[Dict[str, Any]]) -> str:
        report = "=" * 60 + "\n"
        report += "모델 비교 리포트\n"
        report += "=" * 60 + "\n\n"

        for i, r in enumerate(results, 1):
            report += f"[{i}] {r.get('name', 'Unknown')}\n"
            report += f"    정확도: {r.get('accuracy', 0):.4f}\n"
            if "precision" in r:
                report += f"    정밀도: {r['precision']:.4f}\n"
            if "recall" in r:
                report += f"    재현율: {r['recall']:.4f}\n"
            if "f1_score" in r:
                report += f"    F1 점수: {r['f1_score']:.4f}\n"
            report += "\n"

        best = max(results, key=lambda x: x.get("accuracy", 0))
        report += f"최고 모델: {best.get('name')} (정확도: {best.get('accuracy', 0):.4f})\n"

        report_path = self.model_dir / "model_comparison_report.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info("Comparison report saved: %s", report_path)
        return report


def save_model(model: Any, name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    manager = ModelManager()
    return manager.save_model(model, name, metadata)


def load_model(model_path: Union[str, Path]) -> Any:
    manager = ModelManager()
    return manager.load_model(model_path)
