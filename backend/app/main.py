from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.core.queue import redis_lifespan
from app.api.v1 import documents as documents_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Redis pool initialized via redis_lifespan
    async with redis_lifespan(app):
        yield
    # Shutdown: redis_lifespan closes pool


app = FastAPI(title="Heimdall", version="0.1.0", lifespan=lifespan)

app.include_router(documents_router.router, prefix="/v1")

# Add API Key security scheme to OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
