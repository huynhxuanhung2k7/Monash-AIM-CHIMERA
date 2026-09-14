from __future__ import annotations

import os
from pathlib import Path

import pytest
from tests.helpers import accepted_outcome, make_handoff

from chimera_task1.arbitration import DecisionArbiter
from chimera_task1.contracts.adjudication import Stage3OutcomeV1
from chimera_task1.contracts.arbitration import DecisionArbitrationResultV1
from chimera_task1.contracts.decision_handoff import (
    BiopsyDecision,
    DecisionConfidence,
    DecisionHandoffV1,
)
from chimera_task1.contracts.output import (
    Task1DecisionOutput,
    Task1ReasoningOutputV1,
    VariableWeight,
)
from chimera_task1.contracts.reasoning import ReasoningPlanV1
from chimera_task1.evaluation import load_official_outputs
from chimera_task1.reasoning import (
    ReasoningPlanner,
    ReasoningRenderer,
    Stage5ValidationError,
    Stage5Validator,
)
from chimera_task1.runtime.serializer import Task1OutputSerializer
from chimera_task1.testing.fake_decision_service import FakeDecisionScenario


def build_stage5(
    scenario: FakeDecisionScenario = FakeDecisionScenario.LOW_MARGIN,
) -> tuple[
    DecisionHandoffV1,
    Stage3OutcomeV1,
    DecisionArbitrationResultV1,
    ReasoningPlanV1,
    Task1DecisionOutput,
    Task1ReasoningOutputV1,
]:
    handoff = make_handoff(scenario)
    outcome = accepted_outcome(handoff)
    arbitration = DecisionArbiter().arbitrate(handoff=handoff, stage3_outcome=outcome)
    plan = ReasoningPlanner().build(
        handoff=handoff,
        stage3_outcome=outcome,
        arbitration=arbitration,
    )
    reasoning = ReasoningRenderer().render(plan)
    decision = Task1DecisionOutput(arbitration.final_decision)
    return handoff, outcome, arbitration, plan, decision, reasoning


def test_fallback_is_uncertain_and_uses_only_grounded_weights() -> None:
    handoff, outcome, arbitration, plan, decision, reasoning = build_stage5()
    assert reasoning.confidence is DecisionConfidence.UNCERTAIN
    weights = reasoning.variable_weights
    assert weights.psa is VariableWeight.NOTED
    assert weights.age is VariableWeight.NOTED
    assert weights.pirads is VariableWeight.NOT_USED
    assert weights.bx is VariableWeight.NOT_USED
    Stage5Validator().validate(
        handoff=handoff,
        arbitration=arbitration,
        ledger=outcome.evidence_ledger,
        plan=plan,
        decision=decision,
        reasoning=reasoning,
    )


def test_renderer_separates_management_decision_from_cancer_claim() -> None:
    *_, reasoning = build_stage5()
    assert reasoning.free_text.startswith("A prostate biopsy is recommended now.")
    assert "has prostate cancer" not in reasoning.free_text.casefold()


def test_validator_rejects_decision_mutation_and_ungrounded_weight() -> None:
    handoff, outcome, arbitration, plan, _, reasoning = build_stage5()
    wrong = Task1DecisionOutput(BiopsyDecision.NO)
    with pytest.raises(Stage5ValidationError, match="decision_mutation"):
        Stage5Validator().validate(
            handoff=handoff,
            arbitration=arbitration,
            ledger=outcome.evidence_ledger,
            plan=plan,
            decision=wrong,
            reasoning=reasoning,
        )

    data = reasoning.model_dump()
    weights = reasoning.variable_weights.model_dump()
    weights["pirads"] = VariableWeight.IMPORTANT
    data["variable_weights"] = weights
    ungrounded = type(reasoning).model_validate(data)
    with pytest.raises(Stage5ValidationError, match="variable_weight_mutation"):
        Stage5Validator().validate(
            handoff=handoff,
            arbitration=arbitration,
            ledger=outcome.evidence_ledger,
            plan=plan,
            decision=Task1DecisionOutput(arbitration.final_decision),
            reasoning=ungrounded,
        )


def test_serializer_writes_only_locked_payloads(tmp_path: Path) -> None:
    *_, decision, reasoning = build_stage5()
    paths = Task1OutputSerializer().write(
        output_dir=tmp_path, decision=decision, reasoning=reasoning
    )
    assert {path.name for path in tmp_path.iterdir()} == {
        "prostate-biopsy-decision.json",
        "prostate-biopsy-decision-reasoning.json",
    }
    assert paths.decision_path.read_text().strip() == '"yes"'
    combined = paths.decision_path.read_text() + paths.reasoning_path.read_text()
    for forbidden in ("probability_yes", "threshold", "signed_margin"):
        assert forbidden not in combined


def test_serializer_rejects_non_official_files(tmp_path: Path) -> None:
    *_, decision, reasoning = build_stage5()
    (tmp_path / "debug.json").write_text("{}")
    with pytest.raises(ValueError, match="non-official"):
        Task1OutputSerializer().write(
            output_dir=tmp_path, decision=decision, reasoning=reasoning
        )
    assert {path.name for path in tmp_path.iterdir()} == {"debug.json"}


def test_serializer_restores_both_prior_outputs_after_partial_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    *_, decision, reasoning = build_stage5()
    serializer = Task1OutputSerializer()
    serializer.write(output_dir=tmp_path, decision=decision, reasoning=reasoning)
    original = {path.name: path.read_bytes() for path in tmp_path.iterdir()}

    real_replace = os.replace
    calls = 0

    def fail_second_replace(source: Path, destination: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated second-file replacement failure")
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_second_replace)
    with pytest.raises(OSError, match="simulated"):
        serializer.write(output_dir=tmp_path, decision=decision, reasoning=reasoning)
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == original
    load_official_outputs(tmp_path)


@pytest.mark.parametrize(
    ("text", "safe_code"),
    [
        ("Cancer is confirmed by this assessment.", "free_text_decision_mismatch"),
        (
            "A prostate biopsy is recommended now. The probability_yes is private.",
            "private_diagnostic_disclosure",
        ),
        (
            "A prostate biopsy is recommended now. Pathology confirms cancer.",
            "unsupported_cancer_claim",
        ),
    ],
)
def test_validator_rejects_unsafe_free_text(text: str, safe_code: str) -> None:
    handoff, outcome, arbitration, plan, decision, reasoning = build_stage5()
    unsafe = reasoning.model_copy(update={"free_text": text})
    with pytest.raises(Stage5ValidationError, match=safe_code):
        Stage5Validator().validate(
            handoff=handoff,
            arbitration=arbitration,
            ledger=outcome.evidence_ledger,
            plan=plan,
            decision=decision,
            reasoning=unsafe,
        )


def test_predictor_owned_reasoning_has_no_reveals() -> None:
    handoff = make_handoff(FakeDecisionScenario.PREDICTOR_OWNED_YES)
    from chimera_task1.agent.retrieval_planner import RetrievalPlanner
    from chimera_task1.contracts.adjudication import Stage3OutcomeV1, Stage3Status
    from chimera_task1.contracts.retrieval import EvidenceLedgerV1

    outcome = Stage3OutcomeV1(
        handoff_id=handoff.handoff_id,
        status=Stage3Status.SKIPPED_PREDICTOR_OWNED,
        retrieval_plan=RetrievalPlanner().build(handoff),
        evidence_ledger=EvidenceLedgerV1(handoff_id=handoff.handoff_id, attempts=()),
    )
    arbitration = DecisionArbiter().arbitrate(handoff=handoff, stage3_outcome=outcome)
    plan = ReasoningPlanner().build(
        handoff=handoff, stage3_outcome=outcome, arbitration=arbitration
    )
    assert plan.reveal_sequence == ()
    assert plan.confidence is DecisionConfidence.CLEAR
