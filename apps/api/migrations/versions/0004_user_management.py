"""Add optimistic locking for user management.

Revision ID: 0004_user_management
Revises: 0003_project_management
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_user_management"
down_revision: str | None = "0003_project_management"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch_op.create_check_constraint("ck_user_version", "version >= 1")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_user_version", type_="check")
        batch_op.drop_column("version")
