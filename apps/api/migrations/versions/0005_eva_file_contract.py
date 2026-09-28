"""Add local Eva exchange and proposal records.

Revision ID: 0005_eva_file_contract
Revises: 0004_user_management
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_eva_file_contract"
down_revision: str | None = "0004_user_management"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "eva_exchanges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("request_schema_version", sa.String(length=20), nullable=False),
        sa.Column("response_schema_version", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=17), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_eva_exchanges_project_id", "eva_exchanges", ["project_id"])
    op.create_index("ix_eva_exchanges_public_id", "eva_exchanges", ["public_id"])
    op.create_index(
        "ix_eva_exchanges_requested_by_user_id", "eva_exchanges", ["requested_by_user_id"]
    )

    op.create_table(
        "eva_proposals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exchange_id", sa.Integer(), nullable=False),
        sa.Column("proposal_key", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=9), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("converted_test_case_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["converted_test_case_id"], ["test_cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["exchange_id"], ["eva_exchanges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("converted_test_case_id"),
        sa.UniqueConstraint("exchange_id", "proposal_key", name="uq_eva_proposal_exchange_key"),
    )
    op.create_index("ix_eva_proposals_exchange_id", "eva_proposals", ["exchange_id"])


def downgrade() -> None:
    op.drop_index("ix_eva_proposals_exchange_id", table_name="eva_proposals")
    op.drop_table("eva_proposals")
    op.drop_index("ix_eva_exchanges_requested_by_user_id", table_name="eva_exchanges")
    op.drop_index("ix_eva_exchanges_public_id", table_name="eva_exchanges")
    op.drop_index("ix_eva_exchanges_project_id", table_name="eva_exchanges")
    op.drop_table("eva_exchanges")
