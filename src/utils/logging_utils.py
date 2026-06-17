"""Lightweight, consistent logging for every pipeline step.

Using a single helper keeps log formatting identical across modules so the
``run_daily_pipeline.sh`` output reads like one coherent engineering job.
"""
from __future__ import annotations

import logging
import sys

_CONFIGURED = False
_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-22s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a module logger, configuring root handlers once per process.

    Parameters
    ----------
    name:
        Logger name, typically ``__name__`` of the calling module.
    level:
        Logging level for the root configuration.
    """
    global _CONFIGURED
    if not _CONFIGURED:
        logging.basicConfig(
            level=level,
            format=_FORMAT,
            datefmt=_DATEFMT,
            stream=sys.stdout,
        )
        _CONFIGURED = True
    return logging.getLogger(name)


def log_dataframe(logger: logging.Logger, name: str, frame) -> None:
    """Emit a one-line shape/column summary for a DataFrame."""
    logger.info("%s: %d rows x %d cols %s", name, len(frame), frame.shape[1], list(frame.columns))
