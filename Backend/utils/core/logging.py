from __future__ import annotations

import logging
from typing import Optional

from config.app_config import get_app_config

_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    config = get_app_config()
    logging.basicConfig(
        level=getattr(logging, config.runtime.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


__all__ = ["configure_logging", "get_logger"]
