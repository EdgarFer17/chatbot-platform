"""Add persistent knowledge synchronization jobs."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260831_0005"
down_revision: str | None = "20260831_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_sync_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("environment_id", sa.Uuid(), nullable=False),
        sa.Column("assistant_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED", name="syncjobstatus", native_enum=False), nullable=False),
        sa.Column("discovered", sa.Integer(), nullable=False),
        sa.Column("processed", sa.Integer(), nullable=False),
        sa.Column("created", sa.Integer(), nullable=False),
        sa.Column("unchanged", sa.Integer(), nullable=False),
        sa.Column("failed", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assistant_id"], ["assistants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_sync_jobs_tenant_id", "knowledge_sync_jobs", ["tenant_id"])
    op.create_index("ix_knowledge_sync_jobs_environment_id", "knowledge_sync_jobs", ["environment_id"])
    op.create_index("ix_knowledge_sync_jobs_assistant_id", "knowledge_sync_jobs", ["assistant_id"])
    op.create_index("ix_knowledge_sync_jobs_source_id", "knowledge_sync_jobs", ["source_id"])
    op.create_index("ix_knowledge_sync_jobs_status", "knowledge_sync_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("knowledge_sync_jobs")
