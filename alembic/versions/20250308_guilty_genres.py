"""Add guilty_genres column to music_profiles

Revision ID: 20250308_guilty
Revises: 20250307_ref
Create Date: 2025-03-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250308_guilty"
down_revision: Union[str, None] = "20250307_ref"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    # Check if column already exists (SQLite)
    result = conn.execute(sa.text("PRAGMA table_info('music_profiles')"))
    columns = [row[1] for row in result]
    if "guilty_genres" not in columns:
        op.add_column("music_profiles", sa.Column("guilty_genres", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("music_profiles", "guilty_genres")
