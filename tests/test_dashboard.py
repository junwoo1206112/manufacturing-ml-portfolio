import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.app import app


class TestDashboardAPI:
    def setup_method(self):
        self.client = app.test_client()

    def test_index_page(self):
        resp = self.client.get("/")
        assert resp.status_code == 200

    def test_api_summary(self):
        resp = self.client.get("/api/v1/summary")
        data = resp.get_json()
        assert data["status"] == "success"
        assert "total_records" in data["data"]

    def test_api_equipment(self):
        resp = self.client.get("/api/v1/equipment")
        data = resp.get_json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)

    def test_api_lines(self):
        resp = self.client.get("/api/v1/lines")
        data = resp.get_json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)

    def test_api_trends(self):
        resp = self.client.get("/api/v1/trends")
        data = resp.get_json()
        assert data["status"] == "success"
        assert "hours" in data["data"]

    def test_api_correlation(self):
        resp = self.client.get("/api/v1/correlation")
        data = resp.get_json()
        assert data["status"] == "success"
        assert "columns" in data["data"]
        assert "matrix" in data["data"]

    def test_api_anomalies(self):
        resp = self.client.get("/api/v1/anomalies")
        data = resp.get_json()
        assert data["status"] == "success"
        assert "summary" in data["data"]

    def test_api_scatter(self):
        resp = self.client.get("/api/v1/scatter")
        data = resp.get_json()
        assert data["status"] == "success"
        assert "normal" in data["data"]
        assert "anomaly" in data["data"]

    def test_api_rul(self):
        resp = self.client.get("/api/v1/rul")
        data = resp.get_json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        if data["data"]:
            assert "remaining_hours" in data["data"][0]
            assert "recommended_maintenance_date" in data["data"][0]

    def test_api_visualizations(self):
        resp = self.client.get("/api/v1/visualizations")
        data = resp.get_json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)

    def test_api_drift(self):
        resp = self.client.get("/api/v1/drift")
        data = resp.get_json()
        assert data["status"] == "success"
        assert "drift_detected" in data["data"]
        assert "drifted_features" in data["data"]
        assert len(data["data"]["drifted_features"]) >= 6

    def test_serve_visualization(self):
        resp = self.client.get("/visualizations/nonexistent.png")
        assert resp.status_code in (404, 200)
