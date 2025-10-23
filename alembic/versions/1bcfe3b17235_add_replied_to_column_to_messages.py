"""add replied_to column to messages"""

from alembic import op
import sqlalchemy as sa


revision = "279ba50c368f"
down_revision = "202510160001"  
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("replied_to", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_messages_replied_to_messages",
        "messages",
        "messages",
        ["replied_to"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_messages_replied_to_messages", "messages", type_="foreignkey")
    op.drop_column("messages", "replied_to")
