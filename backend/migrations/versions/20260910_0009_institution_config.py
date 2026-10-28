"""Add a single institution binding without changing existing records."""
from alembic import op
import sqlalchemy as sa

revision = "20260910_0009"
down_revision = "20260901_0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("conversation_messages", sa.Column("citations", sa.JSON(), nullable=True))
    op.add_column("conversation_messages", sa.Column("confidence", sa.Float(), nullable=True))
    op.create_table(
        "institution_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assistant_id", sa.Uuid(), sa.ForeignKey("assistants.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("api_key_id", sa.Uuid(), sa.ForeignKey("api_keys.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("welcome_message", sa.Text(), nullable=False),
        sa.Column("accent_color", sa.String(7), nullable=False),
        sa.Column("unavailable_message", sa.Text(), nullable=False),
    )


def downgrade():
    op.drop_table("institution_config")
    op.drop_column("conversation_messages", "confidence")
    op.drop_column("conversation_messages", "citations")
