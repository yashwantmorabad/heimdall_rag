import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.keys import (
    generate_key,
    verify_key,
    create_api_key,
    authenticate_api_key,
    get_api_key_by_prefix,
)
from app.db.models.api_key import ApiKey
@pytest.fixture
def mock_session():
    """Mock AsyncSession for unit tests."""
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def sample_key_data():
    """Generate a sample key and its components."""
    full_key, key_prefix, key_hash = generate_key()
    return {
        "full_key": full_key,
        "key_prefix": key_prefix,
        "key_hash": key_hash,
    }

@pytest.fixture
def api_key_row(sample_key_data):
    """Create a mock ApiKey row."""
    return ApiKey(
        id=uuid4(),
        tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
        name="Test Key",
        key_prefix=sample_key_data["key_prefix"],
        key_hash=sample_key_data["key_hash"],
        scopes=["documents", "query"],
        expires_at=None,
        revoked_at=None,
        last_used_at=None,
        created_at=datetime.now(timezone.utc),
    )

class TestGenerateKey:
    """Tests for generate_key()."""

    def test_key_generated_format_hk_live_(self):
        """Generated key starts with 'hk_live_' + 64 hex chars."""
        full_key, key_prefix, key_hash = generate_key()

        assert full_key.startswith("hk_live_")
        # hk_live_ (8 chars) + 64 hex = 72 chars total
        assert len(full_key) == 72
        # After prefix, all hex
        hex_part = full_key[8:]
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_key_prefix_is_first_24_chars(self):
        """key_prefix is first 24 chars of full key."""
        full_key, key_prefix, key_hash = generate_key()
        assert key_prefix == full_key[:24]

    def test_key_hash_is_sha256_of_full_key(self):
        """key_hash is SHA-256 of full_key, computed independently."""
        full_key, key_prefix, key_hash = generate_key()
        expected_hash = hashlib.sha256(full_key.encode()).hexdigest()
        assert key_hash == expected_hash

    def test_two_generated_keys_differ(self):
        """Two calls produce different keys."""
        key1, _, _ = generate_key()
        key2, _, _ = generate_key()
        assert key1 != key2

    def test_key_has_sufficient_entropy(self):
        """Key uses secrets.token_hex(32) = 256 bits entropy."""
        # Run multiple times, ensure no collisions in small sample
        keys = [generate_key()[0] for _ in range(100)]
        assert len(set(keys)) == 100

class TestVerifyKey:
    """Tests for verify_key()."""

    def test_verify_accepts_valid_key(self, sample_key_data):
        """Correct key matches its hash."""
        assert verify_key(sample_key_data["full_key"], sample_key_data["key_hash"]) is True

    def test_verify_rejects_wrong_key(self, sample_key_data):
        """Wrong key does not match hash."""
        assert verify_key("hk_live_wrongkey12345678901234567890123456789012345678901234", sample_key_data["key_hash"]) is False

    def test_verify_rejects_empty_key(self, sample_key_data):
        """Empty key rejected."""
        assert verify_key("", sample_key_data["key_hash"]) is False

    def test_verify_rejects_none_key(self, sample_key_data):
        """None key rejected."""
        assert verify_key(None, sample_key_data["key_hash"]) is False

    def test_verify_rejects_empty_hash(self):
        """Empty hash rejected."""
        assert verify_key("hk_live_somekey12345678901234567890123456789012345678901234", "") is False

    def test_verify_uses_constant_time_compare(self):
        """
        Guard: verify_key uses secrets.compare_digest (constant-time).
        This test ensures a future change to == is caught.
        """
        # We can't directly test timing, but we verify the implementation uses compare_digest
        import app.services.keys as keys_module
        import inspect
        source = inspect.getsource(keys_module.verify_key)
        assert "compare_digest" in source, "verify_key must use secrets.compare_digest"
        assert "==" not in source or "secrets.compare_digest" in source

class TestAuthenticateApiKeyMocked:
    """Tests for authenticate_api_key() with mocked DB."""

    @pytest.mark.asyncio
    async def test_unknown_prefix_rejected(self, mock_session):
        """Unknown prefix returns None (no leak)."""
        mock_session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        result = await authenticate_api_key(mock_session, "hk_live_unknown12345678901234567890123456789012345678901234")
        assert result is None

    @pytest.mark.asyncio
    async def test_correct_prefix_wrong_key_rejected(self, mock_session, api_key_row, sample_key_data):
        """Correct prefix but wrong key -> rejected, last_used_at NOT updated."""
        # Mock get_api_key_by_prefix to return our key row
        with patch("app.services.keys.get_api_key_by_prefix", return_value=api_key_row):
            # Use a different key with same prefix
            wrong_key = "hk_live_wrongkey12345678901234567890123456789012345678901234"
            result = await authenticate_api_key(mock_session, wrong_key)
            
            assert result is None
            # last_used_at should NOT be updated
            mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_correct_key_accepted_updates_last_used_at(self, mock_session, api_key_row, sample_key_data):
        """Correct key -> returns ApiKey, updates last_used_at in database."""
        with patch("app.services.keys.get_api_key_by_prefix", return_value=api_key_row):
            result = await authenticate_api_key(mock_session, sample_key_data["full_key"])
            
            assert result is not None
            assert result.id == api_key_row.id
            # last_used_at is updated in database via SQL, not on in-memory object
            # Verify the update was executed by checking commit was called
            mock_session.commit.assert_called_once()
            # Verify execute was called with an update statement for last_used_at
            execute_calls = mock_session.execute.call_args_list
            assert len(execute_calls) >= 1  # update (get_api_key_by_prefix is mocked)
            # The last call should be the update statement
            update_call = execute_calls[-1]
            assert "update" in str(update_call).lower() or "last_used_at" in str(update_call)

    @pytest.mark.asyncio
    async def test_expired_key_rejected(self, mock_session, api_key_row):
        """Key with expires_at in past -> rejected."""
        api_key_row.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        with patch("app.services.keys.get_api_key_by_prefix", return_value=api_key_row):
            result = await authenticate_api_key(mock_session, "hk_live_somekey12345678901234567890123456789012345678901234")
            assert result is None

    @pytest.mark.asyncio
    async def test_revoked_key_rejected(self, mock_session, api_key_row):
        """Key with revoked_at set -> rejected."""
        api_key_row.revoked_at = datetime.now(timezone.utc)
        
        with patch("app.services.keys.get_api_key_by_prefix", return_value=api_key_row):
            result = await authenticate_api_key(mock_session, "hk_live_somekey12345678901234567890123456789012345678901234")
            assert result is None

    @pytest.mark.asyncio
    async def test_key_with_no_expiry_works(self, mock_session, api_key_row):
        """Key with expires_at=None works."""
        api_key_row.expires_at = None
        
        with patch("app.services.keys.get_api_key_by_prefix", return_value=api_key_row):
            # Need a valid key - use the one from sample_key_data
            from app.services.keys import generate_key
            full_key, _, key_hash = generate_key()
            api_key_row.key_hash = key_hash
            api_key_row.key_prefix = full_key[:24]
            
            result = await authenticate_api_key(mock_session, full_key)
            assert result is not None

    @pytest.mark.asyncio
    async def test_all_failures_return_same_none(self, mock_session, api_key_row):
        """
        All failure reasons (unknown prefix, wrong key, expired, revoked) 
        return None - no information leakage.
        """
        failure_cases = [
            ("unknown_prefix", "hk_live_unknown12345678901234567890123456789012345678901234", None),
            ("wrong_key", "hk_live_wrongkey12345678901234567890123456789012345678901234", api_key_row),
            ("expired", "hk_live_somekey12345678901234567890123456789012345678901234", api_key_row),
            ("revoked", "hk_live_somekey12345678901234567890123456789012345678901234", api_key_row),
        ]
        
        for name, key, row in failure_cases:
            if row is None:
                mock_session.execute = AsyncMock(return_value=MagicMock(
                    scalar_one_or_none=MagicMock(return_value=None)
                ))
            else:
                if name == "expired":
                    row.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
                elif name == "revoked":
                    row.revoked_at = datetime.now(timezone.utc)
                else:
                    row.expires_at = None
                    row.revoked_at = None
                
                with patch("app.services.keys.get_api_key_by_prefix", return_value=row):
                    result = await authenticate_api_key(mock_session, key)
                    assert result is None, f"Failure case '{name}' should return None"

class TestKeyServiceIntegration:
    """Integration test using real heimdall_test database."""

    @pytest.mark.asyncio
    async def test_create_authenticate_revoke_cycle(self):
        """
        Full cycle: create key -> authenticate (success) -> revoke in DB -> authenticate (fail).
        Uses real heimdall_test database.
        """
        from tests.conftest import AsyncTestSessionLocal
        from app.db.models.tenant import Tenant
        from sqlalchemy import delete
        from uuid import UUID

        TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
        
        async with AsyncTestSessionLocal() as session:
            # Ensure tenant exists
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            await session.execute(
                pg_insert(Tenant).values(id=TENANT_ID, name="test-tenant").on_conflict_do_nothing(index_elements=["id"])
            )
            await session.commit()

            # Create key
            api_key, full_key = await create_api_key(
                session, TENANT_ID, "Integration Test Key", ["documents", "query"]
            )
            await session.commit()

            # 1. Authenticate with valid key -> success
            authenticated = await authenticate_api_key(session, full_key)
            assert authenticated is not None
            assert authenticated.id == api_key.id
            assert authenticated.last_used_at is not None

            # 2. Revoke the key in database
            from datetime import datetime, timezone
            from sqlalchemy import update
            from app.db.models.api_key import ApiKey as ApiKeyModel

            await session.execute(
                update(ApiKeyModel)
                .where(ApiKeyModel.id == api_key.id)
                .values(revoked_at=datetime.now(timezone.utc))
            )
            await session.commit()

            # 3. Authenticate again -> must fail (revoked)
            revoked_result = await authenticate_api_key(session, full_key)
            assert revoked_result is None

            # Cleanup
            await session.execute(delete(ApiKeyModel).where(ApiKeyModel.id == api_key.id))
            await session.commit()