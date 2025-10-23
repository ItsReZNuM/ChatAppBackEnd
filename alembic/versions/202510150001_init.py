"""init tables for user/room/message"""
from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = "202510150001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer, primary_key=True),  # group id is the PK, provided by user
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("room_id", sa.Integer, sa.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_messages_room_time", "messages", ["room_id", "created_at"])

def downgrade() -> None:
    op.drop_index("ix_messages_room_time", table_name="messages")
    op.drop_table("messages")
    op.drop_table("rooms")
    op.drop_table("users")
