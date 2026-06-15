from __future__ import annotations

import logging
import os
import platform
import warnings
from typing import Any, Dict, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


logger = logging.getLogger(__name__)


def _configure_korean_font() -> None:
    system = platform.system()
    candidates: list[str] = []
    if system == "Windows":
        candidates = ["Malgun Gothic", "NanumGothic"]
    elif system == "Darwin":
        candidates = ["AppleGothic", "NanumGothic"]
    else:
        candidates = ["NanumGothic", "Noto Sans CJK KR", "NanumBarunGothic"]

    for font in candidates:
        try:
            plt.rcParams["font.family"] = font
            plt.rcParams["axes.unicode_minus"] = False
            return
        except Exception:
            continue

    warnings.warn("한국어 폰트를 찾을 수 없습니다. 기본 폰트로 폐기합니다.")


class ManufacturingVisualizer:
    def __init__(self) -> None:
        _configure_korean_font()
        plt.style.use("seaborn-v0_8")
        self.colors = ["#2ecc71", "#e74c3c", "#3498db", "#f39c12"]

    def plot_defect_analysis(
        self, df: pd.DataFrame, save_path: str = "visualizations/"
    ) -> None:
        _configure_korean_font()
        os.makedirs(save_path, exist_ok=True)

        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        axes[0, 0].pie(
            df["is_defective"].value_counts(),
            labels=["정상", "불량"],
            autopct="%1.1f%%",
            colors=["#2ecc71", "#e74c3c"],
        )
        axes[0, 0].set_title("전체 불량률")

        line_defect = df.groupby("production_line")["is_defective"].mean() * 100
        axes[0, 1].bar(line_defect.index, line_defect.values, color=self.colors[:3])
        axes[0, 1].set_title("라인별 불량률")
        axes[0, 1].set_ylabel("불량률 (%)")

        axes[1, 0].hist(
            df["temperature"],
            bins=30,
            color="#3498db",
            alpha=0.7,
            edgecolor="black",
        )
        axes[1, 0].set_title("온도 분포")
        axes[1, 0].set_xlabel("온도 (°C)")
        axes[1, 0].set_ylabel("빈도")

        axes[1, 1].scatter(
            df["vibration"],
            df["defect_probability"],
            c=df["is_defective"],
            cmap="RdYlGn_r",
            alpha=0.5,
        )
        axes[1, 1].set_title("진동 vs 불량 확률")
        axes[1, 1].set_xlabel("진동")
        axes[1, 1].set_ylabel("불량 확률")

        plt.tight_layout()
        plt.savefig(f"{save_path}defect_analysis.png", dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("시각화 저장: %sdefect_analysis.png", save_path)

    def plot_time_series(
        self, df: pd.DataFrame, save_path: str = "visualizations/"
    ) -> None:
        _configure_korean_font()
        os.makedirs(save_path, exist_ok=True)

        fig, axes = plt.subplots(2, 1, figsize=(12, 8))

        hourly_defect = df.groupby(df["timestamp"].dt.hour)["is_defective"].mean() * 100
        axes[0].plot(
            hourly_defect.index,
            hourly_defect.values,
            marker="o",
            color="#e74c3c",
        )
        axes[0].fill_between(
            hourly_defect.index, hourly_defect.values, alpha=0.3, color="#e74c3c"
        )
        axes[0].set_title("시간대별 불량률 추이")
        axes[0].set_xlabel("시간")
        axes[0].set_ylabel("불량률 (%)")
        axes[0].grid(True, alpha=0.3)

        daily_temp = df.groupby(df["timestamp"].dt.date)["temperature"].mean()
        axes[1].plot(
            range(len(daily_temp)), daily_temp.values, marker="s", color="#3498db"
        )
        axes[1].set_title("일별 평균 온도 변화")
        axes[1].set_xlabel("날짜")
        axes[1].set_ylabel("온도 (°C)")
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(f"{save_path}time_series.png", dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("시각화 저장: %stime_series.png", save_path)

    def plot_correlation_matrix(
        self, df: pd.DataFrame, save_path: str = "visualizations/"
    ) -> None:
        _configure_korean_font()
        os.makedirs(save_path, exist_ok=True)

        numeric_cols = [
            "temperature",
            "pressure",
            "vibration",
            "humidity",
            "cycle_time",
            "defect_probability",
            "is_defective",
        ]

        corr_matrix = df[numeric_cols].corr()

        plt.figure(figsize=(10, 8))
        sns.heatmap(
            corr_matrix,
            annot=True,
            cmap="coolwarm",
            center=0,
            fmt=".2f",
            square=True,
            linewidths=0.5,
        )
        plt.title("변수 간 상관관계 매트릭스")
        plt.tight_layout()
        plt.savefig(
            f"{save_path}correlation_matrix.png", dpi=150, bbox_inches="tight"
        )
        plt.close()
        logger.info("시각화 저장: %scorrelation_matrix.png", save_path)

    def create_dashboard_summary(
        self, df: pd.DataFrame, save_path: str = "visualizations/"
    ) -> Dict[str, Any]:
        _configure_korean_font()
        os.makedirs(save_path, exist_ok=True)

        summary: Dict[str, Any] = {
            "total_records": len(df),
            "defect_rate": df["is_defective"].mean() * 100,
            "avg_temperature": df["temperature"].mean(),
            "avg_pressure": df["pressure"].mean(),
            "avg_vibration": df["vibration"].mean(),
            "avg_cycle_time": df["cycle_time"].mean(),
        }

        fig, ax = plt.subplots(figsize=(10, 6))

        metrics = list(summary.keys())
        values = list(summary.values())

        colors = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"]

        bars = ax.barh(metrics, values, color=colors)

        ax.set_xlabel("값")
        ax.set_title("제조 공정 핵심 지표")

        for bar, value in zip(bars, values):
            ax.text(
                bar.get_width() + 0.5,
                bar.get_y() + bar.get_height() / 2,
                f"{value:.2f}",
                va="center",
                fontsize=10,
            )

        plt.tight_layout()
        plt.savefig(f"{save_path}dashboard_summary.png", dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("시각화 저장: %sdashboard_summary.png", save_path)

        return summary


def run_visualization() -> Dict[str, Any]:
    logger.info("=== 데이터 시각화 ===")

    df = pd.read_csv("data/manufacturing_data.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    viz = ManufacturingVisualizer()

    logger.info("1. 불량 분석 시각화...")
    viz.plot_defect_analysis(df)

    logger.info("2. 시계열 분석 시각화...")
    viz.plot_time_series(df)

    logger.info("3. 상관관계 매트릭스...")
    viz.plot_correlation_matrix(df)

    logger.info("4. 대시보드 요약...")
    summary = viz.create_dashboard_summary(df)

    logger.info("=== 시각화 완료 ===")
    logger.info("visualizations/ 디렉터리에 이미지 파일이 저장되었습니다.")

    return summary


if __name__ == "__main__":
    print("시각화 모듈을 직접 실행합니다.")
    run_visualization()
