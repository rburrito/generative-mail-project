"""Central logging configuration.

Call setup_logging() once at process start (main.py does this). Controlled by
environment variables:
    LOG_LEVEL  - DEBUG | INFO (default) | WARNING | ERROR
    LOG_FILE   - optional path; if set, logs are also written there

Logs go to stderr so they never corrupt stdout (which the MCP stdio transport
uses). Named loggers used across the app: genmail.api, genmail.mcp, genmail.rag.
"""

from __future__ import annotations

import logging
import os

_CONFIGURED = False


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    handlers: list[logging.Handler] = [logging.StreamHandler()]  # stderr
    log_file = os.environ.get("LOG_FILE")
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,
    )

    # These are noisy and we log requests / HTTP / indexing ourselves.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

    _CONFIGURED = True
