"""Background workers initialization."""

from ...gc import BackgroundWorker
from ...logging_config import get_logger
from ..state import PROVIDERS

logger = get_logger(__name__)

GC_WORKER_INTERVAL_SECONDS = 30
"""Interval for garbage collection worker."""

HEALTH_CHECK_INTERVAL_SECONDS = 60
"""Interval for health check worker."""


def create_background_workers() -> list[BackgroundWorker]:
    """Create (but don't start) background workers.

    Returns:
        List of BackgroundWorker instances (not started).
    """
    gc_worker = BackgroundWorker(
        PROVIDERS,
        interval_s=GC_WORKER_INTERVAL_SECONDS,
        task="gc",
    )

    health_worker = BackgroundWorker(
        PROVIDERS,
        interval_s=HEALTH_CHECK_INTERVAL_SECONDS,
        task="health_check",
    )

    logger.info("background_workers_created", workers=["gc", "health_check"])
    return [gc_worker, health_worker]
