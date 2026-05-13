"""Provide date-related logic for analytics.

This module determines the effective previous business date for the dataset,
locates the matching row when available, and extracts the most recent available
records for the last seven days while handling gaps due to weekends or holidays.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


def _parse_record_date(record: Dict[str, Any]) -> date:
    """Parse the Date field of a record into a date object."""
    date_value = record.get("Date")
    if isinstance(date_value, date):
        return date_value
    if isinstance(date_value, str):
        try:
            return datetime.strptime(date_value.strip(), "%Y-%m-%d").date()
        except ValueError as exc:
            logger.error("Unable to parse record date '%s'.", date_value)
            raise
    raise ValueError("Record Date field must be a date or ISO date string.")


def get_previous_day_reference(reference_date: Optional[str] = None) -> date:
    """Return the previous calendar day as a date object.

    If a reference date is provided as an ISO string, compute the previous day
    relative to that date. Otherwise, use today's date.
    """
    if reference_date:
        base_date = datetime.strptime(reference_date.strip(), "%Y-%m-%d").date()
    else:
        base_date = date.today()
    return base_date - timedelta(days=1)


def _sort_records_by_date(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort records by the parsed Date field in descending order."""
    parsed_records = []
    for record in records:
        try:
            record_date = _parse_record_date(record)
            parsed_records.append((record_date, record))
        except Exception:
            logger.warning("Skipping record with invalid date during sort: %s", record)
    parsed_records.sort(key=lambda pair: pair[0], reverse=True)
    return [record for _, record in parsed_records]


def find_previous_day_row(
    records: Iterable[Dict[str, Any]],
    reference_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Find the record matching the previous day, or fall back to the most recent row.

    Returns a dictionary with the selected row and a fallback flag.
    """
    sorted_records = _sort_records_by_date(records)
    if not sorted_records:
        logger.error("No records available to determine previous day row.")
        return {"previous_day_row": None, "fallback_used": False}

    target_date = get_previous_day_reference(reference_date)
    for record in sorted_records:
        try:
            record_date = _parse_record_date(record)
        except Exception:
            continue
        if record_date == target_date:
            logger.info("Found matching previous day row for %s.", target_date)
            return {"previous_day_row": record, "fallback_used": False}

    fallback = sorted_records[0]
    logger.warning(
        "Previous day row for %s not found; falling back to most recent available date.",
        target_date,
    )
    return {"previous_day_row": fallback, "fallback_used": True}


def extract_last_n_available_rows(
    records: Iterable[Dict[str, Any]],
    n: int = 7,
) -> List[Dict[str, Any]]:
    """Return the most recent n available records sorted by date descending."""
    sorted_records = _sort_records_by_date(records)
    result = sorted_records[:n]
    logger.info("Extracted %s most recent available rows.", len(result))
    return result


def build_date_context(
    records: Iterable[Dict[str, Any]],
    reference_date: Optional[str] = None,
    n: int = 7,
) -> Dict[str, Any]:
    """Build the date context required by analytics.

    The returned structure includes the selected previous day row, the last n
    available rows, and whether a fallback was used.
    """
    last_7_days = extract_last_n_available_rows(records, n=n)
    previous_day_result = find_previous_day_row(records, reference_date=reference_date)

    return {
        "previous_day_row": previous_day_result.get("previous_day_row"),
        "last_7_days": last_7_days,
        "fallback_used": previous_day_result.get("fallback_used", False),
    }
