from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

from anomaly.ml_detector import detector_engine, AnomalyScore

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])


class AnomalyScoreResponse(BaseModel):
    service_id: str
    timestamp: datetime
    score: float
    is_anomaly: bool
    reason: str
    severity: str
    features: Dict[str, float]
    historical_baseline: Optional[float] = None


class DetectionStatistics(BaseModel):
    service_id: str
    total_analyzed: int
    anomalies_detected: int
    anomaly_rate: float
    detection_reasons: Dict[str, int]
    avg_anomaly_score: float


class TrainingRequest(BaseModel):
    service_id: str
    logs: List[Dict[str, Any]]


class AnalyzeLogRequest(BaseModel):
    service_id: str
    log_level: str
    message: str
    vector_score: Optional[float] = None


@router.post("/analyze", response_model=AnomalyScoreResponse)
async def analyze_log(request: AnalyzeLogRequest) -> AnomalyScoreResponse:
    anomaly_score = detector_engine.analyze_log(
        service_id=request.service_id,
        log_level=request.log_level,
        message=request.message,
        anomaly_score_from_vector=request.vector_score,
    )

    return AnomalyScoreResponse(
        service_id=anomaly_score.service_id,
        timestamp=anomaly_score.timestamp,
        score=anomaly_score.score,
        is_anomaly=anomaly_score.is_anomaly,
        reason=anomaly_score.reason,
        severity=anomaly_score.severity,
        features=anomaly_score.features,
        historical_baseline=anomaly_score.historical_baseline,
    )


@router.get("/history/{service_id}", response_model=List[AnomalyScoreResponse])
async def get_anomaly_history(
    service_id: str,
    limit: int = Query(100, ge=1, le=1000),
) -> List[AnomalyScoreResponse]:
    anomalies = detector_engine.get_anomaly_history(
        service_id=service_id, limit=limit
    )

    return [
        AnomalyScoreResponse(
            service_id=a.service_id,
            timestamp=a.timestamp,
            score=a.score,
            is_anomaly=a.is_anomaly,
            reason=a.reason,
            severity=a.severity,
            features=a.features,
            historical_baseline=a.historical_baseline,
        )
        for a in anomalies
    ]


@router.get("/statistics/{service_id}", response_model=DetectionStatistics)
async def get_detection_statistics(service_id: str) -> DetectionStatistics:
    stats = detector_engine.get_statistics(service_id)

    return DetectionStatistics(
        service_id=service_id,
        total_analyzed=stats["total_analyzed"],
        anomalies_detected=stats["anomalies_detected"],
        anomaly_rate=stats["anomaly_rate"],
        detection_reasons=stats["detection_reasons"],
        avg_anomaly_score=stats["avg_anomaly_score"],
    )


@router.post("/train")
async def train_baseline(request: TrainingRequest) -> Dict[str, str]:
    if not request.logs:
        raise HTTPException(
            status_code=400,
            detail="Training logs cannot be empty",
        )

    if len(request.logs) < 100:
        raise HTTPException(
            status_code=400,
            detail="Minimum 100 logs required for training",
        )

    try:
        detector_engine.train_on_baseline(
            service_id=request.service_id,
            logs=request.logs,
        )

        return {
            "message": f"Baseline trained for {request.service_id}",
            "logs_used": str(len(request.logs)),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Training failed: {str(e)}",
        )


@router.get("/alerts/{service_id}")
async def get_recent_anomalies(
    service_id: str,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
) -> List[AnomalyScoreResponse]:
    anomalies = detector_engine.get_anomaly_history(
        service_id=service_id, limit=limit
    )

    filtered_anomalies = [a for a in anomalies if a.is_anomaly]

    if severity:
        filtered_anomalies = [
            a for a in filtered_anomalies if a.severity == severity
        ]

    return [
        AnomalyScoreResponse(
            service_id=a.service_id,
            timestamp=a.timestamp,
            score=a.score,
            is_anomaly=a.is_anomaly,
            reason=a.reason,
            severity=a.severity,
            features=a.features,
            historical_baseline=a.historical_baseline,
        )
        for a in filtered_anomalies
    ]


@router.post("/cleanup")
async def cleanup_detector_data() -> Dict[str, str]:
    detector_engine.pattern_analyzer.cleanup_old_data()

    return {"message": "Old anomaly detection data cleaned up"}


@router.get("/health")
async def anomaly_detection_health() -> Dict[str, Any]:
    total_services = len(detector_engine.anomaly_history)

    return {
        "status": "healthy",
        "services_monitored": total_services,
        "detector_models": {
            "statistical": "active",
            "behavioral": "active",
            "pattern": "active",
        },
    }


@router.get("/summary")
async def get_anomaly_summary() -> Dict[str, Any]:
    summary = {}

    for service_id in detector_engine.anomaly_history.keys():
        stats = detector_engine.get_statistics(service_id)
        summary[service_id] = {
            "anomalies_detected": stats["anomalies_detected"],
            "anomaly_rate": stats["anomaly_rate"],
            "avg_score": stats["avg_anomaly_score"],
            "top_reasons": dict(
                sorted(
                    stats["detection_reasons"].items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:3]
            ),
        }

    return {
        "timestamp": datetime.now().isoformat(),
        "total_services": len(summary),
        "services": summary,
    }
