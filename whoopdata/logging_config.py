"""Logging setup shared by the Telegram bot and scheduled entry points."""

from __future__ import annotations

import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# httpx/httpcore log every request URL at INFO. Telegram Bot API URLs embed the
# bot token (https://api.telegram.org/bot<TOKEN>/...), so these must stay at
# WARNING or the token ends up in plaintext log files.
_NOISY_LOGGERS = ("httpx", "httpcore")


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging and silence loggers that leak secrets or spam."""
    logging.basicConfig(level=level, format=LOG_FORMAT)
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
