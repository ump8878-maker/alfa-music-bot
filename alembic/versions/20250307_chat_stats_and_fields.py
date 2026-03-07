"""chat_stats table, chats.owner_username/updated_at, chat_members.last_activity_at

Revision ID: 20250307_stats
Revises: 20250307_alfa
Create Date: 2025-03-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250307_stats"
down_revision: Union[str, None] = "20250307_alfa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # chat_stats
    if "chat_stats" not in insp.get_table_names():
        op.create_table(
            "chat_stats",
            sa.Column("chat_id", sa.BigInteger(), nullable=False),
            sa.Column("rating", sa.Float(), nullable=True),
            sa.Column("profile_name", sa.String(255), nullable=True),
            sa.Column("top_genres", sa.JSON(), nullable=True),
            sa.Column("top_artists", sa.JSON(), nullable=True),
            sa.Column("participants_count", sa.Integer(), nullable=True),
            sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_growth_message_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(datetime('now'))"), nullable=True),
            sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("chat_id"),
        )

    # chats.owner_username, chats.updated_at
    if "chats" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("chats")]
        if "owner_username" not in cols:
            op.add_column("chats", sa.Column("owner_username", sa.String(255), nullable=True))
        if "updated_at" not in cols:
            op.add_column("chats", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    # chat_members.last_activity_at
    if "chat_members" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("chat_members")]
        if "last_activity_at" not in cols:
            op.add_column("chat_members", sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_table("chat_stats")
    op.drop_column("chats", "owner_username")
    op.drop_column("chats", "updated_at")
    op.drop_column("chat_members", "last_activity_at")
