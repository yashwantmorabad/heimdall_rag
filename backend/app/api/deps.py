"FastAPI dependencies: authentication, tenant resolution."

from uuid import UUID
from typing import Annotated

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.keys import authenticate_api_key
from app.db.models.api_key import ApiKey

async def get_api_key(
        x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
        session: AsyncSession = Depends(get_session),
    ) -> ApiKey:
    """
    Extract and validate API key from X-API-Key header.

    Returns the authenticated ApiKey model 
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Invalid or revoked API-Key."},
        )
    return api_key

def require_scope(required_scope: str):
    """
    Dependency factory: require a specific scope on the authenticated API key.
    
    Usage:
        @router.post("/documents,dependencies=[require_scope("documents")])
    """
    async def _check_scope(api_key: ApiKey = Depends(get_api_key)) -> ApiKey:
        if required_scope not in api_key.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "forbidden", "message": f"API key does not have required scope: {required_scope}."},
            )
        return api_key
    return _check_scope

async def _get_tenant_id(api_key: ApiKey = Depends(get_api_key)) -> UUID:
    "Extract the tenant_id from the authenticated API key."
    return api_key.tenant_id

from fastapi import Depends, Request

async def get_redis_pool(request: Request):
    "Dependency to get Redis pool from app state."
    return request.app.state.redis

__all__ = ["get_api_key", "require_scope", "_get_tenant_id", "get_redis_pool"]