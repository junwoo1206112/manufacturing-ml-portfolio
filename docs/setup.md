# 설치 및 실행 가이드

## 사전 요구사항

- Python 3.12 이상
- pip (Python 패키지 관리자)
- Docker (선택사항, 컨테이너 실행 시)

## 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/junwoo1206112/manufacturing-ml-portfolio.git
cd manufacturing-simulation-portfolio
```

### 2. 가상 환경 생성 (권장)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 개발 의존성 설치 (선택)

```bash
pip install -r requirements-dev.txt
```

## 실행 방법

### Docker (권장)

```bash
docker compose up
```

`app` 서비스가 전체 파이프라인을 실행한 후 종료됩니다. `dashboard` 서비스는 `http://localhost:5000`에서 계속 동작합니다 (로컬 실행 시 `config.yaml`의 `dashboard.port` 기본값 5001).

### 전체 파이프라인 로컬 실행

```bash
python main.py
```

실행 단계:
1. 제조 공정 데이터 생성 (5000건)
2. 데이터 검증 (스키마, 결측치, 범위)
3. 데이터 분석 (불량률, 통계)
4. 데이터 전처리 및 특성 엔지니어링
5. 품질 예측 모델 학습 + SHAP 설명 출력
6. 예측 정비 분석 (RUL)
7. 데이터 드리프트 감지 (KS test + PSI)
8. 시각화 생성 (4종 PNG)

모델과 메타데이터는 `models/`에, 시각화 PNG는 `visualizations/`에 저장됩니다.

### 대시보드 실행

```bash
python dashboard/app.py
```

브라우저에서 `http://localhost:PORT`에 접속합니다 (기본값 5001, `python dashboard/app.py 5001`).

### 개별 모듈 실행

```bash
# 데이터 생성
python -m src.data_generator

# 데이터 검증
python -m src.data_validator

# 품질 예측 + SHAP
python -m src.quality_predictor

# 드리프트 감지
python -m src.drift_detector

# 시각화
python -m src.visualizer
```

## 테스트 실행

```bash
pytest tests/ -v
```

## 프로젝트 구조

```
manufacturing-simulation-portfolio/
├── README.md              # 프로젝트 설명
├── requirements.txt       # 필요 라이브러리
├── main.py                # 메인 실행 파일
├── Dockerfile             # 컨테이너 이미지
├── docker-compose.yml     # app + dashboard 서비스
├── .github/workflows/     # GitHub Actions CI
├── config/                # 설정 파일
│   ├── config.yaml
│   └── equipment.json
├── src/                   # 핵심 소스 코드
│   ├── config.py          # 설정 관리 (deep-merge)
│   ├── logging_config.py  # 구조화된 로깅
│   ├── data_generator.py  # 물리적 기반 데이터 생성
│   ├── data_validator.py  # 데이터 검증
│   ├── data_pipeline.py   # 전처리 파이프라인
│   ├── data_analyzer.py   # 데이터 분석
│   ├── quality_predictor.py  # 품질 예측 + SHAP
│   ├── anomaly_detector.py   # 이상 탐지
│   ├── model_manager.py   # 모델 저장/로드/버전 관리
│   ├── hyperparameter_tuner.py  # 하이퍼파라미터 튜닝
│   ├── predictive_maintenance.py  # 예측 정비 (RUL)
│   ├── drift_detector.py  # 데이터 드리프트 감지
│   └── visualizer.py      # 시각화
├── dashboard/             # 웹 대시보드
│   ├── app.py
│   ├── templates/
│   └── static/
├── tests/                 # 78개 테스트
├── docs/                  # 문서
├── data/                  # 생성 데이터 (auto)
├── models/                # 학습 모델 (auto)
└── visualizations/        # 시각화 PNG (auto)
```
