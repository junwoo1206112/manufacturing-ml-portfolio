# 테스트 가이드

## 개요

pytest 기반, **78개 테스트**, 별도 설정 파일 없이 기본 설정으로 동작합니다.

## 기본 실행

```bash
# 전체 테스트 (축약 출력)
pytest -q

# 상세 출력 (각 테스트명 + 결과)
pytest -v

# 실패 시 짧은 traceback
pytest --tb=short
```

## 특정 파일만 실행

```bash
pytest tests/test_model.py -v          # 모델 관련 테스트만
pytest tests/test_drift.py -v          # 드리프트 감지 테스트만
pytest tests/test_data.py -v           # 데이터 생성/검증 테스트
pytest tests/test_config.py -v         # 설정 테스트
pytest tests/test_logging.py -v        # 로깅 테스트
pytest tests/test_visualizer.py -v     # 시각화 테스트
pytest tests/test_dashboard.py -v      # 대시보드 API 테스트
pytest tests/test_extended.py -v       # 확장 시각화 테스트
```

## 특정 테스트만 실행

```bash
# 클래스명으로 필터
pytest -k "TestQualityPredictor" -v

# 메서드명으로 필터
pytest -k "test_drift" -v
pytest -k "test_shap or test_metadata" -v

# 키워드 and 조합
pytest -k "test_drift and not identical" -v
```

## 실패 시 디버깅

```bash
# 실패 지점에서 pdb 열기
pytest --pdb

# 첫 실패에서 중단
pytest -x

# 실패 상세 보기
pytest -v --tb=long
```

## 커버리지 측정 (선택, pytest-cov 필요)

```bash
pip install pytest-cov
pytest --cov=src --cov-report=term-missing
```

## 예상 실행 시간

| 테스트 파일 | 소요 시간 | 설명 |
|------------|-----------|------|
| test_data.py | ~6초 | 데이터 생성 + 검증 + 전처리 |
| test_model.py | ~4초 | 모델 학습 + SHAP + 메타데이터 |
| test_logging.py | <1초 | 로깅 설정 검증 |
| test_config.py | <1초 | 설정 상수 검증 |
| test_drift.py | <1초 | 드리프트 감지 |
| test_visualizer.py | ~1초 | 시각화 생성 |
| test_dashboard.py | <1초 | Flask API 응답 |
| test_extended.py | ~1초 | 확장 시각화 |
| **전체** | **~12초** | 78개 테스트 |

## 테스트가 실패할 경우

### 1. SHAP 관련 실패
```bash
pip install shap>=0.42.0
```

### 2. scipy 관련 실패
```bash
pip install scipy>=1.10.0
```

### 3. matplotlib "TclError" / tkinter 실패
자동으로 `matplotlib.use("Agg")`를 설정하지만, 환경에 따라 다음 필요:
```bash
pip install pyqt5  # 또는
set MPLBACKEND=Agg  # Windows
export MPLBACKEND=Agg  # macOS/Linux
```

### 4. Flask 포트 충돌
```bash
# 5000번 포트가 사용 중이면 환경변수로 변경
set PORT=5001
python dashboard/app.py
```

## CI 환경 (GitHub Actions)

`.github/workflows/ci.yml`에 정의된 대로 GitHub에 push/PR 시 자동 실행:

```yaml
steps:
  - pip install -r requirements.txt
  - pytest -v --tb=short
```

## 테스트 구조

```
tests/
├── test_config.py         # 설정 기본값, 딥머지, 경로
├── test_data.py           # DataGenerator, DataValidator, DataPipeline
├── test_model.py          # QualityPredictor, AnomalyDetector, ModelManager
├── test_drift.py          # DriftDetector (KS test, PSI)
├── test_logging.py        # setup_logging, get_logger, 파일 핸들러
├── test_visualizer.py     # ManufacturingVisualizer (matplotlib)
├── test_dashboard.py      # Flask API 엔드포인트
└── test_extended.py       # ManufacturingVisualizer 확장 테스트
```

각 테스트는 `sys.path.insert(0, ...)`로 프로젝트 루트를 추가한 후 `from src.xxx import ...` 방식으로 모듈을 임포트합니다. pytest가 자동으로 테스트를 수집하고 실행합니다.
