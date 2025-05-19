import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler


class CustomRichHandler(RichHandler):
    def emit(self, record: logging.LogRecord) -> None:
        # Only handle exceptions with extras
        if record.exc_info and record.exc_info != (None, None, None):
            # Extract extra fields
            extras = {
                key: value
                for key, value in record.__dict__.items()
                if key not in logging.LogRecord.__dict__
                and key
                not in (
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "message",
                    "taskName",
                    "asctime",
                )
            }

            if extras:
                # Store original state
                original_msg = record.msg
                has_message = hasattr(record, "message")
                original_message = record.message if has_message else None

                # Add extras to the message
                extras_str = " | " + " ".join(f"{k}={v}" for k, v in extras.items())
                record.msg = f"{record.msg}{extras_str}"

                # Clear cached message so it will be regenerated
                if has_message:
                    delattr(record, "message")

                try:
                    super().emit(record)
                finally:
                    # Restore original state
                    record.msg = original_msg
                    if has_message:
                        record.message = original_message  # type: ignore[assignment]
                return

        # Normal processing for non-exception logs
        super().emit(record)


class ExtraFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in logging.LogRecord.__dict__
            and key
            not in (
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "taskName",
                "asctime",
            )
        }
        if extras:
            extras_str = " | " + " ".join(f"{k}={v}" for k, v in extras.items())
            return base + extras_str
        return base


def configure_logging(developer_console: bool, data_dir: Path) -> None:
    """
    Configure the root logger with a custom formatter that includes extra fields.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if developer_console else logging.INFO)
    logger.propagate = False  # TODO: check if it's needed
    logger.handlers.clear()

    data_dir.mkdir(parents=True, exist_ok=True)

    console_handler: logging.Handler
    if developer_console:
        console_handler = CustomRichHandler(rich_tracebacks=True, show_time=True, show_level=True, show_path=False)
        formatter = ExtraFormatter("{name} {message}", style="{")
    else:
        console_handler = logging.StreamHandler()
        formatter = ExtraFormatter("{asctime} - {name} - {levelname} - {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{")
    console_handler.setFormatter(formatter)

    # file logs
    file_handler = RotatingFileHandler(data_dir / "app.log", maxBytes=10 * 1024 * 1024, backupCount=1)
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(
        ExtraFormatter("{asctime} - {name} - {levelname} - {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{")
    )
    logger.addHandler(file_handler)

    # access logger
    access_handler = RotatingFileHandler(data_dir / "access.log", maxBytes=10 * 1024 * 1024, backupCount=1)
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(ExtraFormatter("{asctime} - {levelname} - {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{"))
    access_logger = logging.getLogger("access")
    access_logger.setLevel(logging.INFO)
    access_logger.handlers.clear()
    access_logger.addHandler(access_handler)
    access_logger.propagate = False

    logger.addHandler(console_handler)

    for name in ["mm_std", "pymongo", "python_multipart", "urllib3", "httpcore", "telegram", "httpx"]:
        logging.getLogger(name).setLevel(logging.WARNING)

    logging.getLogger("uvicorn").addHandler(logging.NullHandler())
    logging.getLogger("uvicorn").propagate = False
