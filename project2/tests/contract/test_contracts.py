from __future__ import annotations

import math

import pytest
from pydantic import ValidationError
from tests.helpers import make_case, make_handoff

from chimera_task1.contracts.decision_handoff import (
    DecisionConfidence,
    Task1NormalizedFeatures,
)
from chimera_task1.contracts.output import (
    Task1DecisionOutput,
    Task1ReasoningOutputV1,
    Task1VariableWeightsV1,
)
from chimera_task1.testing.fake_decision_service import FakeDecisionScenario


def test_handoff_round_trip_and_strict_failure_cases() -> None:
    handoff = make_handoff()
    assert type(handoff).model_validate_json(handoff.model_dump_json()) == handoff

    payload = make_case().model_dump()
    payload["ground_truth"] = "yes"
    with pytest.raises(ValidationError):
        Task1NormalizedFeatures.model_validate(payload)
    payload = make_case().model_dump()
    payload["psa"] = math.nan
    with pytest.raises(ValidationError):
        Task1NormalizedFeatures.model_validate(payload)


@pytest.mark.parametrize("value", ["yes", "no"])
def test_decision_output_is_a_json_string(value: str) -> None:
    output = Task1DecisionOutput.model_validate_json(f'"{value}"')
    assert output.model_dump_json() == f'"{value}"'


def test_reasoning_has_exact_keys_and_rejects_private_fields() -> None:
    output = Task1ReasoningOutputV1(
        confidence=DecisionConfidence.CLEAR,
        variable_weights=Task1VariableWeightsV1(),
        free_text="A prostate biopsy is recommended now.",
        reveal_sequence=(),
    )
    assert set(output.model_dump()) == {
        "confidence",
        "variable_weights",
        "free_text",
        "reveal_sequence",
    }
    payload = output.model_dump()
    payload["probability_yes"] = 0.9
    with pytest.raises(ValidationError):
        Task1ReasoningOutputV1.model_validate(payload)


def test_fake_artifact_mismatch_is_a_valid_routed_handoff() -> None:
    handoff = make_handoff(FakeDecisionScenario.ARTIFACT_MISMATCH)
    assert handoff.routing_reasons[0].value == "artifact_policy_mismatch"
