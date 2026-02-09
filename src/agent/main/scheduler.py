"""Scheduler for periodic scans."""

import asyncio
import logging
import os
from datetime import datetime
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


class SREScheduler:
    """Manages scheduled scans."""

    def __init__(
        self,
        scan_callback: Callable[[str], Awaitable[None]],
        interval_seconds: int = 300,
        namespaces: list[str] = None
    ):
        """
        Initialize the scheduler.

        Args:
            scan_callback: Async function to call for each namespace scan
            interval_seconds: Seconds between scans (default 5 minutes)
            namespaces: List of namespaces to scan
        """
        self.scan_callback = scan_callback
        self.interval = interval_seconds
        self.namespaces = namespaces or self._get_namespaces_from_env()
        self._running = False
        self._task: asyncio.Task = None

    def _get_namespaces_from_env(self) -> list[str]:
        """Get namespaces from environment variable."""
        ns_env = os.environ.get("TARGET_NAMESPACES", "default")
        return [ns.strip() for ns in ns_env.split(",") if ns.strip()]

    async def start(self):
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            f"Scheduler started: scanning {self.namespaces} every {self.interval}s"
        )

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")

    async def _run_loop(self):
        """Main scheduler loop."""
        # Initial delay to let the service start up
        await asyncio.sleep(10)

        while self._running:
            try:
                await self._run_scans()
            except Exception as e:
                logger.error(f"Error in scheduled scan: {e}", exc_info=True)

            # Wait for next interval
            await asyncio.sleep(self.interval)

    async def _run_scans(self):
        """Run scans for all configured namespaces."""
        logger.info(f"Starting scheduled scans at {datetime.utcnow().isoformat()}")

        for namespace in self.namespaces:
            try:
                logger.info(f"Scanning namespace: {namespace}")
                await self.scan_callback(namespace)
            except Exception as e:
                logger.error(f"Error scanning {namespace}: {e}", exc_info=True)

        logger.info("Scheduled scans complete")

    async def run_once(self, namespace: str = None):
        """Run a single scan immediately (for testing or manual triggers)."""
        namespaces = [namespace] if namespace else self.namespaces
        for ns in namespaces:
            await self.scan_callback(ns)
