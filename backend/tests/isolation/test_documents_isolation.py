import pytest
import pytest_asyncio
from uuid import UUID, uuid4
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession


from app.main import app
from app.services.keys import create_api_key
from app.db.models.document import Document
from app.db.models.tenant import Tenant
from tests.conftest import AsyncTestSessionLocal


TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("22222222-2222-2222-2222-222222222222")


@pytest_asyncio.fixture
async def isolation_setup(db_session: AsyncSession):
    """Create two tenants with API keys and a document for Tenant A."""
    # Create tenants
    db_session.add_all([
        Tenant(id=TENANT_A, name="Tenant A"),
        Tenant(id=TENANT_B, name="Tenant B"),
    ])
    await db_session.commit()

    # Create API keys for both tenants
    key_a, full_key_a = await create_api_key(
        db_session, TENANT_A, "Key A", ["documents", "query"]
    )
    key_b, full_key_b = await create_api_key(
        db_session, TENANT_B, "Key B", ["documents", "query"]
    )
    await db_session.commit()

    # Create a document for Tenant A
    doc_a = Document(
        id=uuid4(),
        tenant_id=TENANT_A,
        filename="tenant_a_doc.pdf",
        status="ready",
    )
    db_session.add(doc_a)
    await db_session.commit()

    yield {
        "key_a": full_key_a,
        "key_b": full_key_b,
        "doc_a_id": doc_a.id,
    }


async def test_tenant_b_cannot_list_tenant_a_documents(isolation_setup):
    """Tenant B's key cannot see Tenant A's documents."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/v1/documents",
            headers={"X-API-Key": isolation_setup["key_b"]},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["documents"] == []  # Tenant B sees empty list


async def test_tenant_b_cannot_get_tenant_a_document(isolation_setup):
    """Tenant B's key gets 404 for Tenant A's document."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/v1/documents/{isolation_setup['doc_a_id']}",
            headers={"X-API-Key": isolation_setup["key_b"]},
        )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "not_found"


async def test_tenant_b_cannot_delete_tenant_a_document(isolation_setup):
    """Tenant B's key gets 404 when trying to delete Tenant A's document."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            f"/v1/documents/{isolation_setup['doc_a_id']}",
            headers={"X-API-Key": isolation_setup["key_b"]},
        )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "not_found"


async def test_tenant_a_can_access_own_document(isolation_setup):
    """Tenant A can list, get, and delete their own document."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # List
        response = await client.get(
            "/v1/documents",
            headers={"X-API-Key": isolation_setup["key_a"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) == 1
        assert data["documents"][0]["document_id"] == str(isolation_setup["doc_a_id"])

        # Get
        response = await client.get(
            f"/v1/documents/{isolation_setup['doc_a_id']}",
            headers={"X-API-Key": isolation_setup["key_a"]},
        )
        assert response.status_code == 200
        assert response.json()["document_id"] == str(isolation_setup["doc_a_id"])

        # Delete
        response = await client.delete(
            f"/v1/documents/{isolation_setup['doc_a_id']}",
            headers={"X-API-Key": isolation_setup["key_a"]},
        )
        assert response.status_code == 204

        # Verify gone
        response = await client.get(
            f"/v1/documents/{isolation_setup['doc_a_id']}",
            headers={"X-API-Key": isolation_setup["key_a"]},
        )
        assert response.status_code == 404


async def test_revoked_key_fails(isolation_setup, db_session: AsyncSession):
    """Revoked API key returns 401."""
    # Revoke key_a
    from sqlalchemy import update
    from app.db.models.api_key import ApiKey
    from datetime import datetime, timezone
    await db_session.execute(
        update(ApiKey)
        .where(ApiKey.key_prefix == isolation_setup["key_a"][:24])
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/v1/documents",
            headers={"X-API-Key": isolation_setup["key_a"]},
        )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "unauthorized"


async def test_wrong_scope_fails(isolation_setup):
    """API key without 'documents' scope returns 403."""
    # Create key with only 'query' scope
    async with AsyncTestSessionLocal() as session:
        key_c, full_key_c = await create_api_key(
            session, TENANT_A, "Key C", ["query"]  # No 'documents' scope
        )
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/v1/documents",
            headers={"X-API-Key": full_key_c},
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "forbidden"
    assert "documents" in response.json()["detail"]["message"]