"""
Smart Manufacturing Simulation Portfolio
소르테크 지원용 포트폴리오 프로젝트

이 프로젝트는 다음 기술을 시연합니다:
1. Python 데이터 분석 (Pandas, NumPy)
2. 머신러닝 모델 개발 (Scikit-learn)
3. 제조 공정 데이터 처리
4. 예측 정비 시스템
5. 데이터 시각화
6. 웹 대시보드 (Flask)
"""

import logging
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import DATA_CONFIG, DATA_DIR, LATEST_MODEL_META_PATH, LATEST_MODEL_PATH, BASE_DIR
from src.data_analyzer import analyze_production_data, save_data
from src.data_generator import generate_manufacturing_data
from src.data_validator import validate_data
from src.drift_detector import DriftDetector
from src.logging_config import setup_logging
from src.history_repository import HistoryRepository
from src.predictive_maintenance import run_predictive_maintenance
from src.quality_predictor import run_quality_prediction
from src.visualizer import run_visualization


def main():
    setup_logging(level=logging.INFO)
    from src.config import HISTORY_DATABASE_PATH
    repository = HistoryRepository(HISTORY_DATABASE_PATH)
    repository.initialize()
    run_id = repository.start_run(
        random_seed=DATA_CONFIG["random_seed"], source_name="synthetic_manufacturing_data"
    )
    print("=" * 60)
    print("Smart Manufacturing Simulation Portfolio")
    print("소르테크 지원용 포트폴리오 프로젝트")
    print("=" * 60)

    try:
        print("\n[1/7] 제조 공정 데이터 생성...")
        df = generate_manufacturing_data(DATA_CONFIG["num_records"])
        save_data(df)
        observation_ids = repository.insert_observations(run_id, df.to_dict("records"))
        print(f"\n  총 레코드: {len(df)}")
        print("\n[2/7] 데이터 검증...")
        validation = validate_data(df)
        print(f"  검증 결과: {'통과' if validation['is_valid'] else '실패'}")
        print("\n[3/7] 데이터 분석...")
        analysis = analyze_production_data(df)
        print(f"  불량률: {analysis['defect_rate']:.2f}%")
        print("\n[4/7] 학습 입력 계약 확인...")
        print("  시간순 분할을 보존하기 위해 원본 센서 특성 5개를 QualityPredictor에 전달합니다.")
        print("\n[5/7] 품질 예측 모델 학습...")
        # Keep timestamp available to the predictor so it can perform a
        # leakage-safe chronological train/validation/test split.
        _, predictor, X_test = run_quality_prediction(df=df, return_artifacts=True)
        with open(LATEST_MODEL_META_PATH, encoding="utf-8") as meta_file:
            metadata = json.load(meta_file)
        from src.model_manager import ModelManager
        model_version_id = repository.register_model(run_id, metadata, ModelManager().compute_checksum(LATEST_MODEL_PATH))
        observation_id_by_source_index = dict(zip(df.index, observation_ids))
        test_observation_ids = [observation_id_by_source_index[index] for index in X_test.index]
        predicted_is_defective, probabilities = predictor.predict(X_test)
        repository.record_predictions(
            model_version_id,
            test_observation_ids,
            predicted_is_defective.astype(int).tolist(),
            probabilities[:, 1].astype(float).tolist(),
            threshold=float(predictor.threshold),
        )
        latest_metrics = repository.latest_model_metrics()
        evidence_path = BASE_DIR / "docs" / "latest_model_metrics.md"
        metrics_lines = [
            "# 최신 모델 성능 증빙",
            "",
            "`python main.py`가 SQLite의 최신 test 지표를 조회하여 자동 생성한 문서입니다.",
            "합성 데이터의 시간순 held-out test split 결과이며 실제 생산 성능을 뜻하지 않습니다.",
            "",
            f"- 모델: `{latest_metrics['model_name']}` / 버전: `{latest_metrics['version']}`",
            f"- 학습 시각 (UTC): `{latest_metrics['trained_at']}`",
            f"- 예측 threshold: `{latest_metrics['threshold']:.4f}`",
            "- test 지표:",
        ]
        metrics_lines.extend(f"  - `{name}`: `{value:.4f}`" for name, value in latest_metrics["metrics"].items())
        evidence_path.write_text("\n".join(metrics_lines) + "\n", encoding="utf-8")
        print("\n[6/7] 예측 정비 시스템...")
        run_predictive_maintenance()
        print("\n[7/7] 데이터 드리프트 감지...")
        ref_df = pd.read_csv(DATA_DIR / "manufacturing_data.csv")
        np.random.seed(42)
        live_df = ref_df.copy()
        live_df["temperature"] += np.random.normal(2, 0.5, len(live_df))
        live_df["vibration"] *= np.random.uniform(1.2, 1.4, len(live_df))
        report = DriftDetector(ks_alpha=0.05).detect(ref_df, live_df)
        repository.record_drift(
            run_id, report,
            reference_source="synthetic_manufacturing_data",
            live_source="synthetic_shift_temperature_plus_2_vibration_scale",
        )
        print(f"  드리프트 감지 결과: {'[DRIFT]' if report['drift_detected'] else '[OK]'}")
        run_visualization()
        repository.finish_run(run_id, record_count=len(df))
        print("\n대시보드 실행 방법: python dashboard/app.py")
    except Exception as exc:
        repository.finish_run(run_id, error_summary=str(exc)[:1000])
        raise


if __name__ == "__main__":
    main()
