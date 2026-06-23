import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


@dataclass
class AnomalyScore:
    service_id: str
    timestamp: datetime
    score: float
    is_anomaly: bool
    reason: str
    severity: str
    features: Dict[str, float] = field(default_factory=dict)
    historical_baseline: Optional[float] = None


class LogPatternAnalyzer:
    def __init__(self, window_size_minutes: int = 60):
        self.window_size_minutes = window_size_minutes
        self.error_rate_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.message_patterns: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.service_metrics: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )

    def update_pattern(
        self, service_id: str, log_level: str, message: str
    ) -> None:
        pattern_key = self._extract_pattern(message)
        self.message_patterns[service_id][pattern_key] += 1

        if log_level == "ERROR":
            self.service_metrics[service_id]["error_count"].append(1)
        else:
            self.service_metrics[service_id]["error_count"].append(0)

    def get_error_rate(self, service_id: str) -> float:
        if service_id not in self.service_metrics:
            return 0.0

        error_counts = self.service_metrics[service_id]["error_count"]
        if not error_counts:
            return 0.0

        recent_errors = error_counts[-100:]
        return sum(recent_errors) / len(recent_errors)

    def get_pattern_frequency(
        self, service_id: str, pattern: str
    ) -> float:
        if service_id not in self.message_patterns:
            return 0.0

        total = sum(self.message_patterns[service_id].values())
        if total == 0:
            return 0.0

        return self.message_patterns[service_id][pattern] / total

    def _extract_pattern(self, message: str) -> str:
        words = message.split()
        if len(words) > 3:
            return " ".join(words[:3])
        return message[:50]

    def cleanup_old_data(self) -> None:
        cutoff_time = datetime.now() - timedelta(
            minutes=self.window_size_minutes * 2
        )

        for service_id in list(self.error_rate_history.keys()):
            self.error_rate_history[service_id] = [
                (ts, rate)
                for ts, rate in self.error_rate_history[service_id]
                if ts > cutoff_time
            ]


class StatisticalAnomalyDetector:
    def __init__(
        self,
        z_score_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
        min_samples: int = 30,
    ):
        self.z_score_threshold = z_score_threshold
        self.iqr_multiplier = iqr_multiplier
        self.min_samples = min_samples
        self.service_baselines: Dict[str, Dict[str, Any]] = {}

    def detect_anomaly(
        self, service_id: str, metric_value: float
    ) -> Tuple[bool, str, float]:
        if service_id not in self.service_baselines:
            return False, "insufficient_data", 0.0

        baseline = self.service_baselines[service_id]

        if len(baseline["values"]) < self.min_samples:
            return False, "insufficient_samples", 0.0

        mean = baseline["mean"]
        std = baseline["std"]

        if std == 0:
            return False, "no_variance", 0.0

        z_score = abs((metric_value - mean) / std)

        if z_score > self.z_score_threshold:
            anomaly_score = min(z_score / self.z_score_threshold, 1.0)
            return True, "statistical_outlier", anomaly_score

        q1 = baseline.get("q1", mean - std)
        q3 = baseline.get("q3", mean + std)
        iqr = q3 - q1
        lower_bound = q1 - self.iqr_multiplier * iqr
        upper_bound = q3 + self.iqr_multiplier * iqr

        if metric_value < lower_bound or metric_value > upper_bound:
            anomaly_score = 0.7
            return True, "iqr_outlier", anomaly_score

        return False, "normal", 0.0

    def update_baseline(
        self, service_id: str, values: List[float]
    ) -> None:
        if len(values) < self.min_samples:
            return

        values_array = np.array(values[-1000:])

        baseline = {
            "mean": float(np.mean(values_array)),
            "std": float(np.std(values_array)),
            "min": float(np.min(values_array)),
            "max": float(np.max(values_array)),
            "q1": float(np.percentile(values_array, 25)),
            "q2": float(np.percentile(values_array, 50)),
            "q3": float(np.percentile(values_array, 75)),
            "values": values,
            "updated_at": datetime.now().isoformat(),
        }

        self.service_baselines[service_id] = baseline
        logger.info(f"Updated baseline for {service_id}: mean={baseline['mean']:.2f}, std={baseline['std']:.2f}")


class BehavioralAnomalyDetector:
    def __init__(self):
        self.service_behavior: Dict[str, Dict[str, Any]] = {}
        self.deviation_threshold = 0.5

    def detect_behavior_change(
        self,
        service_id: str,
        current_error_rate: float,
        current_message_distribution: Dict[str, float],
    ) -> Tuple[bool, str, float]:
        if service_id not in self.service_behavior:
            self.service_behavior[service_id] = {
                "error_rates": [current_error_rate],
                "message_patterns": current_message_distribution,
            }
            return False, "learning", 0.0

        behavior = self.service_behavior[service_id]

        recent_error_rates = behavior["error_rates"][-100:]
        if recent_error_rates:
            baseline_error_rate = np.mean(recent_error_rates)
            error_rate_deviation = abs(
                current_error_rate - baseline_error_rate
            )

            if (
                baseline_error_rate > 0
                and error_rate_deviation / baseline_error_rate
                > self.deviation_threshold
            ):
                anomaly_score = min(
                    error_rate_deviation / baseline_error_rate, 1.0
                )
                return True, "error_rate_spike", anomaly_score

        behavior["error_rates"].append(current_error_rate)
        if len(behavior["error_rates"]) > 1000:
            behavior["error_rates"] = behavior["error_rates"][-500:]

        return False, "normal", 0.0

    def detect_pattern_shift(
        self,
        service_id: str,
        current_patterns: Dict[str, float],
        threshold: float = 0.3,
    ) -> Tuple[bool, str, float]:
        if service_id not in self.service_behavior:
            return False, "learning", 0.0

        behavior = self.service_behavior[service_id]
        previous_patterns = behavior.get("message_patterns", {})

        if not previous_patterns:
            behavior["message_patterns"] = current_patterns
            return False, "learning", 0.0

        common_patterns = set(current_patterns.keys()) & set(
            previous_patterns.keys()
        )
        if not common_patterns:
            return True, "pattern_shift", 0.8

        divergence = 0.0
        for pattern in common_patterns:
            prev_freq = previous_patterns.get(pattern, 0)
            curr_freq = current_patterns.get(pattern, 0)

            if prev_freq > 0:
                change = abs(curr_freq - prev_freq) / prev_freq
                divergence = max(divergence, change)

        if divergence > threshold:
            anomaly_score = min(divergence, 1.0)
            return True, "pattern_shift", anomaly_score

        behavior["message_patterns"] = current_patterns
        return False, "normal", 0.0


class MLAnomalyDetectionEngine:
    def __init__(
        self,
        z_score_threshold: float = 3.0,
        min_samples: int = 30,
    ):
        self.pattern_analyzer = LogPatternAnalyzer()
        self.statistical_detector = StatisticalAnomalyDetector(
            z_score_threshold=z_score_threshold,
            min_samples=min_samples,
        )
        self.behavioral_detector = BehavioralAnomalyDetector()
        self.anomaly_history: Dict[str, List[AnomalyScore]] = defaultdict(list)
        self.detection_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

    def analyze_log(
        self,
        service_id: str,
        log_level: str,
        message: str,
        anomaly_score_from_vector: Optional[float] = None,
    ) -> AnomalyScore:
        self.pattern_analyzer.update_pattern(service_id, log_level, message)

        is_anomaly, reason, score = self._run_detectors(
            service_id, log_level, message, anomaly_score_from_vector
        )

        severity = self._determine_severity(score, log_level)

        anomaly = AnomalyScore(
            service_id=service_id,
            timestamp=datetime.now(),
            score=score,
            is_anomaly=is_anomaly,
            reason=reason,
            severity=severity,
            features={
                "log_level": 1.0 if log_level == "ERROR" else 0.0,
                "vector_score": anomaly_score_from_vector or 0.0,
            },
            historical_baseline=self.statistical_detector.service_baselines.get(
                service_id, {}
            ).get("mean"),
        )

        self.anomaly_history[service_id].append(anomaly)
        if len(self.anomaly_history[service_id]) > 10000:
            self.anomaly_history[service_id] = (
                self.anomaly_history[service_id][-5000:]
            )

        if is_anomaly:
            self.detection_stats[service_id][reason] += 1

        return anomaly

    def _run_detectors(
        self,
        service_id: str,
        log_level: str,
        message: str,
        vector_score: Optional[float],
    ) -> Tuple[bool, str, float]:
        error_rate = self.pattern_analyzer.get_error_rate(service_id)

        behavioral_is_anomaly, behavioral_reason, behavioral_score = (
            self.behavioral_detector.detect_behavior_change(
                service_id, error_rate, {}
            )
        )

        if behavioral_is_anomaly and behavioral_score > 0.7:
            return True, behavioral_reason, behavioral_score

        if vector_score and vector_score > 0.8:
            return True, "vector_anomaly", vector_score

        is_critical = log_level in ["ERROR", "CRITICAL", "FATAL"]
        base_score = 0.6 if is_critical else 0.0

        if is_critical and error_rate > 0.5:
            return True, "critical_error_spike", min(base_score + error_rate, 1.0)

        return False, "normal", 0.0

    def _determine_severity(self, score: float, log_level: str) -> str:
        if score > 0.8:
            return "critical"
        elif score > 0.6:
            return "high"
        elif score > 0.4:
            return "medium"
        elif score > 0.2:
            return "low"
        else:
            return "info"

    def get_anomaly_history(
        self,
        service_id: str,
        limit: int = 100,
    ) -> List[AnomalyScore]:
        history = self.anomaly_history.get(service_id, [])
        return history[-limit:]

    def get_statistics(self, service_id: str) -> Dict[str, Any]:
        history = self.anomaly_history.get(service_id, [])
        anomalies = [a for a in history if a.is_anomaly]

        return {
            "total_analyzed": len(history),
            "anomalies_detected": len(anomalies),
            "anomaly_rate": len(anomalies) / len(history) if history else 0,
            "detection_reasons": dict(
                self.detection_stats.get(service_id, {})
            ),
            "avg_anomaly_score": (
                np.mean([a.score for a in anomalies])
                if anomalies
                else 0
            ),
        }

    def train_on_baseline(
        self, service_id: str, logs: List[Dict[str, Any]]
    ) -> None:
        error_counts = []

        for log in logs:
            level = log.get("level", "INFO")
            error_counts.append(1 if level == "ERROR" else 0)

        error_rate_values = []
        window = 50
        for i in range(len(error_counts) - window):
            window_errors = sum(error_counts[i : i + window])
            error_rate_values.append(window_errors / window)

        if error_rate_values:
            self.statistical_detector.update_baseline(
                service_id, error_rate_values
            )

        logger.info(
            f"Trained baseline for {service_id} on {len(logs)} logs"
        )


detector_engine = MLAnomalyDetectionEngine()
