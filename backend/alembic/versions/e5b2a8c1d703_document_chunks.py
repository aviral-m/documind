"""Document indexing: document_chunks with a pgvector column, and index status on documents.

Revision ID: e5b2a8c1d703
Revises: c3d8f2a6e510
Create Date: 2026-11-16 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "e5b2a8c1d703"
down_revision: str | None = "c3d8f2a6e510"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIMENSIONS = 768


def upgrade() -> None:
    # The extension is left in place on downgrade, because other objects may depend on it.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column("documents", sa.Column("index_status", sa.String(length=16), nullable=True))
    op.add_column("documents", sa.Column("index_error", sa.String(length=255), nullable=True))
    op.add_column("documents", sa.Column("chunk_count", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("embedding_model", sa.String(length=100), nullable=True))
    op.add_column("documents", sa.Column("chunk_target_chars", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("chunk_overlap_chars", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_chunk"),
    )
    op.create_index(op.f("ix_document_chunks_document_id"), "document_chunks", ["document_id"])
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_embedding_hnsw", table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_document_id"), table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_column("documents", "indexed_at")
    op.drop_column("documents", "chunk_overlap_chars")
    op.drop_column("documents", "chunk_target_chars")
    op.drop_column("documents", "embedding_model")
    op.drop_column("documents", "chunk_count")
    op.drop_column("documents", "index_error")
    op.drop_column("documents", "index_status")
