"""Cluster metadata models for semantic duplicate detection."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class LogCluster:
    """Represents a semantic duplicate cluster stored in Qdrant."""

    cluster_id: str
    representative_log: str
    occurrence_count: int = 1
    first_seen: str = ""
    last_seen: str = ""
    sample_logs: list[str] = field(default_factory=list)
    similarity_score_average: float = 0.0
    service_name: str | None = None
    cluster_summary: str = ""
    duplicate_reduction_percentage: float = 0.0
    visualization_metadata: dict[str, object] = field(default_factory=dict)
    cluster_label: str | None = None
    is_cluster: bool = True

    def to_payload(self) -> dict[str, object]:
        return {
            "cluster_id": self.cluster_id,
            "representative_log": self.representative_log,
            "occurrence_count": self.occurrence_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "sample_logs": self.sample_logs,
            "similarity_score_average": round(self.similarity_score_average, 4),
            "service_name": self.service_name,
            "cluster_summary": self.cluster_summary,
            "duplicate_reduction_percentage": round(self.duplicate_reduction_percentage, 2),
            "visualization_metadata": self.visualization_metadata,
            "cluster_label": self.cluster_label,
            "is_cluster": self.is_cluster,
        }


@dataclass(slots=True)
class ClusterDecision:
    """Outcome of the duplicate cluster assignment decision."""

    cluster_id: str | None
    is_duplicate: bool
    similarity_score: float
    cluster: LogCluster | None = None

    @property
    def occurrence_count(self) -> int:
        return self.cluster.occurrence_count if self.cluster else 0

    @property
    def representative_log(self) -> str | None:
        return self.cluster.representative_log if self.cluster else None

    @property
    def first_seen(self) -> str | None:
        return self.cluster.first_seen if self.cluster else None

    @property
    def last_seen(self) -> str | None:
        return self.cluster.last_seen if self.cluster else None

    @property
    def sample_logs(self) -> list[str]:
        return self.cluster.sample_logs if self.cluster else []

    @property
    def similarity_score_average(self) -> float:
        return self.cluster.similarity_score_average if self.cluster else 0.0

    @property
    def service_name(self) -> str | None:
        return self.cluster.service_name if self.cluster else None
