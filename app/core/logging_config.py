import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    root = logging.getLogger("hydra")
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    if root.hasHandlers():
        root.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(root.level)

    if settings.ENVIRONMENT == "prod":
        import json
        from datetime import datetime, timezone

        class JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                if hasattr(record, "request_id"):
                    payload["request_id"] = record.request_id
                return json.dumps(payload, ensure_ascii=False)

        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] %(levelname)-5s %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.addHandler(handler)
