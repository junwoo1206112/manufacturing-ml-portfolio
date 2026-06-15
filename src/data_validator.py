from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.logging_config import get_logger

logger = get_logger(__name__)


class DataValidator:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_completeness(self, df: pd.DataFrame) -> bool:
        missing = df.isnull().sum()
        missing_pct = (missing / len(df)) * 100

        for col in df.columns:
            if missing_pct[col] > 0:
                self.warnings.append(f"{col}: {missing_pct[col]:.2f}% 결측값")

        return bool(missing_pct.max() < 5)

    def validate_ranges(self, df: pd.DataFrame) -> bool:
        valid = True

        if "temperature" in df.columns:
            temp_outliers = df[(df["temperature"] < -10) | (df["temperature"] > 60)]
            if len(temp_outliers) > 0:
                self.errors.append(f"온도 범위 초과: {len(temp_outliers)}건")
                valid = False

        if "pressure" in df.columns:
            pres_outliers = df[(df["pressure"] < 50) | (df["pressure"] > 150)]
            if len(pres_outliers) > 0:
                self.errors.append(f"압력 범위 초과: {len(pres_outliers)}건")
                valid = False

        if "vibration" in df.columns:
            vib_outliers = df[(df["vibration"] < 0) | (df["vibration"] > 2.0)]
            if len(vib_outliers) > 0:
                self.errors.append(f"진동 범위 초과: {len(vib_outliers)}건")
                valid = False

        if "humidity" in df.columns:
            hum_outliers = df[(df["humidity"] < 0) | (df["humidity"] > 100)]
            if len(hum_outliers) > 0:
                self.errors.append(f"습도 범위 초과: {len(hum_outliers)}건")
                valid = False

        if "is_defective" in df.columns:
            if not df["is_defective"].isin([0, 1]).all():
                self.errors.append("is_defective에 유효하지 않은 값 존재")
                valid = False

        return bool(valid)

    def validate_consistency(self, df: pd.DataFrame) -> bool:
        valid = True

        if "timestamp" in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                self.errors.append("timestamp가 datetime 타입이 아님")
                valid = False

        if "production_line" in df.columns:
            valid_lines = ["Line_A", "Line_B", "Line_C"]
            invalid_lines = set(df["production_line"].unique()) - set(valid_lines)
            if invalid_lines:
                self.errors.append(f"잘못된 라인: {invalid_lines}")
                valid = False

        return bool(valid)

    def detect_outliers_iqr(
        self, df: pd.DataFrame, columns: List[str], threshold: float = 1.5
    ) -> Dict[str, int]:
        outlier_counts: Dict[str, int] = {}

        for col in columns:
            if col in df.columns:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower = Q1 - threshold * IQR
                upper = Q3 + threshold * IQR

                outliers = df[(df[col] < lower) | (df[col] > upper)]
                outlier_counts[col] = len(outliers)

        return outlier_counts

    def detect_outliers_zscore(
        self, df: pd.DataFrame, columns: List[str], threshold: float = 3.0
    ) -> Dict[str, int]:
        outlier_counts: Dict[str, int] = {}

        for col in columns:
            if col in df.columns:
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                outliers = df[z_scores > threshold]
                outlier_counts[col] = len(outliers)

        return outlier_counts

    def validate(self, df: pd.DataFrame) -> Dict[str, Any]:
        self.errors = []
        self.warnings = []

        completeness = self.validate_completeness(df)
        ranges = self.validate_ranges(df)
        consistency = self.validate_consistency(df)

        numeric_cols = [
            "temperature",
            "pressure",
            "vibration",
            "humidity",
            "cycle_time",
        ]
        existing_cols = [c for c in numeric_cols if c in df.columns]
        iqr_outliers = self.detect_outliers_iqr(df, existing_cols)
        zscore_outliers = self.detect_outliers_zscore(df, existing_cols)

        is_valid = completeness and ranges and consistency
        if not is_valid:
            logger.warning("Data validation failed with %d errors", len(self.errors))
        else:
            logger.info("Data validation passed for %d records", len(df))

        return {
            "is_valid": is_valid,
            "completeness": completeness,
            "ranges": ranges,
            "consistency": consistency,
            "errors": self.errors,
            "warnings": self.warnings,
            "iqr_outliers": iqr_outliers,
            "zscore_outliers": zscore_outliers,
            "total_records": len(df),
        }


def validate_data(df: pd.DataFrame) -> Dict[str, Any]:
    validator = DataValidator()
    return validator.validate(df)


if __name__ == "__main__":
    from src.data_generator import generate_manufacturing_data

    print("=== 데이터 검증 ===")
    df = generate_manufacturing_data(100)
    result = validate_data(df)

    print(f"\n검증 결과: {'통과' if result['is_valid'] else '실패'}")
    print(f"총 레코드: {result['total_records']}")

    if result["errors"]:
        print("\n[에러]")
        for err in result["errors"]:
            print(f"  - {err}")

    if result["warnings"]:
        print("\n[경고]")
        for warn in result["warnings"]:
            print(f"  - {warn}")

    print("\nIQR 이상치:")
    for col, count in result["iqr_outliers"].items():
        print(f"  {col}: {count}건")
