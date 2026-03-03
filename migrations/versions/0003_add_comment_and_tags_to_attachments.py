"""add comment and tags to attachments

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-03 10:15:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attachments",
        sa.Column("comment", sa.String(), nullable=True),
    )
    op.add_column(
        "attachments",
        sa.Column(
            "tags",
            sa.ARRAY(sa.String()),
            server_default="{}",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("attachments", "tags")
    op.drop_column("attachments", "comment")
