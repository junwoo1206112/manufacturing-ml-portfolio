import os
import sys
import tempfile

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.visualizer import ManufacturingVisualizer


class TestVisualizer:
    def setup_method(self):
        data = {
            "timestamp": pd.date_range("2024-01-01", periods=50, freq="h"),
            "production_line": ["Line_A"] * 50,
            "temperature": np.random.normal(25, 5, 50),
            "pressure": np.random.normal(100, 10, 50),
            "vibration": np.random.normal(0.5, 0.2, 50),
            "humidity": np.random.normal(60, 10, 50),
            "cycle_time": np.random.normal(30, 5, 50),
            "defect_probability": np.random.uniform(0, 0.3, 50),
            "is_defective": np.random.randint(0, 2, 50),
        }
        self.df = pd.DataFrame(data)

    def test_korean_labels_do_not_raise(self):
        viz = ManufacturingVisualizer()
        with tempfile.TemporaryDirectory() as tmpdir:
            viz.plot_defect_analysis(self.df, save_path=tmpdir + "/")
            assert os.path.exists(os.path.join(tmpdir, "defect_analysis.png"))
