from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.config import DRIFT_CONFIG


logger = logging.getLogger(__name__)

NUMERIC_FEATURES = [
    "temperature",
    "pressure",
    "vibration",
    "humidity",
    "cycle_time",
    "defect_probability",
]


class DriftDetector:
    def __init__(
        self,
        ks_alpha: Optional[float] = None,
        psi_threshold: Optional[float] = None,
        reference_window: Optional[int] = None,
    ) -> None:
        self.ks_alpha = ks_alpha if ks_alpha is not None else DRIFT_CONFIG["ks_alpha"]
        self.psi_threshold = (
            psi_threshold if psi_threshold is not None else DRIFT_CONFIG["psi_threshold"]
        )
        self.reference_window = (
            reference_window
            if reference_window is not None
            else DRIFT_CONFIG["reference_window"]
        )

    def ks_test(
        self, reference: pd.DataFrame, live: pd.DataFrame
    ) -> Dict[str, Dict[str, Any]]:
        """Compute KS test p-value for each numeric feature."""
        results: Dict[str, Dict[str, Any]] = {}
        for col in NUMERIC_FEATURES:
            if col not in reference or col not in live:
                continue
            ref_vals = reference[col].dropna().values
            live_vals = live[col].dropna().values
            if len(ref_vals) == 0 or len(live_vals) == 0:
                results[col] = {"p_value": 1.0, "statistic": 0.0, "drifted": False}
                continue

            try:
                from scipy.stats import ks_2samp

                stat, p_value = ks_2samp(ref_vals, live_vals)
            except ImportError:
                logger.warning("scipy not available; skipping KS test")
                stat, p_value = 0.0, 1.0

            results[col] = {
                "p_value": float(p_value),
                "statistic": float(stat),
                "drifted": bool(p_value < self.ks_alpha),
            }
        return results

    def psi(
        self, reference: pd.DataFrame, live: pd.DataFrame, n_bins: int = 10
    ) -> Dict[str, Dict[str, Any]]:
        """Compute Population Stability Index for each numeric feature."""
        results: Dict[str, Dict[str, Any]] = {}
        for col in NUMERIC_FEATURES:
            if col not in reference or col not in live:
                continue
            ref_vals = reference[col].dropna().values
            live_vals = live[col].dropna().values
            if len(ref_vals) == 0 or len(live_vals) == 0:
                results[col] = {"psi": 0.0, "drifted": False}
                continue

            all_vals = np.concatenate([ref_vals, live_vals])
            bins = np.percentile(all_vals, np.linspace(0, 100, n_bins + 1))
            bins[0] = -np.inf
            bins[-1] = np.inf

            ref_counts, _ = np.histogram(ref_vals, bins=bins)
            live_counts, _ = np.histogram(live_vals, bins=bins)

            ref_pct = ref_counts / len(ref_vals)
            live_pct = live_counts / len(live_vals)

            eps = 1e-6
            ref_pct = np.clip(ref_pct, eps, 1.0)
            live_pct = np.clip(live_pct, eps, 1.0)

            psi_value = np.sum((ref_pct - live_pct) * np.log(ref_pct / live_pct))

            results[col] = {
                "psi": float(psi_value),
                "drifted": bool(psi_value > self.psi_threshold),
            }
        return results

    def detect(
        self, reference: pd.DataFrame, live: pd.DataFrame
    ) -> Dict[str, Any]:
        """Run KS test and PSI on all numeric features.

        Returns a report dict with per-feature results and overall flag.
        """
        ks_results = self.ks_test(reference, live)
        psi_results = self.psi(reference, live)

        drifted_features: List[Dict[str, Any]] = []
        for col in NUMERIC_FEATURES:
            if col not in ks_results and col not in psi_results:
                continue
            entry: Dict[str, Any] = {"feature": col}
            if col in ks_results:
                entry["ks_p_value"] = ks_results[col]["p_value"]
                entry["ks_drifted"] = ks_results[col]["drifted"]
            if col in psi_results:
                entry["psi"] = psi_results[col]["psi"]
                entry["psi_drifted"] = psi_results[col]["drifted"]
            entry["drifted"] = entry.get("ks_drifted", False) or entry.get(
                "psi_drifted", False
            )
            drifted_features.append(entry)

        drift_detected = any(f["drifted"] for f in drifted_features)

        return {
            "drifted_features": drifted_features,
            "drift_detected": drift_detected,
            "ks_results": ks_results,
            "psi_results": psi_results,
        }
