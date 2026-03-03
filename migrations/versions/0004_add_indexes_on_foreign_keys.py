"""add indexes on foreign keys

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-03 13:10:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"]
    )
    op.create_index(
        "ix_attachment_files_attachment_id", "attachment_files", ["attachment_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_attachment_files_attachment_id", table_name="attachment_files")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
