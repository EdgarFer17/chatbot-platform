"""Add embedding vector column to knowledge_chunks for semantic search."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "20261019_0011"
down_revision: str | None = "20260923_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
        op.add_column("knowledge_chunks", sa.Column("embedding", Vector(384), nullable=True))
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)"))
    else:
        op.add_column("knowledge_chunks", sa.Column("embedding", Vector(384), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding"))
    op.drop_column("knowledge_chunks", "embedding")
