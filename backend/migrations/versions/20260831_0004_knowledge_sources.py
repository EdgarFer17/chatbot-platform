"""Add synchronized knowledge sources and document versions."""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20260831_0004"
down_revision: str | None = "20260831_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("environment_id", sa.Uuid(), nullable=False), sa.Column("assistant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(220), nullable=False),
        sa.Column("source_type", sa.Enum("MANUAL", "FILE", "DOCUMENT_URL", "WEBSITE", name="sourcetype", native_enum=False), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True), sa.Column("allowed_host", sa.String(255), nullable=True),
        sa.Column("sync_status", sa.Enum("PENDING", "SYNCING", "READY", "FAILED", name="syncstatus", native_enum=False), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assistant_id"], ["assistants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_sources_tenant_id", "knowledge_sources", ["tenant_id"])
    op.create_index("ix_knowledge_sources_environment_id", "knowledge_sources", ["environment_id"])
    op.create_index("ix_knowledge_sources_assistant_id", "knowledge_sources", ["assistant_id"])
    op.add_column("knowledge_documents", sa.Column("source_id", sa.Uuid(), nullable=True))
    op.add_column("knowledge_documents", sa.Column("original_url", sa.Text(), nullable=True))
    op.add_column("knowledge_documents", sa.Column("mime_type", sa.String(120), nullable=True))
    op.add_column("knowledge_documents", sa.Column("checksum", sa.String(64), nullable=True))
    op.add_column("knowledge_documents", sa.Column("version_number", sa.Integer(), server_default="1", nullable=False))
    op.add_column("knowledge_documents", sa.Column("is_current", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.create_foreign_key("fk_knowledge_documents_source_id", "knowledge_documents", "knowledge_sources", ["source_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_knowledge_documents_source_id", "knowledge_documents", ["source_id"])
    op.create_index("ix_knowledge_documents_checksum", "knowledge_documents", ["checksum"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_documents_checksum", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_source_id", table_name="knowledge_documents")
    op.drop_constraint("fk_knowledge_documents_source_id", "knowledge_documents", type_="foreignkey")
    for column in ["is_current", "version_number", "checksum", "mime_type", "original_url", "source_id"]:
        op.drop_column("knowledge_documents", column)
    op.drop_table("knowledge_sources")
