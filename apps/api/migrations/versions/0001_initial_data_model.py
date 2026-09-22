"""Create the initial local data model.

Revision ID: 0001_initial_data_model
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_data_model"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = sa.Enum("ADMIN", "TESTER", "DEV", name="userrole", native_enum=False)
test_priority = sa.Enum("HIGH", "MEDIUM", "LOW", name="testpriority", native_enum=False)
test_type = sa.Enum(
    "FUNCTIONAL_POSITIVE",
    "FUNCTIONAL_NEGATIVE",
    "BLACK_BOX",
    "BOUNDARY_VALUE_ANALYSIS",
    name="testtype",
    native_enum=False,
)
test_result = sa.Enum(
    "NOT_EXECUTED", "PASSED", "FAILED", "BLOCKED", name="testresult", native_enum=False
)
test_origin = sa.Enum(
    "MANUAL", "EVA", "AUTOMATION_TOOL", name="testorigin", native_enum=False
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("next_case_sequence", sa.Integer(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("next_case_sequence >= 1", name="ck_project_next_sequence"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "test_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("case_number", sa.String(length=20), nullable=False),
        sa.Column("execution_order", sa.Integer(), nullable=False),
        sa.Column("priority", test_priority, nullable=False),
        sa.Column("executor_id", sa.Integer()),
        sa.Column("execution_date", sa.Date()),
        sa.Column("requirement", sa.Text(), nullable=False),
        sa.Column("browser", sa.String(length=120)),
        sa.Column("test_type", test_type, nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("test_data", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("preconditions", sa.Text(), nullable=False),
        sa.Column("expected_result", sa.Text(), nullable=False),
        sa.Column("final_result", test_result, nullable=False),
        sa.Column("origin", test_origin, nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("execution_order >= 1", name="ck_test_case_execution_order"),
        sa.CheckConstraint("version >= 1", name="ck_test_case_version"),
        sa.ForeignKeyConstraint(["executor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("project_id", "case_number", name="uq_test_case_project_number"),
        sa.UniqueConstraint("project_id", "execution_order", name="uq_test_case_project_order"),
    )
    op.create_index("ix_test_cases_project_id", "test_cases", ["project_id"])

    op.create_table(
        "test_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("test_case_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("expected_result", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("position >= 1", name="ck_test_step_position"),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("test_case_id", "position", name="uq_test_step_case_position"),
    )
    op.create_index("ix_test_steps_test_case_id", "test_steps", ["test_case_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer()),
        sa.Column("project_id", sa.Integer()),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])
    op.create_index("ix_audit_events_project_id", "audit_events", ["project_id"])
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("test_steps")
    op.drop_table("test_cases")
    op.drop_table("projects")
    op.drop_table("users")
