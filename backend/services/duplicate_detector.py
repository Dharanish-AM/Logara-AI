"""Semantic duplicate clustering service for log ingestion."""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

try:
    from qdrant_client.models import PointStruct
except ImportError:  # pragma: no cover
    @dataclass
    class PointStruct:
        id: Any
        vector: Any
        payload: dict[str, Any]

from models.log_cluster import ClusterDecision, LogCluster
from services.vector_store import build_payload_filter
from utils.similarity import normalize_log_text, normalize_vector

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "the",
    "to",
    "with",
    "while",
    "error",
    "warn",
    "warning",
    "critical",
    "info",
    "database",
    "timeout",
}


class DuplicateClusteringService:
    """Assigns logs to semantic clusters based on vector similarity."""

    def __init__(
        self,
        qdrant_client: Any,
        similarity_threshold: float = 0.92,
        max_cluster_sample_size: int = 5,
        enable_duplicate_clustering: bool = True,
        logs_collection: str = "logs",
        clusters_collection: str = "log_clusters",
    ) -> None:
        self.qdrant_client = qdrant_client
        self.similarity_threshold = float(similarity_threshold)
        self.max_cluster_sample_size = max(1, int(max_cluster_sample_size))
        self.enable_duplicate_clustering = bool(enable_duplicate_clustering)
        self.logs_collection = logs_collection
        self.clusters_collection = clusters_collection

    def assign_to_cluster(
        self,
        log_text: str,
        embedding: list[float],
        service_id: str,
        service_name: str | None = None,
        timestamp: str | None = None,
        log_source: str | None = None,
    ) -> ClusterDecision:
        """Assign a log to an existing cluster or create a new cluster.

        `service_id` is required. It is used to scope the Qdrant cluster
        search so that a log from one service can never be matched against
        an existing cluster belonging to a different service, matching the
        same scoping guarantee documented in
        docs/service-scoped-vector-search.md and already enforced for
        `/search` via `build_payload_filter()`.
        """
        if not self.enable_duplicate_clustering or self.qdrant_client is None:
            return ClusterDecision(cluster_id=None, is_duplicate=False, similarity_score=0.0)

        if not log_text or not str(log_text).strip():
            return ClusterDecision(cluster_id=None, is_duplicate=False, similarity_score=0.0)

        if not service_id or not str(service_id).strip():
            logger.warning(
                "assign_to_cluster called without a service_id; refusing to run "
                "an unscoped Qdrant cluster search"
            )
            return ClusterDecision(cluster_id=None, is_duplicate=False, similarity_score=0.0)

        normalized_embedding = normalize_vector(embedding)
        if not normalized_embedding:
            return ClusterDecision(cluster_id=None, is_duplicate=False, similarity_score=0.0)

        timestamp_value = timestamp or self._utc_timestamp()
        search_result = self._search_cluster(normalized_embedding, service_id)
        if not search_result:
            cluster = self._create_cluster(
                log_text=log_text,
                service_id=service_id,
                service_name=service_name,
                timestamp=timestamp_value,
                log_source=log_source,
            )
            self._enrich_cluster(cluster)
            self._upsert_cluster(cluster, normalized_embedding)
            logger.info(
                "Created new semantic cluster | cluster_id=%s | similarity_score=0.0",
                cluster.cluster_id,
            )
            return ClusterDecision(
                cluster_id=cluster.cluster_id,
                is_duplicate=False,
                similarity_score=0.0,
                cluster=cluster,
            )

        hit = search_result[0]
        score = float(getattr(hit, "score", 0.0) or 0.0)
        payload = getattr(hit, "payload", None)

        if not isinstance(payload, dict):
            cluster = self._create_cluster(
                log_text=log_text,
                service_id=service_id,
                service_name=service_name,
                timestamp=timestamp_value,
                log_source=log_source,
            )
            self._enrich_cluster(cluster)
            self._upsert_cluster(cluster, normalized_embedding)
            return ClusterDecision(
                cluster_id=cluster.cluster_id,
                is_duplicate=False,
                similarity_score=0.0,
                cluster=cluster,
            )

        if score < self.similarity_threshold:
            cluster = self._create_cluster(
                log_text=log_text,
                service_id=service_id,
                service_name=service_name,
                timestamp=timestamp_value,
                log_source=log_source,
            )
            self._enrich_cluster(cluster)
            self._upsert_cluster(cluster, normalized_embedding)
            logger.info(
                "New semantic cluster created | cluster_id=%s | similarity_score=%.4f",
                cluster.cluster_id,
                score,
            )
            return ClusterDecision(
                cluster_id=cluster.cluster_id,
                is_duplicate=False,
                similarity_score=score,
                cluster=cluster,
            )

        cluster = LogCluster(
            cluster_id=str(payload.get("cluster_id") or uuid.uuid4().hex),
            representative_log=str(payload.get("representative_log") or log_text),
            occurrence_count=int(payload.get("occurrence_count") or 1),
            first_seen=str(payload.get("first_seen") or timestamp_value),
            last_seen=str(payload.get("last_seen") or timestamp_value),
            sample_logs=[str(item) for item in payload.get("sample_logs") or []],
            similarity_score_average=float(payload.get("similarity_score_average") or score),
            service_id=str(payload.get("service_id") or service_id),
            service_name=payload.get("service_name") or service_name,
            cluster_summary=str(payload.get("cluster_summary") or ""),
            duplicate_reduction_percentage=float(payload.get("duplicate_reduction_percentage") or 0.0),
            visualization_metadata=dict(payload.get("visualization_metadata") or {}),
            cluster_label=str(payload.get("cluster_label") or None),
        )

        updated_cluster = self._update_cluster(cluster, log_text, score, timestamp_value, service_name)
        self._enrich_cluster(updated_cluster)
        self._upsert_cluster(updated_cluster, normalized_embedding)
        logger.info(
            "Matched existing cluster | cluster_id=%s | similarity_score=%.4f",
            updated_cluster.cluster_id,
            score,
        )

        return ClusterDecision(
            cluster_id=updated_cluster.cluster_id,
            is_duplicate=True,
            similarity_score=score,
            cluster=updated_cluster,
        )

    def generate_cluster_summary(self, cluster: LogCluster) -> str:
        """Create a readable summary that is suitable for dashboards and AI prompts."""
        text = normalize_log_text(cluster.representative_log)
        if not text:
            return "Unclassified cluster"

        cleaned = re.sub(r"^(error|warn|warning|critical|info)\s*[:\-\s]*", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:0x)?[a-f0-9]{6,}\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b\d+\b", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        if not cleaned:
            return text[:160]

        severity = self._infer_severity(text)
        prefix = {
            "critical": "Critical cluster",
            "error": "Error cluster",
            "warn": "Warning cluster",
            "info": "Info cluster",
        }.get(severity, "Operational cluster")
        return f"{prefix}: {cleaned[:120]}"

    def build_visualization_metadata(self, cluster: LogCluster) -> dict[str, Any]:
        """Build dashboard-friendly metadata for a semantic cluster."""
        text = normalize_log_text(cluster.representative_log).lower()
        severity = self._infer_severity(text)
        status = "duplicate" if cluster.occurrence_count > 1 else "new"
        return {
            "status": status,
            "severity": severity,
            "service_id": cluster.service_id,
            "service_name": cluster.service_name,
            "occurrence_count": cluster.occurrence_count,
            "cluster_label": self._cluster_label(cluster),
            "sample_count": len(cluster.sample_logs),
        }

    def build_cluster_statistics(
        self,
        cluster: LogCluster,
        total_logs: int = 0,
    ) -> dict[str, Any]:
        """Return dashboard-ready cluster statistics for UI or API consumers."""
        duplicate_reduction_percentage = self.calculate_duplicate_reduction_percentage(
            cluster.occurrence_count,
            total_logs,
        )
        visualization_metadata = self.build_visualization_metadata(cluster)
        cluster.cluster_summary = self.generate_cluster_summary(cluster)
        cluster.visualization_metadata = visualization_metadata
        cluster.duplicate_reduction_percentage = duplicate_reduction_percentage
        cluster.cluster_label = visualization_metadata.get("cluster_label")

        return {
            "cluster_id": cluster.cluster_id,
            "representative_log": cluster.representative_log,
            "cluster_summary": cluster.cluster_summary,
            "occurrence_count": cluster.occurrence_count,
            "first_seen": cluster.first_seen,
            "last_seen": cluster.last_seen,
            "sample_logs": list(cluster.sample_logs),
            "sample_count": len(cluster.sample_logs),
            "similarity_score_average": round(cluster.similarity_score_average, 4),
            "service_id": cluster.service_id,
            "service_name": cluster.service_name,
            "duplicate_reduction_percentage": round(duplicate_reduction_percentage, 2),
            "visualization_metadata": visualization_metadata,
            "cluster_label": visualization_metadata.get("cluster_label"),
        }

    def calculate_duplicate_reduction_percentage(
        self,
        occurrence_count: int,
        total_logs: int,
    ) -> float:
        """Estimate how much duplicate volume this cluster represents."""
        if total_logs <= 0 or occurrence_count <= 1:
            return 0.0

        ratio = min(100.0, ((occurrence_count - 1) / total_logs) * 100.0)
        return round(ratio, 2)

    def _search_cluster(self, embedding: list[float], service_id: str) -> list[Any] | None:
        try:
            query_filter = build_payload_filter(service_id=service_id)
        except Exception:
            logger.exception(
                "Failed to build service-scoped Qdrant filter for service_id=%s; "
                "skipping cluster search rather than searching unscoped",
                service_id,
            )
            return None

        try:
            result = self.qdrant_client.search(
                collection_name=self.clusters_collection,
                query_vector=embedding,
                query_filter=query_filter,
                limit=1,
                with_payload=True,
            )
        except TypeError:
            result = self.qdrant_client.search(
                collection_name=self.clusters_collection,
                query_vector=embedding,
                query_filter=query_filter,
                limit=1,
                with_payload=True,
                score_threshold=0.0,
            )

        if not isinstance(result, (list, tuple)) or not result:
            return None

        return [hit for hit in result if hasattr(hit, "payload")]

    def _create_cluster(
        self,
        log_text: str,
        service_id: str,
        service_name: str | None,
        timestamp: str,
        log_source: str | None = None,
    ) -> LogCluster:
        representative = str(log_text).strip() or log_source or "unknown log"
        return LogCluster(
            cluster_id=f"cluster-{uuid.uuid4().hex}",
            representative_log=representative,
            occurrence_count=1,
            first_seen=timestamp,
            last_seen=timestamp,
            sample_logs=[representative],
            similarity_score_average=0.0,
            service_id=service_id,
            service_name=service_name,
        )

    def _update_cluster(
        self,
        cluster: LogCluster,
        log_text: str,
        similarity_score: float,
        timestamp: str,
        service_name: str | None,
    ) -> LogCluster:
        cluster.last_seen = timestamp
        cluster.occurrence_count += 1
        cluster.similarity_score_average = (
            (cluster.similarity_score_average * (cluster.occurrence_count - 1)) + similarity_score
        ) / cluster.occurrence_count

        if service_name and not cluster.service_name:
            cluster.service_name = service_name

        sample_logs = list(cluster.sample_logs)
        representative = str(log_text).strip() or cluster.representative_log
        if representative not in sample_logs:
            sample_logs.insert(0, representative)

        cluster.sample_logs = sample_logs[: self.max_cluster_sample_size]
        return cluster

    def _enrich_cluster(self, cluster: LogCluster) -> None:
        cluster.cluster_summary = self.generate_cluster_summary(cluster)
        cluster.visualization_metadata = self.build_visualization_metadata(cluster)
        cluster.cluster_label = cluster.visualization_metadata.get("cluster_label")
        cluster.duplicate_reduction_percentage = self.calculate_duplicate_reduction_percentage(
            cluster.occurrence_count,
            0,
        )

    def _upsert_cluster(self, cluster: LogCluster, embedding: list[float]) -> None:
        payload = cluster.to_payload()
        point = PointStruct(id=cluster.cluster_id, vector=embedding, payload=payload)
        self.qdrant_client.upsert(collection_name=self.clusters_collection, points=[point])

    @staticmethod
    def _utc_timestamp() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _infer_severity(text: str) -> str:
        lowered = text.lower()
        if "critical" in lowered or "fatal" in lowered:
            return "critical"
        if "error" in lowered or "exception" in lowered or "failure" in lowered:
            return "error"
        if "warn" in lowered or "warning" in lowered or "rate limit" in lowered:
            return "warn"
        return "info"

    @staticmethod
    def _cluster_label(cluster: LogCluster) -> str:
        if cluster.service_name:
            return f"{cluster.service_name}:{cluster.cluster_id}"
        return cluster.cluster_id