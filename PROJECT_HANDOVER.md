# Project handover

이전 handover에는 2026-06-15의 과거 성능·테스트 수·계획이 포함되어 있어 면접용 최신 증빙으로 사용하지 않습니다.

현재 상태, 측정 지표, Docker 실행 및 SQLite 예측 이력 검증은 [PORTFOLIO_EVIDENCE.md](PORTFOLIO_EVIDENCE.md)를 단일 기준 문서로 확인하세요.

기술적 변경을 이어갈 때는 다음을 먼저 실행합니다.

```powershell
pip install -r requirements-tested.txt
pytest -q
python main.py
docker compose up --build -d
```

범위는 로컬·합성 데이터 포트폴리오입니다. 모델 파일은 artifact source, SQLite는 이력·집계 계층으로 유지하며 실제 운영 시스템으로 확장하지 않습니다.
