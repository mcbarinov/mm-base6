from __future__ import annotations

import anyio

from mm_base6.core.config import CoreConfig


class LogfileService:
    """Service for managing application and access log files.

    Provides operations to read, clean, and get size information for
    the framework's log files. Handles both application logs (Python logging)
    and access logs (HTTP requests from uvicorn/FastAPI).
    """

    def __init__(self, core_config: CoreConfig) -> None:
        self.logfile_app = anyio.Path(core_config.data_dir / "app.log")
        self.logfile_access = anyio.Path(core_config.data_dir / "access.log")

    async def read_logfile(self, file: str) -> str:
        """Read the contents of a log file.

        Args:
            file: Log file type, either "app" or "access"

        Returns:
            Complete log file contents as string

        Raises:
            ValueError: If file type is not "app" or "access"
        """
        if file == "app":
            return await self.logfile_app.read_text(encoding="utf-8")
        if file == "access":
            return await self.logfile_access.read_text(encoding="utf-8")
        raise ValueError(f"Unknown logfile: {file}")

    async def clean_logfile(self, file: str) -> None:
        """Clear the contents of a log file.

        Args:
            file: Log file type, either "app" or "access"

        Raises:
            ValueError: If file type is not "app" or "access"
        """
        if file == "app":
            await self.logfile_app.write_text("", encoding="utf-8")
            return
        if file == "access":
            await self.logfile_access.write_text("", encoding="utf-8")
            return
        raise ValueError(f"Unknown logfile: {file}")

    async def get_logfile_size(self, file: str) -> int:
        """Get the size of a log file in bytes.

        Args:
            file: Log file type, either "app" or "access"

        Returns:
            File size in bytes

        Raises:
            ValueError: If file type is not "app" or "access"
        """
        if file == "app":
            return (await self.logfile_app.stat()).st_size
        if file == "access":
            return (await self.logfile_access.stat()).st_size
        raise ValueError(f"Unknown logfile: {file}")
