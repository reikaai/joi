from contextlib import asynccontextmanager

from fastapi import FastAPI

from joi_mcp.jackett import mcp as jackett_mcp
from joi_mcp.tmdb import mcp as tmdb_mcp
from joi_mcp.transmission import mcp as transmission_mcp

jackett_app = jackett_mcp.http_app(path="/")
tmdb_app = tmdb_mcp.http_app(path="/")
transmission_app = transmission_mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with jackett_app.lifespan(jackett_app):
        async with tmdb_app.lifespan(tmdb_app):
            async with transmission_app.lifespan(transmission_app):
                yield


app = FastAPI(title="Joi MCP", lifespan=lifespan)
app.mount("/jackett", jackett_app)
app.mount("/tmdb", tmdb_app)
app.mount("/transmission", transmission_app)


@app.get("/")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    from joi_mcp.config import settings

    uvicorn.run(app, host=settings.host, port=settings.port)
