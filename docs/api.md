# API 문서

## 개요

Smart Manufacturing Dashboard API는 제조 공정 데이터를 분석하고 시각화하는 RESTful API입니다.

**Base URL**: `http://localhost:5001` (Docker: `http://localhost:5000`, 로컬 기본값 5001)

## 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/v1/summary` | 제조 공정 요약 통계 |
| GET | `/api/v1/lines` | 라인별 불량률 |
| GET | `/api/v1/trends` | 시간대별 불량률 추이 |
| GET | `/api/v1/correlation` | 변수 간 상관관계 매트릭스 |
| GET | `/api/v1/scatter` | 온도-진동 산점도 |
| GET | `/api/v1/equipment` | 설비 건강 상태 |
| GET | `/api/v1/anomalies` | 이상 탐지 결과 |
| GET | `/api/v1/rul` | 잔여 수명 예측 |
| GET | `/api/v1/visualizations` | 시각화 파일 목록 |
| GET | `/api/v1/drift` | 데이터 드리프트 감지 결과 |

### GET /api/v1/summary

제조 공정 요약 통계를 반환합니다.

**응답:**
```json
{
  "status": "success",
  "data": {
    "total_records": 5000,
    "defect_rate": 4.5,
    "avg_temperature": 27.5,
    "avg_pressure": 102.3,
    "avg_vibration": 0.52,
    "avg_humidity": 58.7,
    "avg_cycle_time": 32.1
  }
}
```

### GET /api/v1/equipment

설비 건강 상태를 반환합니다.

**응답:**
```json
{
  "status": "success",
  "data": [
    {
      "equipment_id": "CNC_001",
      "health_score": 85,
      "status": "양호",
      "alerts": []
    }
  ]
}
```

### GET /api/v1/rul

설비별 잔여 수명(RUL) 및 권장 정비일을 반환합니다.

**응답:**
```json
{
  "status": "success",
  "data": [
    {
      "equipment_id": "CNC_001",
      "name": "CNC 머시닝 센터 1",
      "health_score": 100,
      "status": "양호",
      "remaining_hours": 77,
      "recommended_maintenance_date": "2026-06-18",
      "reliability_score": 100.0,
      "confidence": 0.85,
      "model": "lognormal_reliability",
      "alerts": []
    }
  ]
}
```

### GET /api/v1/lines

라인별 불량률을 반환합니다.

**응답:**
```json
{
  "status": "success",
  "data": [
    {
      "line": "Line_A",
      "defect_rate": 4.2,
      "count": 1650
    }
  ]
}
```

### GET /api/v1/trends

시간대별 불량률 및 온도 추이를 반환합니다.

**응답:**
```json
{
  "status": "success",
  "data": {
    "hours": [0, 1, 2, ...],
    "defect_rates": [3.5, 4.2, ...],
    "temperatures": [25.3, 24.8, ...]
  }
}
```

### GET /api/v1/correlation

변수 간 상관관계 매트릭스를 반환합니다.

**응답:**
```json
{
  "status": "success",
  "data": {
    "columns": ["temperature", "pressure", "vibration", ...],
    "matrix": [[1.0, 0.2, ...], ...]
  }
}
```

### GET /api/v1/scatter

온도-진동 산점도 데이터를 반환합니다. 정상 데이터는 최대 200개로 샘플링됩니다.

**응답:**
```json
{
  "status": "success",
  "data": {
    "normal": [{"x": 27.5, "y": 0.5}, {"x": 28.1, "y": 0.6}, ...],
    "anomaly": [{"x": 35.2, "y": 0.9}, ...]
  }
}
```

### GET /api/v1/anomalies

이상 탐지 결과를 반환합니다.

**응답:**
```json
{
  "status": "success",
  "data": {
    "summary": {
      "total_records": 5000,
      "anomaly_count": 250,
      "anomaly_rate": 5.0
    },
    "top_anomalies": [...]
  }
}
```

### GET /api/v1/visualizations

`visualizations/` 디렉터리에 있는 PNG 파일 목록을 반환합니다.

**응답:**
```json
{
  "status": "success",
  "data": ["correlation_matrix.png", "dashboard_summary.png", ...]
}
```

### GET /visualizations/<filename>

지정한 시각화 PNG 이미지를 반환합니다.

**예시:** `GET /visualizations/correlation_matrix.png`

**응답:** `image/png`

## 에러 응답

모든 에러 응답은 다음 형식을 따릅니다:

```json
{
  "status": "error",
  "message": "에러 메시지"
}
```

HTTP 상태 코드:
- `200`: 성공
- `500`: 서버 에러
