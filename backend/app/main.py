from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.queue import redis_lifespan
from app.api.v1 import documents as documents_router

app = FastAPI(title="Heimdall", version="0.1.0")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Redis pool initialized via redis_lifespan
    async with redis_lifespan(app):
        yield
    # Shutdown: redis_lifespan closes pool


app = FastAPI(title="Heimdall", version="0.1.0", lifespan=lifespan)

app.include_router(documents_router.router, prefix="/v1")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
