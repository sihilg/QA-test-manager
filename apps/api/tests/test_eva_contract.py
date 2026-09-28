import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from qa_test_manager.eva_contract import EvaRequestPackage, EvaResponsePackage

REPOSITORY_ROOT = Path(__file__).parents[3]
EXAMPLES = REPOSITORY_ROOT / "docs" / "eva" / "examples"
SCHEMAS = REPOSITORY_ROOT / "docs" / "eva" / "schemas"


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_fictitious_request_example_matches_contract() -> None:
    request = EvaRequestPackage.model_validate(load_json(EXAMPLES / "request-v1.json"))

    assert request.schema_version == "1.0"
    assert request.project.name == "Loja fictícia"


def test_fictitious_response_example_matches_contract() -> None:
    response = EvaResponsePackage.model_validate(load_json(EXAMPLES / "response-v1.json"))

    assert {proposal.category.value for proposal in response.proposals} == {
        "POSITIVE",
        "NEGATIVE",
        "BOUNDARY",
    }


def test_response_rejects_incompatible_version() -> None:
    payload = load_json(EXAMPLES / "response-v1.json")
    payload["schema_version"] = "2.0"

    with pytest.raises(ValidationError, match="schema_version"):
        EvaResponsePackage.model_validate(payload)


def test_response_rejects_duplicate_proposal_keys() -> None:
    payload = load_json(EXAMPLES / "response-v1.json")
    proposals = payload["proposals"]
    assert isinstance(proposals, list)
    assert isinstance(proposals[0], dict)
    assert isinstance(proposals[1], dict)
    proposals[1]["proposal_key"] = proposals[0]["proposal_key"]

    with pytest.raises(ValidationError, match="proposal_key must be unique"):
        EvaResponsePackage.model_validate(payload)


def test_response_requires_all_three_categories() -> None:
    payload = load_json(EXAMPLES / "response-v1.json")
    proposals = payload["proposals"]
    assert isinstance(proposals, list)
    assert isinstance(proposals[2], dict)
    proposals[2]["category"] = "POSITIVE"

    with pytest.raises(ValidationError, match="positive, negative and boundary"):
        EvaResponsePackage.model_validate(payload)


def test_committed_json_schemas_are_versioned_and_strict() -> None:
    for name in ("request-v1.schema.json", "response-v1.schema.json"):
        schema = load_json(SCHEMAS / name)
        properties = schema["properties"]
        assert isinstance(properties, dict)
        assert properties["schema_version"] == {"const": "1.0"}
        assert schema["additionalProperties"] is False
