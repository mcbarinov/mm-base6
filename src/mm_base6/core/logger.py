import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler


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
    logger.handlers.clear()

    console_handler: logging.Handler

    if developer_console:
        console_handler = RichHandler(rich_tracebacks=True, show_time=True, show_level=True, show_path=False)
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

    logger.addHandler(console_handler)

    for name in ["mm_std", "pymongo"]:
        logging.getLogger(name).setLevel(logging.WARNING)

    logging.getLogger("uvicorn").propagate = False
