from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from src.config import DATA_DIR
from src.logging_config import get_logger

logger = get_logger(__name__)


def analyze_production_data(df: pd.DataFrame) -> Dict[str, Any]:
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    analysis: Dict[str, Any] = {
        "total_records": len(df),
        "defect_rate": df["is_defective"].mean() * 100,
        "avg_temperature": df["temperature"].mean(),
        "avg_pressure": df["pressure"].mean(),
        "avg_vibration": df["vibration"].mean(),
        "avg_cycle_time": df["cycle_time"].mean(),
        "production_by_line": df.groupby("production_line")["is_defective"].mean()
        * 100,
        "hourly_defect_trend": df.groupby(df["timestamp"].dt.hour)["is_defective"].mean()
        * 100,
    }
    return analysis


def save_data(df: pd.DataFrame, filename: str = "manufacturing_data.csv") -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DATA_DIR / filename
    df.to_csv(filepath, index=False)
    logger.info("Data saved: %s", filepath)
    return str(filepath)


if __name__ == "__main__":
    from src.data_generator import generate_manufacturing_data

    print("=== 제조 공정 데이터 분석 ===")
    df = generate_manufacturing_data(1000)

    print(f"\n데이터 기본 정보:")
    print(f"- 총 레코드 수: {len(df)}")
    print(f"- 불량률: {df['is_defective'].mean()*100:.2f}%")
    print(f"- 평균 온도: {df['temperature'].mean():.2f}°C")

    print("\n=== 데이터 분석 ===")
    analysis = analyze_production_data(df)
    print(f"\n라인별 불량률:")
    for line, rate in analysis["production_by_line"].items():
        print(f"  {line}: {rate:.2f}%")

    save_data(df)
    print("\n데이터 분석 완료!")
