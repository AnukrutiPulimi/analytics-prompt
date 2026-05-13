"""Define navigation flows for Looker Studio dashboards.

This module provides safe navigation to Numbers pages for each utility.
It clicks sidebar links, validates table visibility, and returns a structured
status object for each navigation step.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import Page
except ImportError:  # pragma: no cover
    PlaywrightError = Exception
    Page = object

logger = logging.getLogger(__name__)


def default_sidebar_selectors() -> Dict[str, str]:
    """Return the default sidebar selector mapping for Numbers pages."""
    return {
        "Numbers Web Outage": "",
        "Numbers Android App Outage": "",
        "Numbers iOS App Outage": "",
    }


@dataclass
class NavigationStatus:
    """Structured status returned from navigation attempts."""

    success: bool
    clicked_label: Optional[str] = None
    attempts: int = 0
    message: Optional[str] = None


class NavigationError(Exception):
    """Raised when a navigation step fails after retrying."""


def _click_sidebar_item(
    page: Page,
    label: str,
    selector: str,
    timeout: int,
    retries: int,
    delay_seconds: int,
) -> NavigationStatus:
    """Click a sidebar item safely with retry and selector validation."""
    logger.info("Attempting to click sidebar item '%s'.", label)

    for attempt in range(1, retries + 1):
        try:
            logger.debug("Waiting for sidebar selector '%s' (attempt %s).", selector, attempt)
            page.wait_for_selector(selector, timeout=timeout)
            logger.debug("Sidebar selector '%s' is visible.", selector)

            page.click(selector, timeout=timeout)
            logger.info("Clicked sidebar item '%s' successfully.", label)
            return NavigationStatus(
                success=True,
                clicked_label=label,
                attempts=attempt,
                message=f"Clicked '{label}' successfully.",
            )
        except PlaywrightError as exc:
            logger.warning(
                "Sidebar click attempt %s for '%s' failed: %s",
                attempt,
                label,
                exc,
            )
            if attempt < retries:
                logger.debug("Retrying sidebar click after %s seconds.", delay_seconds)
                time.sleep(delay_seconds)
            else:
                message = f"Failed to click sidebar item '{label}' after {retries} attempts."
                logger.error(message)
                return NavigationStatus(success=False, clicked_label=label, attempts=attempt, message=message)


def _confirm_table_visible(page: Page, table_selector: str, timeout: int) -> None:
    """Confirm the table is visible before proceeding."""
    logger.info("Waiting for table selector '%s' to appear.", table_selector)
    try:
        page.wait_for_selector(table_selector, timeout=timeout)
        logger.info("Table selector '%s' is visible.", table_selector)
    except PlaywrightError as exc:
        logger.exception("Table selector '%s' did not appear in time.", table_selector)
        raise NavigationError(f"Table selector '{table_selector}' was not visible within timeout.") from exc


def navigate_to_numbers_page(
    page: Page,
    dashboard_name: str,
    sidebar_selectors: Optional[Dict[str, str]] = None,
    table_selector: str = "",
    timeout: int = 60000,
    click_retries: int = 3,
    click_delay_seconds: int = 3,
) -> NavigationStatus:
    """Navigate to the requested Numbers page via sidebar clicks.

    After loading the utility URL, this method clicks the sidebar link that
    matches the configured Numbers page label and validates the table's visibility.
    """
    sidebar_selectors = sidebar_selectors or default_sidebar_selectors()

    if dashboard_name not in sidebar_selectors:
        message = f"Dashboard name '{dashboard_name}' is not configured for navigation."
        logger.error(message)
        return NavigationStatus(success=False, message=message)

    selector = sidebar_selectors[dashboard_name]
    if not selector:
        message = f"No sidebar selector configured for '{dashboard_name}'."
        logger.error(message)
        return NavigationStatus(success=False, message=message)

    status = _click_sidebar_item(
        page=page,
        label=dashboard_name,
        selector=selector,
        timeout=timeout,
        retries=click_retries,
        delay_seconds=click_delay_seconds,
    )

    if not status.success:
        raise NavigationError(status.message or "Sidebar click failed.")

    _confirm_table_visible(page, table_selector, timeout)
    status.message = f"Navigation to '{dashboard_name}' completed and table is visible."
    return status
