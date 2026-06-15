from __future__ import annotations

import logging
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, send_from_directory

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import DATA_CONFIG, DASHBOARD_CONFIG, DATA_FILE, EQUIPMENT_FILE, VISUALIZATIONS_DIR
from src.logging_config import setup_logging
from src.data_generator import generate_manufacturing_data
from src.anomaly_detector import detect_anomalies
from src.drift_detector import DriftDetector
from src.predictive_maintenance import PredictiveMaintenance

app = Flask(__name__)


class DataCache:
    def __init__(self, ttl=60):
        self.ttl = ttl
        self._data = None
        self._timestamp = 0
        self._anomaly_result = None
        self._anomaly_timestamp = 0

    def get(self):
        now = time.time()
        if self._data is None or (now - self._timestamp) > self.ttl:
            self._data = self._load()
            self._timestamp = now
        return self._data

    def get_anomaly(self):
        now = time.time()
        if self._anomaly_result is None or (now - self._anomaly_timestamp) > self.ttl:
            df = self.get()
            self._anomaly_result = detect_anomalies(df)
            self._anomaly_timestamp = now
        return self._anomaly_result

    def _load(self):
        if os.path.exists(DATA_FILE):
            return pd.read_csv(DATA_FILE)
        return generate_manufacturing_data(5000)

    def invalidate(self):
        self._data = None
        self._timestamp = 0
        self._anomaly_result = None
        self._anomaly_timestamp = 0


cache = DataCache(ttl=60)


def load_equipment():
    if os.path.exists(EQUIPMENT_FILE):
        with open(EQUIPMENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/v1/summary")
def api_summary():
    try:
        df = cache.get()
        summary = {
            "total_records": len(df),
            "defect_rate": float(df["is_defective"].mean() * 100),
            "avg_temperature": float(df["temperature"].mean()),
            "avg_pressure": float(df["pressure"].mean()),
            "avg_vibration": float(df["vibration"].mean()),
            "avg_humidity": float(df["humidity"].mean()),
            "avg_cycle_time": float(df["cycle_time"].mean()),
        }
        return jsonify({"status": "success", "data": summary})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/equipment")
def api_equipment():
    try:
        pm = PredictiveMaintenance()
        equipment_list = load_equipment()

        equipment_status = []
        for eq in equipment_list:
            health = pm.analyze_equipment_health(eq["id"], eq["sensors"])
            equipment_status.append(health)

        return jsonify({"status": "success", "data": equipment_status})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/lines")
def api_lines():
    try:
        df = cache.get()
        line_defect = df.groupby("production_line")["is_defective"].mean() * 100
        line_data = [
            {"line": line, "defect_rate": float(rate), "count": int(df[df["production_line"] == line].shape[0])}
            for line, rate in line_defect.items()
        ]
        return jsonify({"status": "success", "data": line_data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/trends")
def api_trends():
    try:
        df = cache.get()
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        hourly_defect = df.groupby(df["timestamp"].dt.hour)["is_defective"].mean() * 100

        trends = {
            "hours": hourly_defect.index.tolist(),
            "defect_rates": hourly_defect.values.tolist(),
        }
        return jsonify({"status": "success", "data": trends})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/anomalies")
def api_anomalies():
    try:
        result = cache.get_anomaly()
        return jsonify({
            "status": "success",
            "data": {
                "summary": result["summary"],
                "top_anomalies": result["top_anomalies"].to_dict("records"),
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/correlation")
def api_correlation():
    try:
        df = cache.get()
        numeric_cols = ["temperature", "pressure", "vibration", "humidity", "cycle_time", "is_defective"]
        corr = df[numeric_cols].corr().round(3)
        return jsonify({
            "status": "success",
            "data": {
                "columns": numeric_cols,
                "matrix": corr.values.tolist(),
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/scatter")
def api_scatter():
    try:
        df = cache.get()
        normal = df[df["is_defective"] == 0][["temperature", "vibration"]].head(200)
        anomaly = df[df["is_defective"] == 1][["temperature", "vibration"]].head(200)

        return jsonify({
            "status": "success",
            "data": {
                "normal": [{"x": float(r.temperature), "y": float(r.vibration)} for _, r in normal.iterrows()],
                "anomaly": [{"x": float(r.temperature), "y": float(r.vibration)} for _, r in anomaly.iterrows()],
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/rul")
def api_rul():
    try:
        pm = PredictiveMaintenance()
        report = pm.generate_rul_report()
        return jsonify({"status": "success", "data": report["equipment"]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/visualizations")
def api_visualizations():
    try:
        files = sorted([f.name for f in VISUALIZATIONS_DIR.glob("*.png")]) if VISUALIZATIONS_DIR.exists() else []
        return jsonify({"status": "success", "data": files})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/visualizations/<filename>")
def serve_visualization(filename):
    try:
        return send_from_directory(VISUALIZATIONS_DIR, filename)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 404


@app.route("/api/v1/drift")
def api_drift():
    try:
        df = cache.get()
        np.random.seed(99)
        live_df = df.copy()
        live_df["temperature"] = live_df["temperature"] + np.random.normal(1.5, 0.5, len(live_df))
        live_df["vibration"] = live_df["vibration"] * np.random.uniform(1.1, 1.3, len(live_df))

        detector = DriftDetector()
        report = detector.detect(df, live_df)
        return jsonify({"status": "success", "data": report})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    import sys as _sys
    setup_logging(level=logging.INFO)

    port = DASHBOARD_CONFIG["port"]
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    if not os.path.exists(DATA_FILE):
        print("데이터 생성 중...")
        df = generate_manufacturing_data(DATA_CONFIG["num_records"])
        os.makedirs("data", exist_ok=True)
        df.to_csv(DATA_FILE, index=False)
        print(f"데이터 저장 완료: {DATA_FILE}")

    host = DASHBOARD_CONFIG["host"]
    print(f"\n대시보드 실행: http://localhost:{port}")
    app.run(host=host, debug=False, port=port)
