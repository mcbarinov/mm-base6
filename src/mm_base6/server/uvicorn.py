import uvicorn
from fastapi import FastAPI


async def serve_uvicorn(app: FastAPI, host: str, port: int, log_level: str) -> None:
    config = uvicorn.Config(app, host=host, port=port, log_level=log_level)
    server = uvicorn.Server(config)
    await server.serve()
