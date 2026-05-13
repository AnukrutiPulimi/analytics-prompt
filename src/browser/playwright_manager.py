"""Manage the Playwright browser lifecycle.

This module initializes the Playwright browser, provides a reliable
navigation helper with retry behavior, and waits for Looker Studio content
such as table selectors and network idle state before handing control back
to the caller.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import Browser, Page, sync_playwright
except ImportError:  # pragma: no cover
    PlaywrightError = Exception
    Browser = object
    Page = object
    sync_playwright = None


logger = logging.getLogger(__name__)


class BrowserManagerError(Exception):
    """Base exception for browser manager failures."""


class PlaywrightInitializationError(BrowserManagerError):
    """Raised when Playwright cannot be initialized."""


class NavigationError(BrowserManagerError):
    """Raised when navigation to a target page fails."""


class NetworkIdleTimeoutError(NavigationError):
    """Raised when waiting for network idle exceeds the configured timeout."""


class SelectorTimeoutError(NavigationError):
    """Raised when the expected selector does not appear in time."""


class BrowserManager:
    """Encapsulate browser startup, navigation, and teardown behavior."""

    def __init__(
        self,
        headless: bool = True,
        default_timeout: int = 60000,
        navigation_retries: int = 3,
        retry_delay: int = 5,
        wait_for_load_state: str = "networkidle",
    ):
        self.headless = headless
        self.default_timeout = default_timeout
        self.navigation_retries = navigation_retries
        self.retry_delay = retry_delay
        self.wait_for_load_state = wait_for_load_state
        self._playwright = None
        self.browser: Optional[Browser] = None
        self.logger = logger

    def start(self) -> Browser:
        """Launch Playwright and open a browser instance."""
        self.logger.info("Starting Playwright browser (headless=%s).", self.headless)

        if sync_playwright is None:
            raise PlaywrightInitializationError("Playwright is not installed or cannot be imported.")

        try:
            self._playwright = sync_playwright().start()
            self.browser = self._playwright.chromium.launch(headless=self.headless)
            self.logger.info("Playwright browser launched successfully.")
            return self.browser
        except PlaywrightError as exc:
            self.logger.exception("Failed to initialize Playwright browser.")
            raise PlaywrightInitializationError("Unable to start Playwright browser.") from exc

    def close(self) -> None:
        """Close the browser and clean up Playwright resources."""
        self.logger.info("Closing Playwright browser.")
        if self.browser is not None:
            try:
                self.browser.close()
                self.logger.info("Browser closed successfully.")
            except PlaywrightError:
                self.logger.exception("Error while closing browser.")
        if self._playwright is not None:
            try:
                self._playwright.stop()
                self.logger.info("Playwright stopped successfully.")
            except PlaywrightError:
                self.logger.exception("Error while stopping Playwright.")

    def create_page(self, browser: Optional[Browser] = None) -> Page:
        """Open a new browser page for navigation."""
        self.logger.info("Creating new browser page.")
        if browser is None:
            browser = self.browser
        if browser is None:
            raise BrowserManagerError("Browser instance is not initialized.")

        return browser.new_page()

    def navigate_with_retry(
        self,
        page: Page,
        url: str,
        table_selector: str,
        timeout: Optional[int] = None,
    ) -> Page:
        """Navigate to a URL and wait for the target page to stabilize."""
        timeout = timeout or self.default_timeout

        last_exception: Optional[Exception] = None
        for attempt in range(1, self.navigation_retries + 1):
            self.logger.info("Navigation attempt %s to URL: %s", attempt, url)
            try:
                self._navigate(page, url, timeout)
                self._wait_for_network_idle(page, timeout)
                self._wait_for_selector(page, table_selector, timeout)
                self.logger.info("Navigation succeeded on attempt %s.", attempt)
                return page
            except NavigationError as exc:
                last_exception = exc
                self.logger.warning(
                    "Navigation attempt %s failed: %s. Retrying after %s seconds.",
                    attempt,
                    exc,
                    self.retry_delay,
                )
                time.sleep(self.retry_delay)
            except PlaywrightError as exc:
                last_exception = exc
                self.logger.exception("Playwright error during navigation on attempt %s.", attempt)
                time.sleep(self.retry_delay)

        self.logger.error("Navigation failed after %s attempts.", self.navigation_retries)
        raise NavigationError("Unable to navigate to URL after retries.") from last_exception

    def _navigate(self, page: Page, url: str, timeout: int) -> None:
        """Perform a single page navigation and handle timeout exceptions."""
        self.logger.debug("Starting page.goto for URL: %s", url)
        try:
            page.goto(url, timeout=timeout)
            self.logger.debug("Page.goto completed for URL: %s", url)
        except PlaywrightError as exc:
            self.logger.exception("Page navigation error for URL: %s", url)
            raise NavigationError(f"Navigation to {url} failed.") from exc

    def _wait_for_network_idle(self, page: Page, timeout: int) -> None:
        """Wait until the page reaches network idle state."""
        self.logger.debug("Waiting for network idle state with timeout %sms.", timeout)
        try:
            page.wait_for_load_state(self.wait_for_load_state, timeout=timeout)
            self.logger.debug("Network idle state reached.")
        except PlaywrightError as exc:
            self.logger.exception("Timeout waiting for network idle.")
            raise NetworkIdleTimeoutError("Network idle wait timed out.") from exc

    def _wait_for_selector(self, page: Page, selector: str, timeout: int) -> None:
        """Wait until the configured table selector becomes available."""
        self.logger.debug("Waiting for selector '%s' with timeout %sms.", selector, timeout)
        try:
            page.wait_for_selector(selector, timeout=timeout)
            self.logger.debug("Selector '%s' is present on the page.", selector)
        except PlaywrightError as exc:
            self.logger.exception("Timeout waiting for selector: %s", selector)
            raise SelectorTimeoutError(f"Selector '{selector}' did not appear in time.") from exc


def launch_browser(headless: bool = True) -> Browser:
    """Convenience wrapper to launch a Playwright browser externally."""
    manager = BrowserManager(headless=headless)
    return manager.start()


def close_browser(browser: Browser) -> None:
    """Convenience wrapper to close a Playwright browser instance."""
    manager = BrowserManager()
    manager.browser = browser
    manager.close()
