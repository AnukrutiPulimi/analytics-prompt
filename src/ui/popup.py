"""Create a local popup summary for analytics results.

This module displays a Windows Tkinter popup with a clean executive layout.
It also persists a structured summary to a JSON file under the local data
folder, including fallback flags and health status.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:  # pragma: no cover
    tk = None
    messagebox = None

logger = logging.getLogger(__name__)


def _ensure_data_directory(data_dir: Path) -> Path:
    """Ensure the data directory exists and return its Path."""
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _summary_file_path(data_dir: Path | str | None = None) -> Path:
    """Build the daily summary file path."""
    directory = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parents[1] / "data"
    _ensure_data_directory(directory)
    filename = f"{datetime.now():%Y-%m-%d}-summary.json"
    return directory / filename


def save_summary_to_file(summary: Dict[str, Any], data_dir: Path | str | None = None) -> Path:
    """Write the summary dictionary to a JSON file and return the path."""
    file_path = _summary_file_path(data_dir)
    try:
        with file_path.open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, default=str)
        logger.info("Summary written to %s", file_path)
    except Exception as exc:
        logger.exception("Failed to write summary JSON to %s.", file_path)
        raise
    return file_path


def _build_popup_message(summary: Dict[str, Any]) -> str:
    """Construct a human-readable popup message from the summary data."""
    lines = [
        f"Utility: {summary.get('utility', 'N/A')}",
        f"Platform: {summary.get('platform', 'N/A')}",
        f"Offer: {summary.get('offer', 'N/A')}",
        f"Complete: {summary.get('complete', 'N/A')}",
        f"Completion Rate: {summary.get('completion_rate', 'N/A')}",
        f"Status: {summary.get('status_label', 'N/A')}",
        f"Fallback Used: {summary.get('fallback_used', False)}",
        "",
        f"Overall Health: {summary.get('overall_health', 'N/A')}",
    ]
    return "\n".join(lines)


def _display_tk_popup(summary: Dict[str, Any]) -> None:
    """Display the summary in a Tkinter popup."""
    if tk is None or messagebox is None:
        raise RuntimeError("Tkinter is not available in this environment.")

    root = tk.Tk()
    root.withdraw()
    root.title("Analytics Daily Summary")
    popup_text = _build_popup_message(summary)

    try:
        messagebox.showinfo("Analytics Summary", popup_text)
    finally:
        root.destroy()


def show_summary_popup(summary: Dict[str, Any], data_dir: Path | str | None = None) -> None:
    """Save the summary and display a Windows popup if possible.

    The summary is always persisted to a JSON file, even if the popup fails.
    """
    try:
        save_summary_to_file(summary, data_dir=data_dir)
    except Exception:
        logger.warning("Proceeding even though summary file save failed.")

    try:
        _display_tk_popup(summary)
    except Exception as exc:
        logger.exception("Popup display failed, continuing execution.")
        logger.debug("Popup failure details: %s", exc)
