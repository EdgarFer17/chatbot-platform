"""Replace the previous default green with institutional blue."""
from alembic import op
import sqlalchemy as sa

revision = "20260923_0010"
down_revision = "20260910_0009"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("UPDATE institution_config SET accent_color = '#173b73' WHERE lower(accent_color) = '#174b45'"))


def downgrade():
    # Keep the selected presentation color; no structural change to revert.
    pass
