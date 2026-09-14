from __future__ import annotations

import pytest
from tests.helpers import accepted_outcome, make_handoff, make_ledger

from chimera_task1.agent.retrieval_planner import RetrievalPlanner
from chimera_task1.arbitration import DecisionArbiter, Stage4ContractError
from chimera_task1.contracts.adjudication import (
    Stage3OutcomeV1,
    Stage3RejectionReason,
    Stage3Status,
)
from chimera_task1.contracts.arbitration import (
    ArbitrationFallbackReason,
    DecisionAgreement,
    DecisionArbitrationPolicyV1,
    DecisionOwner,
)
from chimera_task1.contracts.decision_handoff import BiopsyDecision
from chimera_task1.evaluation import summarize_arbitrations
from chimera_task1.testing.fake_decision_service import FakeDecisionScenario


@pytest.mark.parametrize(
    "scenario",
    [
        FakeDecisionScenario.PREDICTOR_OWNED_YES,
        FakeDecisionScenario.PREDICTOR_OWNED_NO,
    ],
)
def test_predictor_owned_truth_rows(scenario: FakeDecisionScenario) -> None:
    handoff = make_handoff(scenario)
    result = DecisionArbiter().arbitrate(handoff=handoff, stage3_outcome=None)
    assert result.final_decision is handoff.predictor.decision
    assert result.decision_owner is DecisionOwner.PREDICTOR
    assert result.agreement is DecisionAgreement.NOT_ASSESSED


def test_promoted_sufficient_llm_can_own_routed_decision() -> None:
    handoff = make_handoff()
    outcome = accepted_outcome(handoff, decision=BiopsyDecision.NO)
    arbiter = DecisionArbiter(
        DecisionArbitrationPolicyV1(
            policy_version="promoted-test-v1", llm_decision_promoted=True
        )
    )
    result = arbiter.arbitrate(handoff=handoff, stage3_outcome=outcome)
    assert result.final_decision is BiopsyDecision.NO
    assert result.decision_owner is DecisionOwner.LLM
    assert result.agreement is DecisionAgreement.DISAGREE


@pytest.mark.parametrize("promoted", [False, True])
def test_insufficient_evidence_uses_explicit_fallback(promoted: bool) -> None:
    handoff = make_handoff()
    outcome = accepted_outcome(handoff, decision=BiopsyDecision.NO, sufficient=False)
    arbiter = DecisionArbiter(
        DecisionArbitrationPolicyV1(
            policy_version="test-policy-v1", llm_decision_promoted=promoted
        )
    )
    result = arbiter.arbitrate(handoff=handoff, stage3_outcome=outcome)
    assert result.final_decision is handoff.predictor.decision
    assert result.decision_owner is DecisionOwner.PREDICTOR_FALLBACK
    assert result.fallback_reason is (
        ArbitrationFallbackReason.LLM_EVIDENCE_INSUFFICIENT
    )


def test_unpromoted_assessment_falls_back_visibly() -> None:
    handoff = make_handoff()
    result = DecisionArbiter().arbitrate(
        handoff=handoff,
        stage3_outcome=accepted_outcome(handoff),
    )
    assert result.fallback_reason is ArbitrationFallbackReason.LLM_NOT_PROMOTED
    assert result.decision_owner is DecisionOwner.PREDICTOR_FALLBACK


@pytest.mark.parametrize(
    ("rejection", "fallback"),
    [
        (
            Stage3RejectionReason.RETRIEVAL_FAILURE,
            ArbitrationFallbackReason.RETRIEVAL_FAILURE,
        ),
        (
            Stage3RejectionReason.RETRIEVAL_POLICY_ERROR,
            ArbitrationFallbackReason.LLM_CONTRACT_MISMATCH,
        ),
        (Stage3RejectionReason.LLM_TIMEOUT, ArbitrationFallbackReason.LLM_TIMEOUT),
        (
            Stage3RejectionReason.LLM_PROVIDER_ERROR,
            ArbitrationFallbackReason.LLM_INVALID,
        ),
        (Stage3RejectionReason.INVALID_JSON, ArbitrationFallbackReason.LLM_INVALID),
        (Stage3RejectionReason.SCHEMA_INVALID, ArbitrationFallbackReason.LLM_INVALID),
        (
            Stage3RejectionReason.CONTRACT_MISMATCH,
            ArbitrationFallbackReason.LLM_CONTRACT_MISMATCH,
        ),
        (
            Stage3RejectionReason.UNGROUNDED_FACTOR,
            ArbitrationFallbackReason.LLM_CONTRACT_MISMATCH,
        ),
    ],
)
def test_every_stage3_rejection_maps_to_a_closed_fallback(
    rejection: Stage3RejectionReason,
    fallback: ArbitrationFallbackReason,
) -> None:
    handoff = make_handoff()
    plan = RetrievalPlanner().build(handoff)
    outcome = Stage3OutcomeV1(
        handoff_id=handoff.handoff_id,
        status=Stage3Status.REJECTED,
        retrieval_plan=plan,
        evidence_ledger=make_ledger(plan),
        rejection_reason=rejection,
        llm_attempts=1,
    )
    result = DecisionArbiter().arbitrate(handoff=handoff, stage3_outcome=outcome)
    assert result.decision_owner is DecisionOwner.PREDICTOR_FALLBACK
    assert result.fallback_reason is fallback
    assert result.final_decision is handoff.predictor.decision


def test_missing_outcome_is_invalid_fallback() -> None:
    handoff = make_handoff()
    result = DecisionArbiter().arbitrate(handoff=handoff, stage3_outcome=None)
    assert result.fallback_reason is ArbitrationFallbackReason.LLM_INVALID


def test_artifact_and_identity_mismatch_are_hard_failures() -> None:
    mismatch = make_handoff(FakeDecisionScenario.ARTIFACT_MISMATCH)
    with pytest.raises(Stage4ContractError, match="artifact_policy_mismatch"):
        DecisionArbiter().arbitrate(handoff=mismatch, stage3_outcome=None)

    handoff = make_handoff(case_id="a")
    other = make_handoff(case_id="b")
    with pytest.raises(Stage4ContractError, match="stage3_handoff_mismatch"):
        DecisionArbiter().arbitrate(
            handoff=handoff, stage3_outcome=accepted_outcome(other)
        )


def test_policy_identity_constraints_are_hard_failures() -> None:
    handoff = make_handoff()
    wrong_artifact = DecisionArbiter(
        DecisionArbitrationPolicyV1(
            policy_version="identity-test-v1",
            llm_decision_promoted=False,
            expected_artifact_manifest_digest="sha256:" + "0" * 64,
        )
    )
    with pytest.raises(Stage4ContractError, match="artifact_manifest_digest"):
        wrong_artifact.arbitrate(handoff=handoff, stage3_outcome=None)

    wrong_ownership = DecisionArbiter(
        DecisionArbitrationPolicyV1(
            policy_version="identity-test-v1",
            llm_decision_promoted=False,
            expected_predictor_ownership_policy_version="different-policy-v1",
        )
    )
    with pytest.raises(Stage4ContractError, match="ownership_policy_version"):
        wrong_ownership.arbitrate(handoff=handoff, stage3_outcome=None)


def test_arbitration_result_is_deterministic_and_private() -> None:
    handoff = make_handoff()
    outcome = accepted_outcome(handoff)
    first = DecisionArbiter().arbitrate(handoff=handoff, stage3_outcome=outcome)
    second = DecisionArbiter().arbitrate(handoff=handoff, stage3_outcome=outcome)
    assert first == second
    payload = first.model_dump_json()
    for forbidden in (
        "probability_yes",
        "raw_probability_yes",
        '"threshold"',
        "signed_margin",
        "model_name",
    ):
        assert forbidden not in payload


def test_arbitration_metrics_cover_owners_agreement_and_fallback() -> None:
    predictor_handoff = make_handoff(FakeDecisionScenario.PREDICTOR_OWNED_YES)
    predictor = DecisionArbiter().arbitrate(
        handoff=predictor_handoff, stage3_outcome=None
    )

    routed = make_handoff()
    outcome = accepted_outcome(routed)
    llm = DecisionArbiter(
        DecisionArbitrationPolicyV1(
            policy_version="promoted-test-v1", llm_decision_promoted=True
        )
    ).arbitrate(handoff=routed, stage3_outcome=outcome)
    fallback = DecisionArbiter().arbitrate(handoff=routed, stage3_outcome=outcome)

    metrics = summarize_arbitrations((predictor, llm, fallback))
    assert metrics.total == 3
    assert metrics.predictor_owned == 1
    assert metrics.llm_owned == 1
    assert metrics.predictor_fallback == 1
    assert metrics.agreements == 2
    assert metrics.not_assessed == 1
    assert metrics.fallback_rate == pytest.approx(1 / 3)
    assert metrics.disagreement_rate == 0.0
    assert metrics.fallback_counts == ((ArbitrationFallbackReason.LLM_NOT_PROMOTED, 1),)
