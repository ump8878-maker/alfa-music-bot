"""add quiz_results, chat rating/owner, user score, listening_time

Revision ID: 20250307_alfa
Revises:
Create Date: 2025-03-07

Добавляет таблицу quiz_results и поля:
- chats: rating, owner_id
- users: score
- music_profiles: listening_time

Для уже существующей БД: выполнить alembic upgrade head.
Для чистой установки: можно удалить data/bot.db и запустить бота (init_db создаст всё).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250307_alfa"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # Таблица результатов квиза (создаём только если ещё нет)
    if "quiz_results" not in insp.get_table_names():
        op.create_table(
            "quiz_results",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("chat_id", sa.BigInteger(), nullable=True),
            sa.Column("answers", sa.JSON(), nullable=True),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(datetime('now'))"), nullable=True),
            sa.ForeignKeyConstraint(["chat_id"], ["chats.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    # Новые поля в chats
    if "chats" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("chats")]
        if "rating" not in cols:
            op.add_column("chats", sa.Column("rating", sa.Float(), nullable=True))
        if "owner_id" not in cols:
            op.add_column("chats", sa.Column("owner_id", sa.BigInteger(), nullable=True))
            op.create_foreign_key("fk_chats_owner_id", "chats", "users", ["owner_id"], ["id"])

    # users.score
    if "users" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("users")]
        if "score" not in cols:
            op.add_column("users", sa.Column("score", sa.Float(), nullable=True))

    # music_profiles.listening_time
    if "music_profiles" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("music_profiles")]
        if "listening_time" not in cols:
            op.add_column("music_profiles", sa.Column("listening_time", sa.String(50), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "music_profiles" in insp.get_table_names() and "listening_time" in [c["name"] for c in insp.get_columns("music_profiles")]:
        op.drop_column("music_profiles", "listening_time")
    if "users" in insp.get_table_names() and "score" in [c["name"] for c in insp.get_columns("users")]:
        op.drop_column("users", "score")
    if "chats" in insp.get_table_names():
        if "owner_id" in [c["name"] for c in insp.get_columns("chats")]:
            op.drop_constraint("fk_chats_owner_id", "chats", type_="foreignkey")
            op.drop_column("chats", "owner_id")
        if "rating" in [c["name"] for c in insp.get_columns("chats")]:
            op.drop_column("chats", "rating")
    if "quiz_results" in insp.get_table_names():
        op.drop_table("quiz_results")
