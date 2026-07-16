import logging
from unittest.mock import MagicMock

from services.duplicate_detector import DuplicateClusteringService


class DummyHit:
    def __init__(self, score, payload):
        self.score = score
        self.payload = payload


def make_service(mock_client):
    service = DuplicateClusteringService(
        qdrant_client=mock_client,
        similarity_threshold=0.92,
        max_cluster_sample_size=3,
        enable_duplicate_clustering=True,
        logs_collection="logs",
        clusters_collection="log_clusters",
    )
    return service


def test_detect_duplicate_updates_existing_cluster(caplog):
    caplog.set_level(logging.INFO)

    mock_client = MagicMock()
    mock_client.search.return_value = [
        DummyHit(
            0.95,
            {
                "cluster_id": "cluster-123",
                "representative_log": "ERROR: Database timeout for user 123",
                "occurrence_count": 2,
                "first_seen": "2026-05-20T10:00:00Z",
                "last_seen": "2026-05-21T10:00:00Z",
                "sample_logs": [
                    "ERROR: Database timeout for user 123",
                    "ERROR: Database timeout for user 456",
                ],
                "similarity_score_average": 0.94,
                "service_name": "payments-service",
            },
        )
    ]

    service = make_service(mock_client)

    decision = service.assign_to_cluster(
        log_text="ERROR: Database timeout for user 789",
        embedding=[0.1] * 384,
        service_id="payments-service",
        service_name="payments-service",
        timestamp="2026-05-22T10:00:00Z",
    )

    assert decision.cluster_id == "cluster-123"
    assert decision.is_duplicate is True
    assert decision.similarity_score == 0.95
    mock_client.upsert.assert_called_once()
    assert "Matched existing cluster" in caplog.text


def test_detect_duplicate_creates_new_cluster_when_below_threshold():
    mock_client = MagicMock()
    mock_client.search.return_value = [
        DummyHit(
            0.34,
            {
                "cluster_id": "cluster-999",
                "representative_log": "Redis connection failed",
                "occurrence_count": 1,
                "first_seen": "2026-05-20T10:00:00Z",
                "last_seen": "2026-05-20T10:00:00Z",
                "sample_logs": ["Redis connection failed"],
                "similarity_score_average": 0.34,
                "service_name": "cache-service",
            },
        )
    ]

    service = make_service(mock_client)

    decision = service.assign_to_cluster(
        log_text="Disk pressure observed in volume /var/log",
        embedding=[0.2] * 384,
        service_id="storage-service",
        service_name="storage-service",
        timestamp="2026-05-22T10:00:00Z",
    )

    assert decision.cluster_id is not None
    assert decision.is_duplicate is False
    assert decision.similarity_score == 0.34
    assert mock_client.upsert.call_count == 1


def test_assign_to_cluster_returns_noop_when_disabled():
    mock_client = MagicMock()
    service = DuplicateClusteringService(
        qdrant_client=mock_client,
        similarity_threshold=0.92,
        max_cluster_sample_size=3,
        enable_duplicate_clustering=False,
        logs_collection="logs",
        clusters_collection="log_clusters",
    )

    decision = service.assign_to_cluster(
        log_text="ERROR: Database timeout for user 789",
        embedding=[0.1] * 384,
        service_id="payments-service",
        service_name="payments-service",
        timestamp="2026-05-22T10:00:00Z",
    )

    assert decision.cluster_id is None
    assert decision.is_duplicate is False
    assert mock_client.search.call_count == 0


def test_generate_cluster_summary_and_dashboard_metrics():
    service = make_service(MagicMock())

    cluster = service._create_cluster(
        log_text="ERROR: Database timeout for user 123",
        service_id="payments-service",
        service_name="payments-service",
        timestamp="2026-05-22T10:00:00Z",
    )

    summary = service.generate_cluster_summary(cluster)
    metrics = service.build_cluster_statistics(cluster, total_logs=10)

    assert "database timeout" in summary.lower()
    assert metrics["cluster_id"] == cluster.cluster_id
    assert metrics["occurrence_count"] == cluster.occurrence_count
    assert metrics["duplicate_reduction_percentage"] == 0.0
    assert metrics["visualization_metadata"]["status"] == "new"
    assert metrics["visualization_metadata"]["severity"] == "error"


def test_duplicate_reduction_percentage_reflects_repeated_duplicates():
    service = make_service(MagicMock())
    cluster = service._create_cluster(
        log_text="ERROR: Database timeout for user 123",
        service_id="payments-service",
        service_name="payments-service",
        timestamp="2026-05-22T10:00:00Z",
    )

    cluster = service._update_cluster(
        cluster,
        log_text="ERROR: Database timeout for user 456",
        similarity_score=0.95,
        timestamp="2026-05-22T10:01:00Z",
        service_name="payments-service",
    )
    cluster = service._update_cluster(
        cluster,
        log_text="ERROR: Database timeout for user 789",
        similarity_score=0.96,
        timestamp="2026-05-22T10:02:00Z",
        service_name="payments-service",
    )

    metrics = service.build_cluster_statistics(cluster, total_logs=10)

    assert cluster.occurrence_count == 3
    assert metrics["duplicate_reduction_percentage"] == 20.0


def test_duplicate_reduction_percentage_handles_zero_logs():
    service = make_service(MagicMock())
    cluster = service._create_cluster(
        log_text="WARN: Rate limit approaching",
        service_id="api-service",
        service_name="api-service",
        timestamp="2026-05-22T10:00:00Z",
    )

    metrics = service.build_cluster_statistics(cluster, total_logs=0)

    assert metrics["duplicate_reduction_percentage"] == 0.0
