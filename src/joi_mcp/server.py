from contextlib import asynccontextmanager

from fastapi import FastAPI

from joi_mcp.tmdb import mcp as tmdb_mcp
from joi_mcp.transmission import mcp as transmission_mcp

tmdb_app = tmdb_mcp.http_app(path="/")
transmission_app = transmission_mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with tmdb_app.lifespan(tmdb_app):
        async with transmission_app.lifespan(transmission_app):
            yield


app = FastAPI(title="Joi MCP", lifespan=lifespan)
app.mount("/tmdb", tmdb_app)
app.mount("/transmission", transmission_app)


@app.get("/")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import os

    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
