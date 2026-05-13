"""Generate alerts based on analytics results.

This module evaluates metrics against configured thresholds and returns a
structured severity summary for the given utility/platform.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AlertSummary:
    """Structured alert summary for a platform or utility."""

    severity: str
    reasons: List[str]
    average_completion_rate: float
    highest_completion_rate: float
    lowest_completion_rate: float
    average_complete_count: float
    completion_rate_deviation: Optional[float]
    reference_completion_rate: Optional[float]
    reference_complete_count: Optional[int]


def evaluate_alerts(metrics: Any, thresholds: Dict[str, Any]) -> AlertSummary:
    """Evaluate analytics metrics and determine alert severity."""
    reasons: List[str] = []
    severity = "HEALTHY"

    critical_drop_percent = thresholds.get("critical_drop_percent", 10)
    low_volume_threshold = thresholds.get("low_volume_threshold", 0.7)

    reference_rate = metrics.reference_completion_rate
    avg_rate = metrics.average_completion_rate
    lowest_rate = metrics.lowest_completion_rate
    avg_complete = metrics.average_complete_count
    ref_complete = metrics.reference_complete_count
    deviation = metrics.completion_rate_deviation

    if reference_rate is not None and reference_rate == lowest_rate:
        severity = "CRITICAL"
        reasons.append("Current completion rate is the lowest in the last 7 days.")

    if deviation is not None and deviation < -critical_drop_percent:
        severity = "CRITICAL"
        reasons.append(
            f"Completion rate dropped {abs(deviation):.1f}% below the 7-day average."
        )

    if severity != "CRITICAL":
        if reference_rate is not None and reference_rate < avg_rate:
            severity = "WARNING"
            reasons.append("Current completion rate is below the 7-day average.")

        if ref_complete is not None and avg_complete > 0 and ref_complete < avg_complete * low_volume_threshold:
            if severity != "CRITICAL":
                severity = "WARNING"
            reasons.append(
                "Current completed volume is less than 70% of the 7-day average."
            )

    if not reasons:
        severity = "HEALTHY"
        reasons.append("Performance is above average and within expected thresholds.")

    return AlertSummary(
        severity=severity,
        reasons=reasons,
        average_completion_rate=avg_rate,
        highest_completion_rate=highest_rate,
        lowest_completion_rate=lowest_rate,
        average_complete_count=avg_complete,
        completion_rate_deviation=deviation,
        reference_completion_rate=reference_rate,
        reference_complete_count=ref_complete,
    )


def format_alert_summary(alert: AlertSummary) -> Dict[str, Any]:
    """Format alert summary into a serializable structure."""
    return {
        "severity": alert.severity,
        "reasons": alert.reasons,
        "metrics": {
            "average_completion_rate": alert.average_completion_rate,
            "highest_completion_rate": alert.highest_completion_rate,
            "lowest_completion_rate": alert.lowest_completion_rate,
            "average_complete_count": alert.average_complete_count,
            "completion_rate_deviation": alert.completion_rate_deviation,
            "reference_completion_rate": alert.reference_completion_rate,
            "reference_complete_count": alert.reference_complete_count,
        },
    }
