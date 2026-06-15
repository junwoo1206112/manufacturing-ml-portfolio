from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler

from src.logging_config import get_logger

logger = get_logger(__name__)


class DataPipeline:
    def __init__(self) -> None:
        self.scalers: Dict[str, Any] = {}
        self.encoders: Dict[str, LabelEncoder] = {}
        self.feature_columns: List[str] = []
        self.target_column: str = "is_defective"

    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isnull().any():
                df[col] = df[col].fillna(df[col].median())

        categorical_cols = df.select_dtypes(include=["object", "string"]).columns
        for col in categorical_cols:
            if df[col].isnull().any():
                mode_result = df[col].mode()
                if not mode_result.empty:
                    df[col] = df[col].fillna(mode_result.iloc[0])

        return df

    def encode_categorical(
        self, df: pd.DataFrame, columns: List[str]
    ) -> pd.DataFrame:
        df = df.copy()

        for col in columns:
            if col in df.columns:
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col].astype(str))
                self.encoders[col] = le

        return df

    def scale_features(
        self,
        df: pd.DataFrame,
        columns: List[str],
        method: str = "standard",
    ) -> pd.DataFrame:
        df = df.copy()

        for col in columns:
            if col in df.columns:
                if method == "standard":
                    scaler = StandardScaler()
                elif method == "minmax":
                    scaler = MinMaxScaler()
                else:
                    raise ValueError(f"Unknown scaling method: {method}")

                df[col] = scaler.fit_transform(df[[col]])
                self.scalers[col] = scaler

        return df

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        if "timestamp" in df.columns:
            df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour
            df["day_of_week"] = pd.to_datetime(df["timestamp"]).dt.dayofweek
            df["is_night"] = df["hour"].apply(lambda x: 1 if x < 6 or x > 22 else 0)

        if "temperature" in df.columns and "pressure" in df.columns:
            df["temp_pressure_ratio"] = df["temperature"] / (df["pressure"] + 1e-6)

        if "vibration" in df.columns and "temperature" in df.columns:
            df["vib_temp_interaction"] = df["vibration"] * df["temperature"]

        if "temperature" in df.columns:
            df["temp_squared"] = df["temperature"] ** 2

        if "vibration" in df.columns:
            df["vibration_squared"] = df["vibration"] ** 2

        return df

    def remove_outliers(
        self,
        df: pd.DataFrame,
        columns: List[str],
        method: str = "iqr",
        threshold: float = 1.5,
    ) -> pd.DataFrame:
        df = df.copy()

        if method == "iqr":
            for col in columns:
                if col in df.columns:
                    Q1 = df[col].quantile(0.25)
                    Q3 = df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    lower = Q1 - threshold * IQR
                    upper = Q3 + threshold * IQR
                    df = df[(df[col] >= lower) & (df[col] <= upper)]

        elif method == "zscore":
            for col in columns:
                if col in df.columns:
                    z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                    df = df[z_scores <= threshold]

        return df

    def split_data(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        test_size: float = 0.2,
        val_size: float = 0.15,
        random_state: int = 42,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        X = df[feature_cols].copy()
        y = df[self.target_column].copy()

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        X_train, X_val, y_train, y_val = train_test_split(
            X_train,
            y_train,
            test_size=val_size / (1 - test_size),
            random_state=random_state,
            stratify=y_train,
        )

        return X_train, X_val, X_test, y_train, y_val, y_test

    def prepare(
        self,
        df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
        scale: bool = True,
        encode: bool = True,
        create_features: bool = True,
    ) -> Dict[str, Any]:
        df = self.handle_missing_values(df)

        if create_features:
            df = self.create_features(df)

        categorical_cols = ["production_line", "operator_name"]
        if encode:
            df = self.encode_categorical(
                df, [c for c in categorical_cols if c in df.columns]
            )

        if feature_cols is None:
            exclude_cols = [
                "timestamp",
                self.target_column,
                "defect_rate",
                "defect_probability",
            ]
            feature_cols = [c for c in df.columns if c not in exclude_cols]

        self.feature_columns = feature_cols

        X_train, X_val, X_test, y_train, y_val, y_test = self.split_data(
            df, feature_cols
        )

        if scale:
            numeric_features = [
                c for c in feature_cols if X_train[c].dtype in ["float64", "int64"]
            ]
            for col in numeric_features:
                scaler = StandardScaler()
                X_train[col] = scaler.fit_transform(X_train[[col]])
                X_val[col] = scaler.transform(X_val[[col]])
                X_test[col] = scaler.transform(X_test[[col]])
                self.scalers[col] = scaler

        full_df = df[feature_cols + [self.target_column]].copy()

        logger.info(
            "Prepared data: train=%d, val=%d, test=%d, features=%d",
            len(X_train),
            len(X_val),
            len(X_test),
            len(feature_cols),
        )

        return {
            "X_train": X_train,
            "X_val": X_val,
            "X_test": X_test,
            "y_train": y_train,
            "y_val": y_val,
            "y_test": y_test,
            "feature_columns": feature_cols,
            "full_df": full_df,
        }


def prepare_training_data(df: pd.DataFrame) -> Dict[str, Any]:
    pipeline = DataPipeline()
    return pipeline.prepare(df)


if __name__ == "__main__":
    from src.data_generator import generate_manufacturing_data

    print("=== 데이터 전처리 파이프라인 ===")
    df = generate_manufacturing_data(1000)
    print(f"원본 데이터: {len(df)}건")

    result = prepare_training_data(df)

    print(f"\n전처리 결과:")
    print(f"  학습 데이터: {len(result['X_train'])}건")
    print(f"  검증 데이터: {len(result['X_val'])}건")
    print(f"  테스트 데이터: {len(result['X_test'])}건")
    print(f"  피처 수: {len(result['feature_columns'])}")
    print(f"  피처 목록: {result['feature_columns']}")
