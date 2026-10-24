"""add_unique_tenant_filename_to_documents

Revision ID: 1c7b70d692aa
Revises: 0003_documents_chunks
Create Date: 2026-10-24 01:09:16.064423
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c7b70d692aa'
down_revision: Union[str, None] = '0003_documents_chunks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_documents_tenant_filename",
        "documents",
        ["tenant_id", "filename"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_documents_tenant_filename",
        "documents",
        type_="unique",
    )
