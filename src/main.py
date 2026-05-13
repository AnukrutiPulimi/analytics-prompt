"""Main entry point for the analytics automation tool.

This module coordinates configuration loading, browser automation,
extraction, analytics, and summary presentation. It is designed to
continue processing remaining utilities when partial failures occur.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from browser.navigation import navigate_to_numbers_page
from browser.playwright_manager import BrowserManager
from extraction.date_logic import build_date_context
from extraction.table_parser import parse_table_rows
from logger import get_logger
from analytics.alert_engine import evaluate_alerts, format_alert_summary
from analytics.metrics_engine import compute_metrics
from config_loader import load_selectors_config, load_thresholds_config, load_urls_config
from ui.popup import show_summary_popup

ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"

logger = get_logger(__name__)


def _load_configs() -> Dict[str, Dict[str, Any]]:
    logger.info("Loading configuration files.")
    return {
        "urls": load_urls_config(CONFIG_DIR / "urls.json"),
        "selectors": load_selectors_config(CONFIG_DIR / "selectors.json"),
        "thresholds": load_thresholds_config(CONFIG_DIR / "thresholds.json"),
    }


def _build_sidebar_selector_map(selectors: Dict[str, str]) -> Dict[str, str]:
    return {
        "Numbers Web Outage": selectors.get("sidebar_numbers_web", ""),
        "Numbers Android App Outage": selectors.get("sidebar_numbers_android", ""),
        "Numbers iOS App Outage": selectors.get("sidebar_numbers_ios", ""),
    }


def _build_summary_payload(result: Dict[str, Any], overall_health: str) -> Dict[str, Any]:
    return {
        "utility": result.get("utility"),
        "platform": result.get("platform"),
        "offer": result.get("offer"),
        "complete": result.get("complete"),
        "completion_rate": result.get("completion_rate"),
        "status_label": result.get("status"),
        "fallback_used": result.get("fallback_used", False),
        "health": overall_health,
    }


def _process_platform(
    page: Any,
    utility_name: str,
    utility_url: str,
    platform_name: str,
    sidebar_label: str,
    sidebar_selectors: Dict[str, str],
    table_selector: str,
    thresholds: Dict[str, Any],
) -> Dict[str, Any]:
    logger.info("Processing utility=%s platform=%s", utility_name, platform_name)

    navigation_status = navigate_to_numbers_page(
        page=page,
        dashboard_name=sidebar_label,
        sidebar_selectors=sidebar_selectors,
        table_selector=table_selector,
    )

    page_content = page.content()
    raw_rows = parse_table_rows(page_content)
    date_context = build_date_context(raw_rows)

    metrics = compute_metrics(
        date_context["last_7_days"],
        reference_record=date_context["previous_day_row"],
    )
    alert_summary = evaluate_alerts(metrics, thresholds)
    formatted_alert = format_alert_summary(alert_summary)

    return {
        "utility": utility_name,
        "platform": platform_name,
        "offer": date_context["previous_day_row"].get("Offer") if date_context["previous_day_row"] else None,
        "complete": date_context["previous_day_row"].get("Complete") if date_context["previous_day_row"] else None,
        "completion_rate": date_context["previous_day_row"].get("Completion Rate") if date_context["previous_day_row"] else None,
        "status": formatted_alert["severity"],
        "reasons": formatted_alert["reasons"],
        "metrics": formatted_alert["metrics"],
        "fallback_used": date_context["fallback_used"],
        "navigation_status": navigation_status,
    }


def _aggregate_overall_health(results: List[Dict[str, Any]]) -> str:
    if any(result.get("status") == "CRITICAL" for result in results):
        return "CRITICAL"
    if any(result.get("status") == "WARNING" for result in results):
        return "WARNING"
    return "HEALTHY" if results else "UNKNOWN"


def main() -> int:
    logger.info("Starting analytics automation workflow.")
    exit_code = 0
    browser_manager = BrowserManager(headless=True)
    browser = None
    results: List[Dict[str, Any]] = []

    try:
        configs = _load_configs()
        sidebar_selectors = _build_sidebar_selector_map(configs["selectors"])
        table_selector = configs["selectors"].get("table_selector", "")
        thresholds = configs["thresholds"]

        browser = browser_manager.start()
        page = browser_manager.create_page(browser)

        utilities = configs["urls"].get("utilities", {})
        for utility_name, utility_url in utilities.items():
            try:
                logger.info("Navigating to utility URL: %s", utility_url)
                page.goto(utility_url)

                for platform_name, sidebar_label in [
                    ("Web", "Numbers Web Outage"),
                    ("Android", "Numbers Android App Outage"),
                    ("iOS", "Numbers iOS App Outage"),
                ]:
                    try:
                        result = _process_platform(
                            page=page,
                            utility_name=utility_name,
                            utility_url=utility_url,
                            platform_name=platform_name,
                            sidebar_label=sidebar_label,
                            sidebar_selectors=sidebar_selectors,
                            table_selector=table_selector,
                            thresholds=thresholds,
                        )
                        results.append(result)
                    except Exception as exc:
                        logger.exception(
                            "Platform processing failed for %s/%s: %s",
                            utility_name,
                            platform_name,
                            exc,
                        )
                        exit_code = 1
                        continue
            except Exception as exc:
                logger.exception("Navigation failed for utility %s: %s", utility_name, exc)
                exit_code = 1
                continue

        overall_health = _aggregate_overall_health(results)
        summary = {
            "run_timestamp": datetime.utcnow().isoformat() + "Z",
            "overall_health": overall_health,
            "results": results,
        }

        try:
            show_summary_popup(summary, data_dir=DATA_DIR)
        except Exception as exc:
            logger.exception("Failed to display summary popup: %s", exc)
            exit_code = max(exit_code, 1)

        logger.info("Workflow completed with overall health=%s.", overall_health)
    except Exception as exc:
        logger.exception("Fatal error during workflow execution: %s", exc)
        exit_code = 1
    finally:
        if browser is not None:
            browser_manager.close()
        logger.info("Browser session closed and workflow is exiting.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
