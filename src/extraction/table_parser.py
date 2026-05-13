"""Parse table data from Looker Studio pages.

This module converts raw table rows into structured records and performs
validation of each row's Date, Offer, Complete, and Completion Rate columns.
Malformed rows are skipped with logging, and the parser supports missing
or incomplete table data gracefully.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List, Sequence

logger = logging.getLogger(__name__)


class TableParserError(Exception):
    """Base exception for table parser failures."""


class MissingTableError(TableParserError):
    """Raised when the table is not present in the page content."""


class MalformedRowError(TableParserError):
    """Raised when an individual table row cannot be parsed."""


def parse_table_rows(rows: Iterable[Sequence[str]]) -> List[Dict[str, Any]]:
    """Parse raw table rows into structured records.

    Args:
        rows: An iterable of row value sequences, each containing exactly four
            columns in the order [Date, Offer, Complete, Completion Rate].

    Returns:
        A list of validated records with normalized types.

    Raises:
        MissingTableError: If the provided row collection is missing or None.
    """
    if rows is None:
        logger.error("Table row collection is missing; cannot parse table.")
        raise MissingTableError("Table rows are missing or unavailable.")

    records: List[Dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        try:
            record = extract_columns(row)
            records.append(record)
        except MalformedRowError as exc:
            logger.warning("Skipping malformed row %s: %s", index, exc)
        except Exception as exc:
            logger.warning(
                "Skipping row %s due to unexpected error: %s",
                index,
                exc,
            )
    if len(records) < 7:
        logger.info("Parsed %s valid rows; fewer than 7 rows were available.", len(records))
    return records


def extract_columns(row: Sequence[str]) -> Dict[str, Any]:
    """Extract and normalize expected columns from a table row.

    Args:
        row: A sequence containing [Date, Offer, Complete, Completion Rate].

    Returns:
        A dictionary with normalized values.

    Raises:
        MalformedRowError: If the row is malformed or any column cannot be parsed.
    """
    if not isinstance(row, (list, tuple)):
        raise MalformedRowError("Row must be a list or tuple of column values.")

    if len(row) != 4:
        raise MalformedRowError(
            f"Unexpected column count: expected 4, got {len(row)}."
        )

    date_value = _normalize_date(row[0])
    offer_value = _normalize_integer(row[1], "Offer")
    complete_value = _normalize_integer(row[2], "Complete")
    completion_rate_value = _normalize_completion_rate(row[3])

    return {
        "Date": date_value,
        "Offer": offer_value,
        "Complete": complete_value,
        "Completion Rate": completion_rate_value,
    }


def _normalize_date(value: str) -> str:
    """Normalize a date value into ISO format.

    This function accepts common date representations and converts them to
    YYYY-MM-DD. It leaves any already valid ISO date string unchanged.
    """
    if not isinstance(value, str) or not value.strip():
        raise MalformedRowError("Date value is missing or empty.")

    normalized = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%b %d, %Y"):
        try:
            parsed = datetime.strptime(normalized, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise MalformedRowError(f"Date value '{value}' is not in a recognized format.")


def _normalize_integer(value: str, column_name: str) -> int:
    """Normalize an integer-like value.

    Accepts numeric strings and strips commas or whitespace.
    """
    if not isinstance(value, str) or not value.strip():
        raise MalformedRowError(f"{column_name} value is missing or empty.")

    cleaned = value.replace(",", "").strip()
    if not cleaned.isdigit():
        raise MalformedRowError(f"{column_name} value '{value}' is not an integer.")
    return int(cleaned)


def _normalize_completion_rate(value: str) -> float:
    """Normalize completion rate text into a floating point percentage.

    Example inputs: '94%', '94.0 %', '0.94'.
    """
    if not isinstance(value, str) or not value.strip():
        raise MalformedRowError("Completion Rate value is missing or empty.")

    cleaned = value.strip().replace("%", "").replace(",", "")
    try:
        parsed = float(cleaned)
    except ValueError as exc:
        raise MalformedRowError(
            f"Completion Rate value '{value}' is not a valid number."
        ) from exc

    if parsed > 1 and parsed <= 100:
        return parsed

    return parsed
