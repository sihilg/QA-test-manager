from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    TESTER = "TESTER"
    DEV = "DEV"


class TestPriority(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TestType(StrEnum):
    FUNCTIONAL_POSITIVE = "FUNCTIONAL_POSITIVE"
    FUNCTIONAL_NEGATIVE = "FUNCTIONAL_NEGATIVE"
    BLACK_BOX = "BLACK_BOX"
    BOUNDARY_VALUE_ANALYSIS = "BOUNDARY_VALUE_ANALYSIS"


class TestResult(StrEnum):
    NOT_EXECUTED = "NOT_EXECUTED"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class TestOrigin(StrEnum):
    MANUAL = "MANUAL"
    EVA = "EVA"
    AUTOMATION_TOOL = "AUTOMATION_TOOL"


class EvaExchangeStatus(StrEnum):
    PREPARED = "PREPARED"
    EXPORTED = "EXPORTED"
    RESPONSE_IMPORTED = "RESPONSE_IMPORTED"
    FAILED = "FAILED"


class EvaProposalCategory(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    BOUNDARY = "BOUNDARY"


class EvaProposalStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONVERTED = "CONVERTED"


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON}


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("version >= 1", name="ck_user_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    project_memberships: Mapped[list["ProjectMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __mapper_args__ = {"version_id_col": version}


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


class Project(TimestampMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("next_case_sequence >= 1", name="ck_project_next_sequence"),
        CheckConstraint("version >= 1", name="ck_project_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    next_case_sequence: Mapped[int] = mapped_column(Integer, default=1)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)

    test_cases: Mapped[list["TestCase"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    eva_exchanges: Mapped[list["EvaExchange"]] = relationship(back_populates="project")

    __mapper_args__ = {"version_id_col": version}

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None


class ProjectMember(Base):
    __tablename__ = "project_members"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped[Project] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="project_memberships")


class TestCase(TimestampMixin, Base):
    __tablename__ = "test_cases"
    __table_args__ = (
        UniqueConstraint("project_id", "case_number", name="uq_test_case_project_number"),
        UniqueConstraint("project_id", "execution_order", name="uq_test_case_project_order"),
        CheckConstraint("execution_order >= 1", name="ck_test_case_execution_order"),
        CheckConstraint("version >= 1", name="ck_test_case_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), index=True
    )
    case_number: Mapped[str] = mapped_column(String(20))
    execution_order: Mapped[int] = mapped_column(Integer)
    priority: Mapped[TestPriority] = mapped_column(Enum(TestPriority, native_enum=False))
    executor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    execution_date: Mapped[date | None] = mapped_column(Date)
    requirement: Mapped[str] = mapped_column(Text)
    browser: Mapped[str | None] = mapped_column(String(120))
    test_type: Mapped[TestType] = mapped_column(Enum(TestType, native_enum=False))
    title: Mapped[str] = mapped_column(String(240))
    test_data: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    preconditions: Mapped[str] = mapped_column(Text)
    expected_result: Mapped[str] = mapped_column(Text)
    final_result: Mapped[TestResult] = mapped_column(
        Enum(TestResult, native_enum=False), default=TestResult.NOT_EXECUTED
    )
    origin: Mapped[TestOrigin] = mapped_column(Enum(TestOrigin, native_enum=False))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)

    project: Mapped[Project] = relationship(back_populates="test_cases")
    executor: Mapped[User | None] = relationship()
    steps: Mapped[list["TestStep"]] = relationship(
        back_populates="test_case", cascade="all, delete-orphan", order_by="TestStep.position"
    )

    __mapper_args__ = {"version_id_col": version}

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None


class TestStep(TimestampMixin, Base):
    __tablename__ = "test_steps"
    __table_args__ = (
        UniqueConstraint("test_case_id", "position", name="uq_test_step_case_position"),
        CheckConstraint("position >= 1", name="ck_test_step_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    test_case_id: Mapped[int] = mapped_column(
        ForeignKey("test_cases.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(Text)
    expected_result: Mapped[str | None] = mapped_column(Text)

    test_case: Mapped[TestCase] = relationship(back_populates="steps")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), index=True
    )
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )

    actor: Mapped[User | None] = relationship()
    project: Mapped[Project | None] = relationship()


class EvaExchange(TimestampMixin, Base):
    __tablename__ = "eva_exchanges"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), index=True
    )
    requested_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    request_schema_version: Mapped[str] = mapped_column(String(20), default="1.0")
    response_schema_version: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[EvaExchangeStatus] = mapped_column(
        Enum(EvaExchangeStatus, native_enum=False), default=EvaExchangeStatus.PREPARED
    )
    error_code: Mapped[str | None] = mapped_column(String(100))

    project: Mapped[Project] = relationship(back_populates="eva_exchanges")
    requested_by: Mapped[User | None] = relationship()
    proposals: Mapped[list["EvaProposal"]] = relationship(
        back_populates="exchange", cascade="all, delete-orphan"
    )


class EvaProposal(TimestampMixin, Base):
    __tablename__ = "eva_proposals"
    __table_args__ = (
        UniqueConstraint("exchange_id", "proposal_key", name="uq_eva_proposal_exchange_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    exchange_id: Mapped[int] = mapped_column(
        ForeignKey("eva_exchanges.id", ondelete="CASCADE"), index=True
    )
    proposal_key: Mapped[str] = mapped_column(String(120))
    category: Mapped[EvaProposalCategory] = mapped_column(
        Enum(EvaProposalCategory, native_enum=False)
    )
    status: Mapped[EvaProposalStatus] = mapped_column(
        Enum(EvaProposalStatus, native_enum=False), default=EvaProposalStatus.DRAFT
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    converted_test_case_id: Mapped[int | None] = mapped_column(
        ForeignKey("test_cases.id", ondelete="SET NULL"), unique=True
    )

    exchange: Mapped[EvaExchange] = relationship(back_populates="proposals")
    converted_test_case: Mapped[TestCase | None] = relationship()
