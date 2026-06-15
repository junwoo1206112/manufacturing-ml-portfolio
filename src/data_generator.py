from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from src.config import DATA_CONFIG, PRODUCTION_LINES
from src.logging_config import get_logger

logger = get_logger(__name__)


class ManufacturingDataGenerator:
    def __init__(self, seed: Optional[int] = None) -> None:
        self.seed = seed or DATA_CONFIG["random_seed"]
        self.rng = np.random.default_rng(self.seed)

    def generate_sensor_data(
        self, num_records: int, line_config: Dict[str, Any]
    ) -> Tuple[NDArray[np.float64], ...]:
        temp_base = np.mean(line_config["temp_range"])
        temp_std = (line_config["temp_range"][1] - line_config["temp_range"][0]) / 6
        temperature = self.rng.normal(temp_base, temp_std, num_records)

        pressure_base = np.mean(line_config["pressure_range"])
        pressure_std = (
            line_config["pressure_range"][1] - line_config["pressure_range"][0]
        ) / 6
        pressure = self.rng.normal(pressure_base, pressure_std, num_records)

        vib_base = np.mean(line_config["vibration_range"])
        vib_std = (line_config["vibration_range"][1] - line_config["vibration_range"][0]) / 6
        vibration = self.rng.normal(vib_base, vib_std, num_records)

        humidity_base = np.mean(line_config["humidity_range"])
        humidity_std = (
            line_config["humidity_range"][1] - line_config["humidity_range"][0]
        ) / 6
        humidity = self.rng.normal(humidity_base, humidity_std, num_records)

        cycle_base = np.mean(line_config["cycle_time_range"])
        cycle_std = (
            line_config["cycle_time_range"][1] - line_config["cycle_time_range"][0]
        ) / 6
        cycle_time = self.rng.normal(cycle_base, cycle_std, num_records)

        return temperature, pressure, vibration, humidity, cycle_time

    def apply_daily_cycle(
        self, timestamps: List[datetime], temperature: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        hours = np.array([t.hour + t.minute / 60 for t in timestamps])
        daily_pattern = 3 * np.sin(2 * np.pi * (hours - 6) / 24)
        return temperature + daily_pattern

    def apply_equipment_degradation(
        self, vibration: NDArray[np.float64], usage_hours: NDArray[np.int64]
    ) -> NDArray[np.float64]:
        degradation = 0.0001 * usage_hours
        return vibration + degradation

    def calculate_defect_probability(
        self,
        temperature: NDArray[np.float64],
        pressure: NDArray[np.float64],
        vibration: NDArray[np.float64],
        humidity: NDArray[np.float64],
        line_config: Dict[str, Any],
    ) -> NDArray[np.float64]:
        baseline = line_config.get("defect_baseline", 0.03)

        temp_score = (temperature - 30.0) / 5.0
        vib_score = (vibration - 0.50) / 0.20
        pressure_score = np.maximum(
            (pressure - 110.0) / 5.0, (90.0 - pressure) / 5.0
        )
        humidity_score = (humidity - 60.0) / 15.0

        interaction_score = 0.5 * temp_score * vib_score

        risk_score = (
            -4.5
            + np.log(baseline / 0.03)
            + 2.0 * temp_score
            + 2.5 * vib_score
            + 1.5 * pressure_score
            + 0.8 * humidity_score
            + interaction_score
        )

        defect_prob = 1.0 / (1.0 + np.exp(-risk_score / 1.5))
        defect_prob = np.clip(defect_prob, 0.001, 0.999)

        return defect_prob

    def generate(self, num_records: Optional[int] = None) -> pd.DataFrame:
        n_records: int = num_records if num_records is not None else DATA_CONFIG["num_records"]
        num_records = n_records
        start_date = datetime.strptime(DATA_CONFIG["start_date"], "%Y-%m-%d")
        timestamps = [start_date + timedelta(hours=i) for i in range(num_records)]

        line_names = list(PRODUCTION_LINES.keys())
        line_choices = self.rng.choice(line_names, num_records)

        data: Dict[str, Any] = {
            "timestamp": timestamps,
            "production_line": line_choices,
            "operator_id": self.rng.integers(1, 6, num_records),
        }

        temperatures = np.zeros(num_records)
        pressures = np.zeros(num_records)
        vibrations = np.zeros(num_records)
        humidities = np.zeros(num_records)
        cycle_times = np.zeros(num_records)

        for line_name in PRODUCTION_LINES:
            mask = line_choices == line_name
            count = mask.sum()
            if count == 0:
                continue
            line_config = PRODUCTION_LINES[line_name]
            temp, pres, vib, hum, cycle = self.generate_sensor_data(count, line_config)
            temperatures[mask] = temp
            pressures[mask] = pres
            vibrations[mask] = vib
            humidities[mask] = hum
            cycle_times[mask] = cycle

        temperatures = self.apply_daily_cycle(timestamps, temperatures)
        usage_hours = np.arange(num_records)
        vibrations = self.apply_equipment_degradation(vibrations, usage_hours)

        defect_probs = np.zeros(num_records)
        for line_name in PRODUCTION_LINES:
            mask = line_choices == line_name
            count = mask.sum()
            if count == 0:
                continue
            line_config = PRODUCTION_LINES[line_name]
            defect_probs[mask] = self.calculate_defect_probability(
                temperatures[mask],
                pressures[mask],
                vibrations[mask],
                humidities[mask],
                line_config,
            )

        is_defective = self.rng.binomial(1, defect_probs)
        defect_probability = np.clip(defect_probs, 0.0, 1.0)

        window = min(100, num_records)
        defect_rate = (
            pd.Series(is_defective)
            .rolling(window=window, min_periods=1)
            .mean()
            .to_numpy()
        )

        data["temperature"] = np.round(temperatures, 2)
        data["pressure"] = np.round(pressures, 2)
        data["vibration"] = np.round(vibrations, 4)
        data["humidity"] = np.round(humidities, 2)
        data["cycle_time"] = np.round(cycle_times, 2)
        data["defect_probability"] = np.round(defect_probability, 4)
        data["defect_rate"] = np.round(defect_rate, 4)
        data["is_defective"] = is_defective

        df = pd.DataFrame(data)

        operators = {1: "김철수", 2: "이영희", 3: "박지민", 4: "최동훈", 5: "정미라"}
        df["operator_name"] = df["operator_id"].map(operators)

        logger.info("Generated %d manufacturing records", len(df))
        return df


def generate_manufacturing_data(num_records: int = 5000) -> pd.DataFrame:
    generator = ManufacturingDataGenerator()
    return generator.generate(num_records)


if __name__ == "__main__":
    print("=== 제조 공정 데이터 생성 ===")
    df = generate_manufacturing_data(5000)
    print(f"\n총 레코드: {len(df)}")
    print(f"\n라인별 분포:")
    print(df["production_line"].value_counts())
    print(f"\n불량률: {df['is_defective'].mean() * 100:.2f}%")
    print(f"\n센서 통계:")
    print(df[["temperature", "pressure", "vibration"]].describe())
