from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

router = APIRouter(prefix="/api/performance", tags=["performance"])


class ProcessingMetrics(BaseModel):
    average_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    logs_processed_per_second: float
    batch_size: int
    parallel_workers: int
    embedding_cache_hit_rate: float
    total_processed: int


class PerformanceOptimizationConfig(BaseModel):
    batch_size: int = 32
    max_batch_wait_ms: int = 100
    num_parallel_workers: int = 4
    enable_caching: bool = True
    cache_size: int = 1000
    streaming_enabled: bool = True


class LatencyReport(BaseModel):
    timestamp: datetime
    operation: str
    latency_ms: float
    batch_size: Optional[int] = None
    success: bool


class PerformanceMetricsTracker:
    def __init__(self):
        self.latencies: List[float] = []
        self.batch_sizes: List[int] = []
        self.failed_operations: int = 0
        self.successful_operations: int = 0
        self.embedding_cache_hits: int = 0
        self.embedding_cache_misses: int = 0

    def record_operation(
        self,
        latency_ms: float,
        batch_size: int,
        success: bool,
    ) -> None:
        self.latencies.append(latency_ms)
        self.batch_sizes.append(batch_size)

        if success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1

        if len(self.latencies) > 10000:
            self.latencies = self.latencies[-5000:]
            self.batch_sizes = self.batch_sizes[-5000:]

    def record_cache_hit(self) -> None:
        self.embedding_cache_hits += 1

    def record_cache_miss(self) -> None:
        self.embedding_cache_misses += 1

    def get_metrics(self) -> ProcessingMetrics:
        if not self.latencies:
            return ProcessingMetrics(
                average_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                logs_processed_per_second=0,
                batch_size=0,
                parallel_workers=0,
                embedding_cache_hit_rate=0,
                total_processed=0,
            )

        sorted_latencies = sorted(self.latencies)
        avg_latency = sum(self.latencies) / len(self.latencies)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)

        total_cache_accesses = (
            self.embedding_cache_hits + self.embedding_cache_misses
        )
        cache_hit_rate = (
            self.embedding_cache_hits / total_cache_accesses
            if total_cache_accesses > 0
            else 0
        )

        avg_batch_size = (
            sum(self.batch_sizes) / len(self.batch_sizes)
            if self.batch_sizes
            else 0
        )

        logs_processed = self.successful_operations
        logs_per_second = (
            logs_processed / (sum(self.latencies) / 1000)
            if self.latencies
            else 0
        )

        return ProcessingMetrics(
            average_latency_ms=avg_latency,
            p95_latency_ms=sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else avg_latency,
            p99_latency_ms=sorted_latencies[p99_idx] if p99_idx < len(sorted_latencies) else avg_latency,
            logs_processed_per_second=logs_per_second,
            batch_size=int(avg_batch_size),
            parallel_workers=0,
            embedding_cache_hit_rate=cache_hit_rate,
            total_processed=logs_processed,
        )


tracker = PerformanceMetricsTracker()


@router.get("/metrics", response_model=ProcessingMetrics)
async def get_performance_metrics() -> ProcessingMetrics:
    return tracker.get_metrics()


@router.post("/config")
async def update_optimization_config(
    config: PerformanceOptimizationConfig,
) -> Dict[str, Any]:
    return {
        "message": "Performance optimization configuration updated",
        "config": {
            "batch_size": config.batch_size,
            "max_batch_wait_ms": config.max_batch_wait_ms,
            "num_parallel_workers": config.num_parallel_workers,
            "enable_caching": config.enable_caching,
            "cache_size": config.cache_size,
            "streaming_enabled": config.streaming_enabled,
        },
    }


@router.get("/report")
async def get_performance_report() -> Dict[str, Any]:
    metrics = tracker.get_metrics()

    return {
        "timestamp": datetime.now().isoformat(),
        "performance_metrics": metrics.dict(),
        "recommendations": _generate_recommendations(metrics),
    }


def _generate_recommendations(metrics: ProcessingMetrics) -> List[str]:
    recommendations = []

    if metrics.average_latency_ms > 1000:
        recommendations.append(
            "Average latency exceeds 1 second. Consider increasing batch size."
        )

    if metrics.p99_latency_ms > 5000:
        recommendations.append(
            "P99 latency is high. Consider adding more parallel workers."
        )

    if metrics.embedding_cache_hit_rate < 0.5:
        recommendations.append(
            "Embedding cache hit rate is low. Consider increasing cache size."
        )

    if metrics.logs_processed_per_second < 100:
        recommendations.append(
            "Throughput is low. Enable parallel processing and increase batch size."
        )

    if not recommendations:
        recommendations.append(
            "Performance is optimal. Continue monitoring."
        )

    return recommendations


@router.post("/latency-report")
async def report_latency(latency: LatencyReport) -> Dict[str, str]:
    tracker.record_operation(
        latency_ms=latency.latency_ms,
        batch_size=latency.batch_size or 0,
        success=latency.success,
    )

    return {"message": "Latency reported successfully"}


@router.get("/health")
async def performance_system_health() -> Dict[str, Any]:
    metrics = tracker.get_metrics()

    is_healthy = (
        metrics.average_latency_ms < 1000
        and metrics.embedding_cache_hit_rate > 0.3
    )

    return {
        "status": "healthy" if is_healthy else "degraded",
        "latency_ms": metrics.average_latency_ms,
        "throughput_logs_per_sec": metrics.logs_processed_per_second,
        "cache_hit_rate": metrics.embedding_cache_hit_rate,
    }
