"Change embedding dimension to 768"
"""
Change embedding dimension to 768 for nomic-embed-text model
Revision ID: 0004_change_embedding_dim_768
Revises: 1c7b70d692aa
Create date: 2026-10-27
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

#Revision identifiers, used by Alembic.
revision:str='0004_change_embedding_dim_768'
down_revision:Union[str,None]='1c7b70d692aa'
branch_labels:Union[str,Sequence[str],None]= None
depends_on :Union[str,Sequence[str],None]=None

#New dimension for the nomic-embed-text 
EMBEDDING_DIM=768

def upgrade() -> None:
    "Delete the existing chunks."
    op.execute("DELETE FROM chunks")

    #Alter the embedding coloumn dimesion
    op.alter_column(
        "chunks",
        "embedding",
        type_=Vector(EMBEDDING_DIM),
        postgresql_using="embedding::vector(768)",
        existing_nullable=False
    )

def downgrade() -> None:
    # DOWNGRADE NOT SAFE: Cannot restore original 384-dim vectors.
    # Data would be lost. This migration is effectively one-way.
    # To "downgrade", you would need to:
    # 1. Drop the chunks table
    # 2. Recreate it with vector(384)
    # 3. Re-ingest all documents with the old model
    # 
    # We implement a structural downgrade only (column type change),
    # but warn that data is already gone from upgrade().
    op.execute("DELETE FROM chunks")
    op.alter_column(
        "chunks",
        "embedding",
        type_=Vector(384),
        existing_nullable=False,
    )