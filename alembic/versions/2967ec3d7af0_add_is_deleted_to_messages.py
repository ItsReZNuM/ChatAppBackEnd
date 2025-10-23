"""add is_deleted to messages"""
from alembic import op
import sqlalchemy as sa

revision = "add_is_deleted_messages_001"
down_revision = "279ba50c368f"  
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("messages", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")))

def downgrade() -> None:
    op.drop_column("messages", "is_deleted")
