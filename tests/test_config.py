import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.config as config


class TestConfig:
    def test_paths_are_path_objects(self):
        assert config.BASE_DIR.exists()
        assert config.DATA_DIR.exists()
        assert config.MODELS_DIR.exists()
        assert config.VISUALIZATIONS_DIR.exists()

    def test_data_config_loaded(self):
        assert "num_records" in config.DATA_CONFIG
        assert "random_seed" in config.DATA_CONFIG
        assert isinstance(config.DATA_CONFIG["num_records"], int)

    def test_production_lines_have_tuples(self):
        for line_id, line in config.PRODUCTION_LINES.items():
            assert "name" in line
            assert isinstance(line["temp_range"], tuple)
            assert isinstance(line["pressure_range"], tuple)

    def test_thresholds_loaded(self):
        assert "vibration" in config.THRESHOLDS
        assert "warning" in config.THRESHOLDS["vibration"]
        assert "critical" in config.THRESHOLDS["vibration"]

    def test_ml_config_has_models(self):
        assert "models" in config.ML_CONFIG
        assert "random_forest" in config.ML_CONFIG["models"]

    def test_dashboard_config_loaded(self):
        assert "host" in config.DASHBOARD_CONFIG
        assert "port" in config.DASHBOARD_CONFIG

    def test_latest_model_paths_defined(self):
        assert config.LATEST_MODEL_PATH.name == "quality_predictor_latest.joblib"
        assert config.LATEST_MODEL_META_PATH.name == "quality_predictor_latest_meta.json"
