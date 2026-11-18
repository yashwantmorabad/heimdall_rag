"API key service: generate, hash, verify."

import hashlib
import secrets
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.api_key import ApiKey
from app.core.config import get_settings

KEY_PREFIX = "hk_live_"
KEY_BYTES = 32  # 256 bits

def generate_key() -> tuple[str, str, str]:
    """
    Genarate a new API key.
    
    Reurns:
        (full_key, prefix, key_hash)
        - full_key: shown to user ONCE (e.g., "hk_live_abc123...")
        - key_prefix: stored in DB for identification (e.g., "hk_live_abc123")
        - key_hash: SHA-256 hash stored in DB
    """
    random_part = secrets.token_hex(KEY_BYTES)
    full_key = f"{KEY_PREFIX}{random_part}"
    key_prefix = full_key[:24]  # first 24 chars for identification
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, key_prefix, key_hash

def verify_key(provided_key: str, stored_hash: str) -> bool:
    """
    Verify that the provided API key matches the stored hash.
    
    Args:
        provided_key: The API key provided by the user.
        stored_hash: The SHA-256 hash of the valid API key stored in the database.
    
    Returns:
        True if the provided key is valid, False otherwise.
    """
    if not provided_key or not stored_hash:
        return False
    provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()
    return secrets.compare_digest(provided_hash, stored_hash)

async def create_api_key(
    session: AsyncSession,
    tenant_id: UUID,
    name: str,
    scopes: list[str],
    expires_at: datetime | None = None,
) -> tuple[ApiKey, str]:
    """
    Create a new API key for a tenant in the database.

    Returns:
        (ApiKey, full_key): The created ApiKey object and the full key string (shown to user once).
    """
    # Check active key limit
    settings= get_settings()
    result = await session.execute(
        select(ApiKey).where(
            ApiKey.tenant_id == tenant_id,
            ApiKey.revoked_at.is_(None),
        )
    )
    active_count = len(result.scalars().all())
    if active_count >= settings.max_active_api_keys_per_tenant:
        raise ValueError(f"Maximum active keys per tenant ({settings.max_active_keys_per_tenant}) reached")

    full_key, key_prefix, key_hash = generate_key()

    api_key = ApiKey(
        tenant_id=tenant_id,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=scopes,
        expires_at=expires_at,
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)
    return api_key, full_key

async def get_api_key_by_prefix(session: AsyncSession, key_prefix: str) -> ApiKey | None:
    "Look up API key by prefix (for authentication."
    result = await session.execute(
        select(ApiKey).where(ApiKey.key_prefix == key_prefix)
    )
    return result.scalar_one_or_none()

async def authenticate_api_key(session: AsyncSession, provided_key: str) -> ApiKey | None:
    """
    Authenticate an API key from the X-API-Key header.
    
    Returns the ApiKey if valid, Nane otherwise.
    """
    key_prefix = provided_key[:24]
    api_key = await get_api_key_by_prefix(session, key_prefix)
    if not api_key:
        return None

    # check revoked
    if api_key.revoked_at is not None:
        return None

    # check expired
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        return None

    # verify hash
    if not verify_key(provided_key, api_key.key_hash):
        return None

    # Update last_used_at
    await session.execute(
        update(ApiKey)
        .where(ApiKey.id == api_key.id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    await session.commit()

    return api_key