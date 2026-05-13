"""Calculate analytics metrics from extracted data.

This module computes metrics for a utility/platform dataset, including
7-day averages, highs/lows, and deviation from average for the current or
previous-day record.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class MetricsSummary:
    """Structured metrics summary for a platform or utility."""

    average_completion_rate: float
    highest_completion_rate: float
    lowest_completion_rate: float
    average_complete_count: float
    reference_completion_rate: Optional[float]
    reference_complete_count: Optional[int]
    completion_rate_deviation: Optional[float]
    record_count: int


def _extract_numeric_values(records: Iterable[Dict[str, Any]], key: str) -> List[float]:
    values = []
    for record in records:
        try:
            value = record[key]
            if isinstance(value, str):
                value = float(value.replace("%", "")) if key == "Completion Rate" else int(value.replace(",", ""))
            values.append(float(value))
        except Exception:
            continue
    return values


def compute_metrics(
    records: Iterable[Dict[str, Any]],
    reference_record: Optional[Dict[str, Any]] = None,
) -> MetricsSummary:
    """Compute performance metrics from the given records.

    Args:
        records: Structured records containing Date, Offer, Complete, and
            Completion Rate.
        reference_record: Optional record used for deviation calculation.

    Returns:
        A MetricsSummary containing averages, high/low values, and deviation.
    """
    completion_rates = _extract_numeric_values(records, "Completion Rate")
    complete_counts = _extract_numeric_values(records, "Complete")

    average_completion_rate = mean(completion_rates) if completion_rates else 0.0
    highest_completion_rate = max(completion_rates) if completion_rates else 0.0
    lowest_completion_rate = min(completion_rates) if completion_rates else 0.0
    average_complete_count = mean(complete_counts) if complete_counts else 0.0

    reference_completion_rate = None
    reference_complete_count = None
    completion_rate_deviation = None
    if reference_record is not None:
        try:
            reference_completion_rate = float(str(reference_record["Completion Rate"]).replace("%", ""))
            reference_complete_count = int(str(reference_record["Complete"]).replace(",", ""))
            completion_rate_deviation = (
                (reference_completion_rate - average_completion_rate) / average_completion_rate * 100
                if average_completion_rate else 0.0
            )
        except Exception:
            reference_completion_rate = None
            reference_complete_count = None
            completion_rate_deviation = None

    return MetricsSummary(
        average_completion_rate=average_completion_rate,
        highest_completion_rate=highest_completion_rate,
        lowest_completion_rate=lowest_completion_rate,
        average_complete_count=average_complete_count,
        reference_completion_rate=reference_completion_rate,
        reference_complete_count=reference_complete_count,
        completion_rate_deviation=completion_rate_deviation,
        record_count=len(completion_rates),
    )


def summarize_trends(metrics: MetricsSummary) -> Dict[str, Any]:
    """Summarize metric trends for the analysis period."""
    return {
        "average_completion_rate": metrics.average_completion_rate,
        "highest_completion_rate": metrics.highest_completion_rate,
        "lowest_completion_rate": metrics.lowest_completion_rate,
        "average_complete_count": metrics.average_complete_count,
        "reference_completion_rate": metrics.reference_completion_rate,
        "reference_complete_count": metrics.reference_complete_count,
        "completion_rate_deviation": metrics.completion_rate_deviation,
        "record_count": metrics.record_count,
    }
