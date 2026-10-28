"""Create multi-tenant platform core."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260831_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("tenants", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("slug", sa.String(80), nullable=False), sa.Column("active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("slug"))
    op.create_index("ix_tenants_slug", "tenants", ["slug"])
    op.create_table("environments", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tenant_id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(120), nullable=False), sa.Column("slug", sa.String(80), nullable=False), sa.Column("kind", sa.Enum("SANDBOX", "PRODUCTION", name="environmentkind", native_enum=False), nullable=False), sa.Column("active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("tenant_id", "slug", name="uq_environment_tenant_slug"))
    op.create_index("ix_environments_tenant_id", "environments", ["tenant_id"])
    op.create_table("assistants", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tenant_id", sa.Uuid(), nullable=False), sa.Column("environment_id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(120), nullable=False), sa.Column("slug", sa.String(80), nullable=False), sa.Column("system_prompt", sa.Text(), nullable=False), sa.Column("active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["environment_id"], ["environments.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("environment_id", "slug", name="uq_assistant_environment_slug"))
    op.create_index("ix_assistants_environment_id", "assistants", ["environment_id"])
    op.create_index("ix_assistants_tenant_id", "assistants", ["tenant_id"])
    op.create_table("api_keys", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tenant_id", sa.Uuid(), nullable=False), sa.Column("environment_id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(120), nullable=False), sa.Column("key_prefix", sa.String(16), nullable=False), sa.Column("key_hash", sa.String(64), nullable=False), sa.Column("active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True), sa.ForeignKeyConstraint(["environment_id"], ["environments.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("key_hash"))
    op.create_index("ix_api_keys_environment_id", "api_keys", ["environment_id"])
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("assistants")
    op.drop_table("environments")
    op.drop_table("tenants")
