# 웹 대시보드 테스트 가이드

## 준비

```bash
# 1. 데이터 생성 + 전체 파이프라인 실행 (최초 1회)
python main.py

# 2. 대시보드 실행
python dashboard/app.py 5001

# 3. 브라우저 열기
# http://localhost:5001
```

---

## 1. 기본 동작 확인

### 1.1 페이지 로딩
- [ ] 브라우저에서 `http://localhost:5001` 접속
- [ ] 좌측 사이드바에 6개 메뉴 표시: 대시보드, 설비 상태, 데이터 분석, 이상 탐지, RUL 예측, 시각화
- [ ] 우측 상단 통계 카드 6개 모두 숫자 표시 (총 데이터, 불량률, 온도, 압력, 습도, 사이클 시간)

### 1.2 차트 렌더링
- [ ] **시간대별 불량률** 선 그래프 정상 표시
- [ ] **라인별 불량률** 막대 그래프 3개 바 정상 표시

### 1.3 API 직접 확인

```bash
curl http://localhost:5001/api/v1/summary
curl http://localhost:5001/api/v1/lines
curl http://localhost:5001/api/v1/trends
```

응답에 `"status": "success"` 포함되어야 함.

---

## 2. 섹션별 테스트

### 2.1 대시보드 (Overview)
- [ ] F5 새로고침 후 통계 숫자가 모두 표시되는지 확인
- [ ] `마지막 업데이트` 시간이 현재 시간과 일치하는지 확인
- [ ] 불량률이 0~100% 사이 값인지 확인

### 2.2 설비 상태
- [ ] 좌측 메뉴 "설비 상태" 클릭
- [ ] 4개 설비(CNC_001, CNC_002, PRESS_001, ROBOT_001) 테이블에 표시
- [ ] 건강 점수, 상태 배지(양호/주의/경고) 정상 표시
- [ ] 알림 칼럼에 경고 메시지 있는 설비 확인 (예: CNC_002에 `[WARNING]` 있음)

### 2.3 데이터 분석
- [ ] "데이터 분석" 클릭
- [ ] **상관관계 매트릭스**: 6×6 히트맵 표시, 빨간색(양) / 파란색(음) 구분
- [ ] 히트맵 위에 마우스 호버 → 툴팁에 `temperature × pressure: 0.123` 형식 표시
- [ ] X축/Y축 레이블이 변수명(temperature, pressure...)으로 정확히 표시되는지 확인
- [ ] **온도-진동 분포 산점도**: 정상(초록) / 이상(빨강) 점 구분 표시

### 2.4 이상 탐지
- [ ] "이상 탐지" 클릭
- [ ] 상단 통계 3개 카드 표시 (총 데이터, 이상 데이터, 이상 비율)
- [ ] 하단 테이블에 이상 데이터 목록 표시
- [ ] `로딩 중...` 메시지가 잠깐 보였다가 사라지는지 확인

### 2.5 RUL 예측
- [ ] "RUL 예측" 클릭
- [ ] 4개 설비의 잔여 수명, 권장 정비일, 신뢰도 % 표시
- [ ] 건강 점수 옆에 상태 배지 표시

### 2.6 시각화
- [ ] "시각화" 클릭
- [ ] 4개 PNG 이미지(defect_analysis, time_series, correlation_matrix, dashboard_summary) 표시
- [ ] 이미지가 로딩되지 않으면 `python main.py` 먼저 실행하여 생성

---

## 3. 에러 상황 테스트

### 3.1 서버 중단 시
```bash
# 대시보드 실행 중 Ctrl+C로 종료 후 재접속
```
- [ ] 브라우저에서 페이지 새로고침 → 연결 거부 (정상)
- [ ] 서버 재시작 후 정상 복구

### 3.2 잘못된 경로 접근
- [ ] `http://localhost:5001/없는페이지` → Flask 404 페이지 표시

### 3.3 데이터 파일 삭제 후
```bash
# 대시보드 실행 중, data/manufacturing_data.csv 삭제
rm data/manufacturing_data.csv
python dashboard/app.py
```
- [ ] 대시보드가 자동으로 5000건 데이터를 새로 생성하는지 확인

---

## 4. 모바일 반응형 테스트

### 방법
브라우저 개발자 도구(F12) → 모바일 토글 버튼 클릭 (Ctrl+Shift+M)

### 체크리스트
- [ ] 화면 폭 768px 이하에서 사이드바가 기본적으로 숨겨지는지 확인
- [ ] 좌측 상단 ☰ 버튼 클릭 → 사이드바가 슬라이드되어 나타나는지 확인
- [ ] 사이드바가 열린 상태에서 배경(회색 오버레이) 클릭 → 닫히는지 확인
- [ ] 메뉴 항목 클릭 → 사이드바가 자동으로 닫히는지 확인
- [ ] 통계 카드가 2열 그리드로 변경되는지 확인
- [ ] 차트 영역이 전체 너비에 맞게 표시되는지 확인

---

## 5. 회귀 테스트 (변경 후 항상 실행)

```bash
pytest tests/test_dashboard.py -v
```

11개 테스트 모두 통과 확인:

```
tests/test_dashboard.py::TestDashboardAPI::test_index_page PASSED
tests/test_dashboard.py::TestDashboardAPI::test_api_summary PASSED
tests/test_dashboard.py::TestDashboardAPI::test_api_equipment PASSED
tests/test_dashboard.py::TestDashboardAPI::test_api_lines PASSED
tests/test_dashboard.py::TestDashboardAPI::test_api_trends PASSED
tests/test_dashboard.py::TestDashboardAPI::test_api_correlation PASSED
tests/test_dashboard.py::TestDashboardAPI::test_api_anomalies PASSED
tests/test_dashboard.py::TestDashboardAPI::test_api_scatter PASSED
tests/test_dashboard.py::TestDashboardAPI::test_api_rul PASSED
tests/test_dashboard.py::TestDashboardAPI::test_api_visualizations PASSED
tests/test_dashboard.py::TestDashboardAPI::test_serve_visualization PASSED
```

---

## 6. 최종 통합 확인

```bash
# 전체 프로젝트 검증
pytest -q           # 78 passed
python main.py      # 모든 단계 정상 완료
python dashboard/app.py 5001  # http://localhost:5001 접속 가능
```
