# -*- coding: utf-8 -*-
"""Centralized runtime diagnostics."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from typing import Any

from config import LOG_DIR

_LOGGER_NAME = "window_workspace"
_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    global _CONFIGURED

    logger = logging.getLogger(_LOGGER_NAME)
    if _CONFIGURED:
        return logger

    os.makedirs(LOG_DIR, exist_ok=True)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "window-workspace.log"),
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    previous_hook = sys.excepthook

    def _exception_hook(exc_type, exc_value, exc_tb):
        logger.critical(
            "unhandled_exception",
            exc_info=(exc_type, exc_value, exc_tb),
        )
        if previous_hook is not sys.__excepthook__:
            previous_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _exception_hook
    _CONFIGURED = True
    return logger


def get_logger(component: str | None = None) -> logging.Logger:
    name = _LOGGER_NAME if not component else f"{_LOGGER_NAME}.{component}"
    return logging.getLogger(name)


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    payload = {"event": event, **fields}
    logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))
