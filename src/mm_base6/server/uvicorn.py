import asyncio
import signal

import uvicorn
from fastapi import FastAPI


async def serve_uvicorn(app: FastAPI, host: str, port: int, log_level: str) -> None:
    # logging.config.dictConfig(LOGGING_CONFIG)

    config = uvicorn.Config(app, host=host, port=port, log_level=log_level)
    server = uvicorn.Server(config)

    # Run with a custom signal handler to gracefully handle Ctrl+C
    original_handler = signal.getsignal(signal.SIGINT)

    def handle_sigint(*_args: object) -> None:
        # Restore the original handler to prevent deadlocks on subsequent Ctrl+C
        signal.signal(signal.SIGINT, original_handler)
        raise KeyboardInterrupt

    # Replace the signal handler temporarily
    signal.signal(signal.SIGINT, handle_sigint)

    try:
        # Run the server normally, which sets up proper lifecycle management
        await server.serve()
    except KeyboardInterrupt:
        # KeyboardInterrupt is expected when Ctrl+C is pressed
        pass
    finally:
        try:  # noqa: SIM105
            # Wrap shutdown in a try/except to catch CancelledError
            await server.shutdown()
        except asyncio.CancelledError:
            # Suppress CancelledError during shutdown
            pass
