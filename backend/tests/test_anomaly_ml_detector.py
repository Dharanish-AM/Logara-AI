"""
Tests for the ML-based anomaly detection engine (anomaly/ml_detector.py)
and its REST API (routes/anomalies.py).
"""

import pytest
from fastapi.testclient import TestClient

from anomaly.ml_detector import (
    BehavioralAnomalyDetector,
    LogPatternAnalyzer,
    MLAnomalyDetectionEngine,
)
from app_factory import create_app


@pytest.fixture
def engine():
    return MLAnomalyDetectionEngine()


@pytest.fixture
def client():
    return TestClient(create_app())


class TestLogPatternAnalyzer:
    def test_error_rate_starts_at_zero_for_unseen_service(self):
        analyzer = LogPatternAnalyzer()
        assert analyzer.get_error_rate("unseen-service") == 0.0

    def test_error_rate_reflects_recent_error_logs(self):
        analyzer = LogPatternAnalyzer()
        for _ in range(5):
            analyzer.update_pattern("svc", "INFO", "all good")
        for _ in range(5):
            analyzer.update_pattern("svc", "ERROR", "boom")

        assert analyzer.get_error_rate("svc") == pytest.approx(0.5)

    def test_pattern_frequency_tracks_repeated_messages(self):
        analyzer = LogPatternAnalyzer()
        for _ in range(3):
            analyzer.update_pattern("svc", "INFO", "request handled ok")
        analyzer.update_pattern("svc", "INFO", "totally different message")

        frequency = analyzer.get_pattern_frequency("svc", "request handled ok")
        assert frequency == pytest.approx(0.75)


class TestBehavioralAnomalyDetector:
    def test_first_observation_is_treated_as_learning(self):
        detector = BehavioralAnomalyDetector()
        is_anomaly, reason, score = detector.detect_behavior_change(
            "svc", current_error_rate=0.1, current_message_distribution={}
        )
        assert is_anomaly is False
        assert reason == "learning"

    def test_large_error_rate_deviation_is_flagged(self):
        detector = BehavioralAnomalyDetector()
        detector.detect_behavior_change("svc", 0.05, {})
        for _ in range(10):
            detector.detect_behavior_change("svc", 0.05, {})

        is_anomaly, reason, score = detector.detect_behavior_change(
            "svc", current_error_rate=0.9, current_message_distribution={}
        )
        assert is_anomaly is True
        assert reason == "error_rate_spike"
        assert 0.0 < score <= 1.0


class TestMLAnomalyDetectionEngine:
    def test_normal_log_is_not_flagged(self, engine):
        result = engine.analyze_log("svc", "INFO", "request completed")
        assert result.is_anomaly is False
        assert result.severity == "info"

    def test_sustained_error_burst_is_flagged_as_critical(self, engine):
        result = None
        for i in range(20):
            result = engine.analyze_log("svc", "ERROR", f"failure {i}")

        assert result.is_anomaly is True
        assert result.reason == "critical_error_spike"
        assert result.severity == "critical"

    def test_history_and_statistics_track_analyzed_logs(self, engine):
        engine.analyze_log("svc", "INFO", "ok")
        engine.analyze_log("svc", "INFO", "ok again")

        history = engine.get_anomaly_history("svc")
        assert len(history) == 2

        stats = engine.get_statistics("svc")
        assert stats["total_analyzed"] == 2
        assert stats["anomalies_detected"] == 0

    def test_statistics_for_unseen_service_do_not_error(self, engine):
        stats = engine.get_statistics("never-seen")
        assert stats["total_analyzed"] == 0
        assert stats["anomaly_rate"] == 0

    def test_train_on_baseline_does_not_raise(self, engine):
        logs = [{"level": "ERROR" if i % 10 == 0 else "INFO"} for i in range(200)]
        engine.train_on_baseline("svc", logs)


class TestAnomalyApi:
    def test_analyze_endpoint_returns_score(self, client):
        response = client.post(
            "/api/anomalies/analyze",
            json={
                "service_id": "checkout",
                "log_level": "INFO",
                "message": "order placed",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["service_id"] == "checkout"
        assert body["is_anomaly"] is False

    def test_history_endpoint_returns_prior_analyses(self, client):
        client.post(
            "/api/anomalies/analyze",
            json={
                "service_id": "billing",
                "log_level": "INFO",
                "message": "invoice generated",
            },
        )
        response = client.get("/api/anomalies/history/billing")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_train_endpoint_rejects_too_few_logs(self, client):
        response = client.post(
            "/api/anomalies/train",
            json={"service_id": "svc", "logs": [{"level": "INFO"}] * 10},
        )
        assert response.status_code == 400

    def test_train_endpoint_accepts_sufficient_logs(self, client):
        logs = [{"level": "INFO"}] * 150
        response = client.post(
            "/api/anomalies/train",
            json={"service_id": "svc", "logs": logs},
        )
        assert response.status_code == 200
        assert response.json()["logs_used"] == "150"
