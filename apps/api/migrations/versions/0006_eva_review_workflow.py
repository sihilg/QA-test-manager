"""Persist Eva request packages.

Revision ID: 0006_eva_review_workflow
Revises: 0005_eva_file_contract
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_eva_review_workflow"
down_revision: str | None = "0005_eva_file_contract"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "eva_exchanges",
        sa.Column("request_payload", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("eva_exchanges", "request_payload")
