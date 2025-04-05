import logging

from mm_std import configure_structlog


def configure_logger() -> None:
    logging.getLogger("pymongo").setLevel(logging.WARNING)

    configure_structlog()
