"Test for store"

from app.db.models import tenant
import pytest
from unittest.mock import AsyncMock,MagicMock
from uuid import UUID

from app.rag.ingestion.chunker import Chunk
from app.rag.ingestion.store import store_chunks

#Fake store test
@pytest.fixture
def sample_chunks():
    "Chunks with embeddings ready for storage."
    return[
        Chunk(
        text="First chunk",
        token_count=10,
        page_number=1,
        chunk_index=0,
        embedding=[0.1]*384,
        embedding_model="test-model"
        ),
        Chunk(
        text="Second chunk",
        token_count=12,
        page_number=1,
        chunk_index=1,
        embedding=[0.1]*384,
        embedding_model="test-model"
        ),
    ]

@pytest.mark.asyncio
async def test_store_chunks_inserts_all(sample_chunks):
    "store_chunks inserts all chunks and returns count."
    #mock session wit execute returning rowconut=1 each time
    mock_session=AsyncMock()
    mock_result=MagicMock()
    mock_result.rowcount=1
    mock_session.execute=AsyncMock(return_value=mock_result)

    tenant_id = UUID("00000000-0000-0000-0000-000000000001")
    document_id = UUID("11111111-1111-1111-1111-111111111111")

    inserted=await store_chunks(mock_session,tenant_id,document_id,sample_chunks)

    assert inserted==2
    assert mock_session.execute.call_count==2
    mock_session.commit.assert_awaited_once()
    
@pytest.mark.asyncio
async def test_store_chunks_handles_conflicts(sample_chunks):
    "store_chunks returns 0 when all chunks conflicts(already exist)."
    mock_session=AsyncMock()
    mock_result=MagicMock()
    mock_result.rowcount=0
    mock_session.execute=AsyncMock(return_value=mock_result)

    
    tenant_id = UUID("00000000-0000-0000-0000-000000000001")
    document_id = UUID("11111111-1111-1111-1111-111111111111")

    inserted= await store_chunks(mock_session,tenant_id,document_id,sample_chunks)

    assert inserted ==0
    assert mock_session.execute.call_count==2
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_score_chunks_empty_list():
    "Empty chunks list returns 0, no DB calls."
    mock_session=AsyncMock()
    inserted = await store_chunks(
        mock_session,
        UUID("00000000-0000-0000-0000-000000000001"),
        UUID("11111111-1111-1111-1111-111111111111"),
        [],
    )

    assert inserted == 0
    mock_session.execute.assert_not_called()
    mock_session.commit.assert_not_awaited()   

# Key points
# AsyncMock -- Mock for async functions
# MagicMock -- Mock object that record calls, returns other mocks.
# mock_result.rowcount=1 -- Simulates INSERT retuning 1 row.
# @pytest.mark.asyncio -- Required for async test functions. 
# mock_session.execute.call_count -- Verifies SQL executed correct number of times. 


