# Manufacturing Simulation Portfolio — Handover Status

> Generated: 2026-06-15  
> Purpose: Allow another AI agent to pick up and continue work seamlessly.

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Project** | Smart Manufacturing Simulation Portfolio |
| **Target** | 제조 AI 포트폴리오 |
| **Python** | 3.12 |
| **Key libs** | scikit-learn, pandas, numpy, matplotlib, seaborn, Flask, SHAP |
| **Test framework** | pytest (72 tests, all passing) |
| **Workflow** | OpenSpec v1.3 (Spec-Driven Development) |

---

## 2. Completed Phases

### Phase 0 — Fix Runtime Issues & ML Quality (`fix-runtime-issues`, `ml-model-quality-fix`)
**Archived**: `openspec/changes/archive/2026-06-15-fix-runtime-issues/`, `2026-06-15-ml-model-quality-fix/`

- Fixed ML pipeline crashes (train/test split, feature alignment)
- Improved defective class F1 from ~0 to **~0.59**
- AUC-ROC: **~0.85**, AUC-PR: **~0.66**
- Removed `predict` column leak; proper classification pipeline
- Added `defect_probability` feature and statistical distribution features

### Phase 1 — Professionalism (`professionalism-enhancement`)
**Archived**: `openspec/changes/archive/2026-06-15-professionalism-enhancement/`

- Added `config/config.yaml` runtime loading
- RUL (Remaining Useful Life) enhancement with lognormal model
- Flask dashboard (`dashboard/app.py`) with static visualization serving
- `.gitignore` with sensible output exclusions
- `models/` cleanup: `quality_predictor_latest.*` aliases
- Tests grew from 56 → 66 → 72

### Phase 2 — Production Polish (`completion-polish`)
**Archived**: `openspec/changes/archive/2026-06-15-completion-polish/`

- **Type hints**: All `src/` modules annotated (`from __future__ import annotations`)
- **Structured logging**: `src/logging_config.py` with `setup_logging()`; all `print()` replaced with `logging.getLogger()` calls in core modules; `print()` kept only in `if __name__ == "__main__"` demo blocks
- **Rich model metadata**: `QualityPredictor.save_model()` saves `feature_columns`, `threshold`, `threshold_metric`, `class_distribution`, `training_config`, `feature_importance`, full `metrics` dict; schema version `"2.0"`
- **SHAP interpretability**: `QualityPredictor.explain_prediction(X_sample)` with `TreeExplainer` (tree models) / `KernelExplainer` (linear); demo in `run_quality_prediction()` prints SHAP values
- **Tests added**: metadata schema validation (required keys, version), SHAP value shape matching, logging configuration (file handler, caplog fixture)

---

## 3. OpenSpec Workflow Summary

```
openspec/
├── config.yaml                 # Project context, rules, schemas
├── specs/                      # Main specs (source of truth)
│   ├── type-hinted-codebase/spec.md
│   ├── structured-logging/spec.md
│   ├── rich-model-metadata/spec.md
│   └── shap-interpretability/spec.md
└── changes/
    ├── archive/                # Completed, archived changes
    │   ├── 2026-06-15-fix-runtime-issues/
    │   ├── 2026-06-15-ml-model-quality-fix/
    │   ├── 2026-06-15-professionalism-enhancement/
    │   └── 2026-06-15-completion-polish/
    └── competitiveness-enhancement/     # NEXT: Phase 3 (scaffolded, empty)
```

**CLI commands**:
```bash
openspec list --json                  # Active changes (currently: none)
openspec new change "name"            # Scaffold new change
openspec status --change "name" --json
openspec validate --all --json        # Validate specs before archive
openspec archive "name" --yes         # Archive + sync specs
```

---

## 4. Project Structure

```
manufacturing-simulation-portfolio/
├── main.py                          # Full pipeline entrypoint
├── requirements.txt                 # Includes shap>=0.42
├── .gitignore
├── src/
│   ├── config.py                    # Module-level config (type-hinted)
│   ├── logging_config.py            # setup_logging(), get_logger()
│   ├── data_generator.py            # Manufacturing data generation
│   ├── data_analyzer.py             # Analysis + CSV save
│   ├── data_validator.py            # Schema/missing/range validation
│   ├── data_pipeline.py             # Feature engineering + split
│   ├── quality_predictor.py         # QualityPredictor + SHAP explain + demo
│   ├── model_manager.py             # Save/load/list with metadata
│   ├── predictive_maintenance.py    # RUL + health scoring
│   ├── anomaly_detector.py          # Anomaly detection (IsolationForest)
│   ├── hyperparameter_tuner.py      # GridSearchCV/RandomizedSearchCV
│   └── visualizer.py                # Matplotlib/seaborn plots
├── dashboard/
│   └── app.py                       # Flask dashboard
├── models/                          # Trained models (auto-managed)
│   ├── quality_predictor_latest.joblib
│   └── quality_predictor_latest_meta.json
├── data/                            # Generated CSV (auto)
├── visualizations/                  # Plot images (auto)
├── config/
│   ├── config.yaml                  # Runtime overrides
│   └── equipment.json               # Equipment fleet config
└── tests/
    ├── test_model.py                # Module: QualityPredictor, ModelManager
    ├── test_data.py                 # Module: DataGenerator, Validator, Pipeline
    ├── test_config.py               # Module: Config constants and defaults
    ├── test_visualizer.py           # Module: ManufacturingVisualizer
    ├── test_dashboard.py            # Module: Dashboard endpoints
    ├── test_extended.py             # Extended test coverage
    └── test_logging.py              # NEW: Logging setup verification
```

---

## 5. Test & Run Status

```text
$ pytest -q
72 passed, 1 warning in ~10s

$ python main.py
# Full pipeline: data gen → validation → analysis → training → SHAP → PM → viz
# All stages complete, SHAP explanation printed, model saved with rich metadata
```

**Known LSP warnings** (non-blocking, type-stub issues):
- Pandas `.to_numpy()` on ndarray → type stub version mismatch
- scikit-learn `zero_division=0` expecting `str` stub → runtime accepts int
- SHAP `TreeExplainer` expected_value shape → handled via `_to_scalar()` helper

---

## 6. ML Performance Metrics (Phase 0 tuned)

| Metric | Value |
|---|---|
| Accuracy | ~0.82 |
| F1 (defective class) | ~0.59 |
| F1 (normal class) | ~0.89 |
| AUC-ROC | ~0.85 |
| AUC-PR | ~0.66 |
| Optimized threshold | ~0.69 (F1-based tuning) |

---

## 7. NEXT: Phase 3 — Competitiveness Enhancement

**Change name**: `competitiveness-enhancement` (scaffolded, no artifacts yet)

**Proposed scope** (from original project plan):

1. **Docker containerization**
   - `Dockerfile` (Python 3.12-slim base)
   - `docker-compose.yml` (app + dashboard)
   - `.dockerignore`

2. **CI/CD pipeline**
   - GitHub Actions workflow (`.github/workflows/ci.yml`)
   - Run `pytest` on push/PR
   - Optional: lint check (ruff/flake8)

3. **README polish**
   - Add badges: pytest passing, Python version, license
   - Add screenshots of dashboard/visualizations
   - Architecture overview diagram (ASCII or Mermaid)
   - Honest metrics table (measured, not estimated)

4. **Data drift detection**
   - Module to compare training vs inference distributions
   - Statistical tests (KS test, PSI) for feature drift
   - Alert/warning when significant drift detected
   - Integration into `main.py` pipeline demo

**To start**: Run the following and then create proposal/design/specs/tasks:
```bash
openspec new change "competitiveness-enhancement"   # already done
# Then create artifacts: proposal.md, design.md, specs/, tasks.md
```

---

## 8. Key Conventions (For Another AI)

- **All models saved with metadata** → model + `_meta.json` pair; `*_latest.*` symlink/alias
- **SHAP** → use `TreeExplainer` for tree models, `KernelExplainer` for linear; handle 3D output with `[..., 1]`
- **Logging** → `setup_logging()` at app start; module loggers via `get_logger(__name__)` or `logging.getLogger(__name__)`
- **Tests** → use `matplotlib.use("Agg")` before importing visualizer to avoid Tk failures
- **OpenSpec archive** → if CLI `--no-validate` needed, ensure specs use `SHALL`/`MUST` keywords for requirements
- **Korean text** → used in UI labels, docstrings, log messages; correct on Linux/UTF-8 terminals
- **Config** → `config/config.yaml` overrides `src/config.py` defaults via deep merge
