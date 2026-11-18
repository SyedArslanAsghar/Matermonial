"""Structured logging with request correlation (doc 07 §17, doc 02 §16).

Log records carry the current request ID. Messages must never contain passwords, OTPs,
tokens, private document contents or full payment credentials (CLAUDE.md CC-R47): callers
log identifiers and outcomes, not payloads.
"""

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIDFilter(logging.Filter):
    """Attach the current request ID (or "-") to every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        return True


class JSONFormatter(logging.Formatter):
    """One JSON object per line: timestamp, level, logger, module, message, request_id."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["error_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def build_logging_config(level: str = "INFO", fmt: str = "json") -> dict:
    formatter = "json" if fmt == "json" else "text"
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"request_id": {"()": "common.logs.RequestIDFilter"}},
        "formatters": {
            "json": {"()": "common.logs.JSONFormatter"},
            "text": {"format": "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "filters": ["request_id"],
                "formatter": formatter,
            }
        },
        "root": {"handlers": ["console"], "level": level},
        "loggers": {
            "django": {"handlers": ["console"], "level": level, "propagate": False},
            "celery": {"handlers": ["console"], "level": level, "propagate": False},
        },
    }
