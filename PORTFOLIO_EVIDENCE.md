# Portfolio evidence — Smart Manufacturing ML

Last verified: 2026-11-16 (Asia/Seoul)

## What this project demonstrates

- A synthetic manufacturing-data pipeline with chronological train/validation/test splits.
- SQLite lineage for runs, sensor observations, model artifacts and test metrics, held-out test predictions, and drift reports.
- A local Flask dashboard that displays the latest SQLite-backed model metrics and prediction-history aggregates.
- Chronological evaluation from the five raw sensor features; the separate `DataPipeline` utility is exploratory only and is not part of the scored training path.

## Latest measured evidence

| Check | Result |
|---|---|
| Held-out test F1 (defect class) | 0.7519 |
| Held-out test PR-AUC | 0.7692 |
| Held-out test AUC-ROC | 0.8121 |
| Tuned threshold | 0.4700 |
| Test prediction rows persisted | 750 |
| Python test suite | 86 passed, 1 warning |
| Docker Compose check | `app` completed with exit code 0; `dashboard` served at `http://localhost:5000`; SQLite query returned 750 prediction rows |

Detailed, auto-generated metrics: [docs/latest_model_metrics.md](docs/latest_model_metrics.md).

## Reproduce the verified demo

```powershell
docker compose up --build -d
docker compose logs -f app
# Open http://localhost:5000 after the app service completes.
docker compose exec dashboard python -c "import sqlite3; c=sqlite3.connect('/app/data/manufacturing_history.db'); print(c.execute('select count(*) from predictions').fetchone()[0])"
```

The expected final command output is `750` for this recorded execution. Re-running the pipeline creates another run and can change the total.

## Boundaries

- The data and drift scenario are synthetic; the metrics are not claims about a production line.
- Flask's development server and SQLite are intentional for this local portfolio demo. This project does not claim a production deployment, authentication layer, or production database.
- [`requirements-tested.txt`](requirements-tested.txt) records the exact runtime versions tested for this evidence; `requirements.txt`, Docker, and CI all install that same snapshot.
