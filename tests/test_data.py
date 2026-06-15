import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_generator import ManufacturingDataGenerator, generate_manufacturing_data
from src.data_validator import DataValidator, validate_data
from src.data_pipeline import DataPipeline, prepare_training_data


class TestDataGenerator:
    def test_generate_returns_dataframe(self):
        df = generate_manufacturing_data(100)
        assert isinstance(df, pd.DataFrame)

    def test_generate_correct_row_count(self):
        df = generate_manufacturing_data(500)
        assert len(df) == 500

    def test_generate_has_required_columns(self):
        df = generate_manufacturing_data(100)
        required = ["timestamp", "production_line", "temperature", "pressure",
                    "vibration", "humidity", "cycle_time", "is_defective",
                    "defect_probability", "defect_rate"]
        for col in required:
            assert col in df.columns

    def test_generate_defect_probability_is_bounded(self):
        df = generate_manufacturing_data(500)
        assert df["defect_probability"].min() >= 0.0
        assert df["defect_probability"].max() <= 1.0

    def test_generate_sensor_signal_strength(self):
        df = generate_manufacturing_data(2000)
        numeric_cols = ["temperature", "pressure", "vibration", "humidity"]
        correlations = df[numeric_cols + ["is_defective"]].corr()["is_defective"].abs()
        assert correlations[numeric_cols].max() > 0.30

    def test_generate_defect_values_are_binary(self):
        df = generate_manufacturing_data(100)
        assert df["is_defective"].isin([0, 1]).all()

    def test_generate_production_lines_valid(self):
        df = generate_manufacturing_data(100)
        valid_lines = {"Line_A", "Line_B", "Line_C"}
        assert set(df["production_line"].unique()).issubset(valid_lines)


class TestDataValidator:
    def setup_method(self):
        self.df = generate_manufacturing_data(100)

    def test_validate_valid_data(self):
        result = validate_data(self.df)
        assert result["is_valid"] is True

    def test_validate_completeness(self):
        validator = DataValidator()
        assert validator.validate_completeness(self.df) is True

    def test_validate_ranges(self):
        validator = DataValidator()
        assert validator.validate_ranges(self.df) is True

    def test_validate_consistency(self):
        validator = DataValidator()
        assert validator.validate_consistency(self.df) is True

    def test_detect_outliers_iqr(self):
        validator = DataValidator()
        outliers = validator.detect_outliers_iqr(
            self.df, ["temperature", "pressure"]
        )
        assert isinstance(outliers, dict)


class TestDataPipeline:
    def setup_method(self):
        self.df = generate_manufacturing_data(200)

    def test_handle_missing_values(self):
        pipeline = DataPipeline()
        df = self.df.copy()
        df.loc[0, "temperature"] = np.nan
        result = pipeline.handle_missing_values(df)
        assert result["temperature"].isnull().sum() == 0

    def test_prepare_creates_splits(self):
        result = prepare_training_data(self.df)
        assert "X_train" in result
        assert "X_val" in result
        assert "X_test" in result
        assert len(result["X_train"]) > 0
        assert len(result["X_val"]) > 0
        assert len(result["X_test"]) > 0

    def test_prepare_feature_columns(self):
        result = prepare_training_data(self.df)
        assert len(result["feature_columns"]) > 0

    def test_scale_features_minmax(self):
        pipeline = DataPipeline()
        df = self.df.copy()
        numeric_cols = ["temperature", "pressure"]
        result = pipeline.scale_features(df, numeric_cols, method="minmax")
        for col in numeric_cols:
            assert result[col].min() >= 0
            assert result[col].max() <= 1

    def test_handle_missing_values_all_null_categorical(self):
        pipeline = DataPipeline()
        df = self.df.copy()
        df["production_line"] = np.nan
        result = pipeline.handle_missing_values(df)
        assert "production_line" in result.columns
