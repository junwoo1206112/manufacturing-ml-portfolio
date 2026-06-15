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
import os
import sys

import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import DATA_CONFIG, DATA_DIR
from src.data_analyzer import analyze_production_data, save_data
from src.data_generator import generate_manufacturing_data
from src.data_pipeline import prepare_training_data
from src.data_validator import validate_data
from src.drift_detector import DriftDetector
from src.logging_config import setup_logging
from src.predictive_maintenance import run_predictive_maintenance
from src.quality_predictor import run_quality_prediction
from src.visualizer import run_visualization


def main():
    setup_logging(level=logging.INFO)
    print("=" * 60)
    print("Smart Manufacturing Simulation Portfolio")
    print("소르테크 지원용 포트폴리오 프로젝트")
    print("=" * 60)

    print("\n[1/6] 제조 공정 데이터 생성...")
    df = generate_manufacturing_data(DATA_CONFIG["num_records"])
    save_data(df)

    print(f"\n  총 레코드: {len(df)}")
    print(f"  라인별 분포:")
    for line, count in df["production_line"].value_counts().items():
        print(f"    {line}: {count}건")

    print("\n[2/6] 데이터 검증...")
    validation = validate_data(df)
    print(f"  검증 결과: {'통과' if validation['is_valid'] else '실패'}")
    if validation["errors"]:
        print(f"  에러: {validation['errors']}")
    if validation["warnings"]:
        print(f"  경고: {validation['warnings'][:3]}...")

    print("\n[3/6] 데이터 분석...")
    analysis = analyze_production_data(df)
    print(f"  불량률: {analysis['defect_rate']:.2f}%")
    print(f"  평균 온도: {analysis['avg_temperature']:.2f}°C")

    print("\n[4/6] 데이터 전처리...")
    train_data = prepare_training_data(df)
    print(f"  학습: {len(train_data['X_train'])}건")
    print(f"  검증: {len(train_data['X_val'])}건")
    print(f"  테스트: {len(train_data['X_test'])}건")

    print("\n[5/6] 품질 예측 모델 학습...")
    run_quality_prediction(df=train_data["full_df"])

    print("\n[6/7] 예측 정비 시스템...")
    run_predictive_maintenance()

    print("\n[7/7] 데이터 드리프트 감지...")
    print("  참조 데이터 로드 중...")
    ref_df = pd.read_csv(DATA_DIR / "manufacturing_data.csv")

    np.random.seed(42)
    live_df = ref_df.copy()
    live_df["temperature"] = live_df["temperature"] + np.random.normal(2, 0.5, len(live_df))
    live_df["vibration"] = live_df["vibration"] * np.random.uniform(1.2, 1.4, len(live_df))
    print(f"  드리프트 적용: temperature +2°C shift, vibration ×1.3 scale")

    detector = DriftDetector(ks_alpha=0.05)
    report = detector.detect(ref_df, live_df)

    drift_label = "[DRIFT]" if report['drift_detected'] else "[OK]"
    print(f"\n  드리프트 감지 결과: {drift_label}")
    for entry in report["drifted_features"]:
        flags = []
        if entry.get("ks_drifted"):
            flags.append(f"KS p={entry['ks_p_value']:.4f}")
        if entry.get("psi_drifted"):
            flags.append(f"PSI={entry['psi']:.4f}")
        marker = "[!]" if entry["drifted"] else "[.]"
        print(f"  {marker} {entry['feature']}: {', '.join(flags) if flags else '정상'}")

    print("\n" + "=" * 60)
    print("모든 프로젝트 실행 완료!")
    print("=" * 60)

    print("\n시각화 생성...")
    run_visualization()

    print("\n대시보드 실행 방법:")
    print("  python dashboard/app.py")
    print("  브라우저에서 http://localhost:5000 접속")


if __name__ == "__main__":
    main()
