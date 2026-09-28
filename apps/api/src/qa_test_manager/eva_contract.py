from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

EVA_SCHEMA_VERSION: Literal["1.0"] = "1.0"

ShortText = Annotated[str, Field(min_length=1, max_length=240)]
LongText = Annotated[str, Field(min_length=1, max_length=20_000)]


class EvaSourceKind(StrEnum):
    FREE_TEXT = "FREE_TEXT"
    DOCUMENT_TEXT = "DOCUMENT_TEXT"


class EvaProposalCategory(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    BOUNDARY = "BOUNDARY"


class StrictContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvaProjectReference(StrictContractModel):
    id: int = Field(gt=0)
    name: ShortText


class EvaSource(StrictContractModel):
    kind: EvaSourceKind
    title: ShortText
    content: LongText


class EvaGenerationRules(StrictContractModel):
    language: Literal["pt-PT"] = "pt-PT"
    required_categories: list[EvaProposalCategory] = Field(
        default_factory=lambda: list(EvaProposalCategory), min_length=3, max_length=3
    )
    maximum_proposals: int = Field(default=30, ge=3, le=100)

    @model_validator(mode="after")
    def include_every_category_once(self) -> "EvaGenerationRules":
        if set(self.required_categories) != set(EvaProposalCategory):
            raise ValueError("required_categories must contain POSITIVE, NEGATIVE and BOUNDARY")
        return self


class EvaRequestPackage(StrictContractModel):
    schema_version: Literal["1.0"] = EVA_SCHEMA_VERSION
    exchange_id: UUID
    exported_at: datetime
    project: EvaProjectReference
    source: EvaSource
    generation_rules: EvaGenerationRules = Field(default_factory=EvaGenerationRules)


class EvaProposalStep(StrictContractModel):
    position: int = Field(gt=0)
    action: LongText
    expected_result: LongText


class EvaProposalPayload(StrictContractModel):
    proposal_key: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{0,119}$")]
    category: EvaProposalCategory
    title: ShortText
    requirement: LongText
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    test_type: Literal[
        "FUNCTIONAL_POSITIVE",
        "FUNCTIONAL_NEGATIVE",
        "BLACK_BOX",
        "BOUNDARY_VALUE_ANALYSIS",
    ]
    test_data: LongText
    description: LongText
    preconditions: LongText
    expected_result: LongText
    steps: list[EvaProposalStep] = Field(min_length=1, max_length=100)
    assumptions: list[ShortText] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def positions_are_sequential(self) -> "EvaProposalPayload":
        if [step.position for step in self.steps] != list(range(1, len(self.steps) + 1)):
            raise ValueError("step positions must be sequential and start at 1")
        return self


class EvaResponsePackage(StrictContractModel):
    schema_version: Literal["1.0"] = EVA_SCHEMA_VERSION
    exchange_id: UUID
    generated_at: datetime
    proposals: list[EvaProposalPayload] = Field(min_length=3, max_length=100)
    warnings: list[ShortText] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_proposal_set(self) -> "EvaResponsePackage":
        keys = [proposal.proposal_key for proposal in self.proposals]
        if len(keys) != len(set(keys)):
            raise ValueError("proposal_key must be unique inside an exchange")
        if not set(EvaProposalCategory).issubset(
            {proposal.category for proposal in self.proposals}
        ):
            raise ValueError("response must include positive, negative and boundary proposals")
        return self
