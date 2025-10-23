"""add edited_at to messages"""
from alembic import op
import sqlalchemy as sa

revision = "202510160001"
down_revision = "202510150001"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("messages", sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column("messages", "edited_at")
