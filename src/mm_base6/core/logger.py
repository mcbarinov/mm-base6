import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog


# Custom filter to allow only INFO level messages
class InfoFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == logging.INFO


def configure_logger(debug: bool, logs_dir: Path) -> None:
    """
    Configures logging for the application with different handlers based on the debug mode.

    :param debug: Boolean flag indicating if the application is in debug mode.
    :param logs_dir: Path to the directory where log files will be stored.

    Console logs are rendered using structlog processors.
    File logs are rotated automatically when they exceed 10 MB.
    """
    # Ensure logs directory exists
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Clear existing handlers from the root logger
    root_logger: logging.Logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # --------------------------
    # Configure Console Handler
    # --------------------------
    console_handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
    if debug:
        # For development: colorful and detailed logs
        console_processor = structlog.dev.ConsoleRenderer(colors=True)
        console_level: int = logging.DEBUG
    else:
        # For production: plain logs without colors
        console_processor = structlog.processors.KeyValueRenderer(key_order=["timestamp", "level", "event"])
        console_level = logging.INFO

    console_formatter: structlog.stdlib.ProcessorFormatter = structlog.stdlib.ProcessorFormatter(
        processor=console_processor,
        foreign_pre_chain=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ],
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(console_level)

    # --------------------------
    # Configure Info File Handler
    # --------------------------
    info_log_path: Path = logs_dir / "info.log"
    info_file_handler: RotatingFileHandler = RotatingFileHandler(
        str(info_log_path), maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.addFilter(InfoFilter())
    info_formatter: structlog.stdlib.ProcessorFormatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ],
    )
    info_file_handler.setFormatter(info_formatter)

    # ---------------------------
    # Configure Error File Handler
    # ---------------------------
    error_log_path: Path = logs_dir / "error.log"
    error_file_handler: RotatingFileHandler = RotatingFileHandler(
        str(error_log_path), maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    error_file_handler.setLevel(logging.WARNING)
    error_formatter: structlog.stdlib.ProcessorFormatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.KeyValueRenderer(key_order=["timestamp", "level", "event"]),
        foreign_pre_chain=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ],
    )
    error_file_handler.setFormatter(error_formatter)

    # ---------------------------
    # Setup Root Logger and Handlers
    # ---------------------------
    root_logger.setLevel(console_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(info_file_handler)
    root_logger.addHandler(error_file_handler)

    # ---------------------------
    # Configure structlog
    # ---------------------------
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Disable some library loggers
    logging.getLogger("pymongo").setLevel(logging.WARNING)


