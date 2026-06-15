from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from src.config import EQUIPMENT_FILE, THRESHOLDS
from src.logging_config import get_logger

logger = get_logger(__name__)


class PredictiveMaintenance:
    DEFAULT_INTERVAL = 1000.0

    def __init__(
        self,
        equipment_file: Optional[Union[str, Path]] = None,
        thresholds: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> None:
        self.equipment_file = Path(equipment_file) if equipment_file else EQUIPMENT_FILE
        self.maintenance_thresholds = thresholds if thresholds is not None else THRESHOLDS
        self.equipment_data: List[Dict[str, Any]] = self._load_equipment()

    def _load_equipment(self) -> List[Dict[str, Any]]:
        if not self.equipment_file.exists():
            logger.warning("Equipment file not found: %s", self.equipment_file)
            return []
        try:
            with open(self.equipment_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.exception("Failed to load equipment file: %s", self.equipment_file)
            return []

    def analyze_equipment_health(
        self, equipment_id: str, sensor_data: Dict[str, float]
    ) -> Dict[str, Any]:
        health_score = 100
        alerts: List[str] = []

        for sensor, value in sensor_data.items():
            if sensor in self.maintenance_thresholds:
                thresholds = self.maintenance_thresholds[sensor]

                if value >= thresholds["critical"]:
                    health_score -= 30
                    alerts.append(f"[CRITICAL] {sensor}: {value}")
                elif value >= thresholds["warning"]:
                    health_score -= 15
                    alerts.append(f"[WARNING] {sensor}: {value}")

        health_score = max(0, health_score)

        return {
            "equipment_id": equipment_id,
            "health_score": health_score,
            "status": self._get_status(health_score),
            "alerts": alerts,
            "timestamp": datetime.now().isoformat(),
        }

    def _get_status(self, health_score: int) -> str:
        if health_score >= 80:
            return "양호"
        elif health_score >= 60:
            return "주의"
        elif health_score >= 40:
            return "경고"
        else:
            return "위험"

    def _fit_lognormal_rul(
        self, failure_history: List[Dict[str, Any]], usage_hours: float
    ) -> Dict[str, Any]:
        if not failure_history:
            return {
                "remaining_hours": max(0.0, self.DEFAULT_INTERVAL - usage_hours),
                "reliability_score": max(0.0, 1.0 - usage_hours / self.DEFAULT_INTERVAL)
                * 100,
                "confidence": 0.5,
                "model": "default",
            }

        intervals = np.array([f["interval"] for f in failure_history], dtype=float)
        if len(intervals) < 2:
            mean_interval = (
                float(intervals[0]) if len(intervals) == 1 else self.DEFAULT_INTERVAL
            )
            return {
                "remaining_hours": max(0.0, mean_interval - usage_hours),
                "reliability_score": max(0.0, 1.0 - usage_hours / mean_interval)
                * 100,
                "confidence": 0.65,
                "model": "mean_interval",
            }

        log_intervals = np.log(intervals)
        mu = float(np.mean(log_intervals))
        sigma = float(np.std(log_intervals, ddof=1))
        sigma = max(sigma, 1e-6)

        z = (np.log(max(usage_hours, 1e-6)) - mu) / sigma
        cdf = 0.5 * (
            1.0 + np.sign(z) * np.sqrt(1.0 - np.exp(-2.0 / np.pi * z * z))
        )
        cdf = np.clip(cdf, 0.0, 1.0)
        reliability = 1.0 - cdf

        phi_arg = mu + sigma ** 2 - np.log(max(usage_hours, 1e-6))
        phi_cdf = 0.5 * (
            1.0
            + np.sign(phi_arg / sigma)
            * np.sqrt(1.0 - np.exp(-2.0 / np.pi * (phi_arg / sigma) ** 2))
        )
        phi_cdf = np.clip(phi_cdf, 0.0, 1.0)
        expected_total = (
            np.exp(mu + sigma ** 2 / 2.0) * phi_cdf / max(reliability, 1e-6)
        )
        remaining = max(0.0, expected_total - usage_hours)

        confidence = min(0.95, 0.7 + 0.05 * len(intervals))

        return {
            "remaining_hours": remaining,
            "reliability_score": reliability * 100,
            "confidence": confidence,
            "model": "lognormal_reliability",
        }

    def predict_maintenance_date(
        self,
        equipment_id: str,
        usage_hours: float,
        failure_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        rul = self._fit_lognormal_rul(failure_history, usage_hours)
        maintenance_date = datetime.now() + timedelta(
            hours=rul["remaining_hours"] * 0.8
        )

        return {
            "equipment_id": equipment_id,
            "usage_hours": usage_hours,
            "remaining_hours": rul["remaining_hours"],
            "recommended_maintenance_date": maintenance_date.strftime("%Y-%m-%d"),
            "reliability_score": rul["reliability_score"],
            "confidence": rul["confidence"],
            "model": rul["model"],
        }

    def generate_maintenance_report(
        self, equipment_list: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        if equipment_list is None:
            equipment_list = self.equipment_data

        report = {
            "generated_at": datetime.now().isoformat(),
            "total_equipment": len(equipment_list),
            "status_summary": {
                "양호": 0,
                "주의": 0,
                "경고": 0,
                "위험": 0,
            },
            "equipment_details": [],
        }

        for equipment in equipment_list:
            health = self.analyze_equipment_health(
                equipment["id"],
                equipment["sensors"],
            )
            report["status_summary"][health["status"]] += 1
            report["equipment_details"].append(health)

        logger.info("Maintenance report generated for %d equipment", len(equipment_list))
        return report

    def generate_rul_report(self) -> Dict[str, Any]:
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_equipment": len(self.equipment_data),
            "equipment": [],
        }

        for equipment in self.equipment_data:
            health = self.analyze_equipment_health(
                equipment["id"],
                equipment["sensors"],
            )
            rul = self.predict_maintenance_date(
                equipment["id"],
                equipment.get("usage_hours", 0),
                equipment.get("failure_history", []),
            )
            report["equipment"].append(
                {
                    "equipment_id": equipment["id"],
                    "name": equipment.get("name", equipment["id"]),
                    "health_score": health["health_score"],
                    "status": health["status"],
                    "remaining_hours": rul["remaining_hours"],
                    "recommended_maintenance_date": rul["recommended_maintenance_date"],
                    "reliability_score": rul["reliability_score"],
                    "confidence": rul["confidence"],
                    "model": rul["model"],
                    "alerts": health["alerts"],
                }
            )

        logger.info("RUL report generated for %d equipment", len(self.equipment_data))
        return report


def run_predictive_maintenance() -> Dict[str, Any]:
    print("=== 예측 정비 시스템 ===")

    pm = PredictiveMaintenance()

    print("\n=== 설비 건강 상태 분석 ===")
    for equipment in pm.equipment_data:
        health = pm.analyze_equipment_health(equipment["id"], equipment["sensors"])
        print(f"\n{health['equipment_id']}:")
        print(f"  건강 점수: {health['health_score']}/100")
        print(f"  상태: {health['status']}")
        if health["alerts"]:
            print(f"  알림: {', '.join(health['alerts'])}")

    print("\n=== 예측 정비 리포트 ===")
    report = pm.generate_maintenance_report()

    print(f"생성 시간: {report['generated_at']}")
    print(f"총 설비 수: {report['total_equipment']}")
    print(f"상태 요약:")
    for status, count in report["status_summary"].items():
        print(f"  {status}: {count}대")

    print("\n=== 잔여 수명 예측 (RUL) ===")
    rul_report = pm.generate_rul_report()
    for item in rul_report["equipment"]:
        print(f"\n{item['equipment_id']}:")
        print(f"  이름: {item['name']}")
        print(f"  건강 점수: {item['health_score']}/100 ({item['status']})")
        print(f"  신뢰도 점수: {item['reliability_score']:.1f}/100")
        print(f"  잔여 수명: {item['remaining_hours']:.0f}시간")
        print(f"  권장 정비일: {item['recommended_maintenance_date']}")
        print(f"  예측 신뢰도: {item['confidence'] * 100:.0f}%")
        print(f"  모델: {item['model']}")

    return report


if __name__ == "__main__":
    run_predictive_maintenance()
