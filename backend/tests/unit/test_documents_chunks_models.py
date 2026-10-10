import app.db.models  # noqa: F401
from app.db.base import Base
from app.db.models.chunk import EMBEDDING_DIM


def test_documents_and_chunks_tables_exist():
    assert {"documents", "chunks"} <= set(Base.metadata.tables)


def test_document_status_is_restricted():
    table = Base.metadata.tables["documents"]
    names = {c.name for c in table.constraints}
    assert "ck_documents_status" in names


def test_chunk_embedding_dimension_matches_the_model():
    column = Base.metadata.tables["chunks"].c.embedding
    assert column.type.dim == EMBEDDING_DIM == 384
    assert not column.nullable


def test_chunk_has_full_text_column_and_keeps_embedding_model_name():
    columns = Base.metadata.tables["chunks"].c
    assert "tsv" in columns and "embedding_model" in columns
    assert not columns.embedding_model.nullable


def test_chunks_are_unique_per_document_position():
    names = {c.name for c in Base.metadata.tables["chunks"].constraints}
    assert "uq_chunks_document_chunk_index" in names


def test_deleting_a_document_deletes_its_chunks():
    fks = Base.metadata.tables["chunks"].c.document_id.foreign_keys
    assert {fk.ondelete for fk in fks} == {"CASCADE"}
