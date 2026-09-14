from __future__ import annotations

import json

from chimera_task1.agent.adjudication import compute_assessment_id, sha256_digest
from chimera_task1.agent.prompts import PROMPT_VERSION
from chimera_task1.agent.retrieval_planner import RetrievalPlanner
from chimera_task1.agent.stage3 import DEFAULT_QWEN_VERSION
from chimera_task1.contracts.adjudication import (
    LlmDecisionAssessmentV1,
    Stage3OutcomeV1,
    Stage3Status,
)
from chimera_task1.contracts.decision_handoff import (
    BiopsyDecision,
    BiopsyHistory,
    DecisionHandoffV1,
    DreCategory,
    Task1NormalizedFeatures,
)
from chimera_task1.contracts.retrieval import (
    EvidenceLedgerV1,
    RetrievalAttemptStatus,
    RetrievalAttemptV1,
    RetrievalPlanV1,
    Task1RevealSection,
)
from chimera_task1.testing.fake_decision_service import (
    FakeDecisionScenario,
    build_fake_handoff,
)


def make_case(case_id: str = "case-001") -> Task1NormalizedFeatures:
    return Task1NormalizedFeatures(
        case_id=case_id,
        age=67.0,
        psa=7.2,
        previous_psa=6.1,
        supplied_psa_velocity=1.1,
        pirads=4,
        reported_psad=0.18,
        prostate_volume=40.0,
        cspca_score=0.64,
        dre=DreCategory.NORMAL,
        biopsy_history=BiopsyHistory.NONE,
    )


def make_handoff(
    scenario: FakeDecisionScenario = FakeDecisionScenario.LOW_MARGIN,
    *,
    case_id: str = "case-001",
) -> DecisionHandoffV1:
    return build_fake_handoff(make_case(case_id), scenario)


def make_ledger(
    plan: RetrievalPlanV1,
    contents: dict[Task1RevealSection, str] | None = None,
) -> EvidenceLedgerV1:
    contents = contents or {
        request.section: f"Synthetic evidence for {request.section.value}."
        for request in plan.requests
    }
    attempts = tuple(
        RetrievalAttemptV1(
            sequence=sequence,
            section=request.section,
            tool_name=request.tool_name,
            evidence_need=request.evidence_need,
            status=RetrievalAttemptStatus.SUCCESS,
            content_digest=sha256_digest(contents[request.section]),
            content_length=len(contents[request.section]),
        )
        for sequence, request in enumerate(plan.requests)
    )
    return EvidenceLedgerV1(handoff_id=plan.handoff_id, attempts=attempts)


def assessment_json(
    handoff: DecisionHandoffV1,
    ledger: EvidenceLedgerV1,
    *,
    decision: BiopsyDecision = BiopsyDecision.YES,
    sufficient: bool = True,
    factor: str = "pirads",
    source: str = "structured_prompt",
) -> str:
    assessment_id = compute_assessment_id(
        handoff=handoff,
        ledger=ledger,
        model_version=DEFAULT_QWEN_VERSION,
        prompt_version=PROMPT_VERSION,
        seed=20260812,
    )
    return json.dumps(
        {
            "schema_version": "1.0",
            "assessment_id": assessment_id,
            "handoff_id": handoff.handoff_id,
            "decision": decision.value,
            "management_state": "initial_diagnosis",
            "evidence_sufficient": sufficient,
            "supporting_factors": [
                {
                    "schema_version": "1.0",
                    "factor": factor,
                    "summary": "The available evidence supports the assessment.",
                    "source": source,
                }
            ],
            "opposing_factors": [],
            "unresolved_contradictions": [],
            "consulted_sections": [item.value for item in ledger.successful_sections],
            "uncertainty_reasons": [] if sufficient else ["Context remains unclear."],
            "model_version": DEFAULT_QWEN_VERSION,
            "prompt_version": PROMPT_VERSION,
            "seed": 20260812,
            "warnings": [],
        },
        sort_keys=True,
    )


def accepted_outcome(
    handoff: DecisionHandoffV1,
    *,
    decision: BiopsyDecision = BiopsyDecision.YES,
    sufficient: bool = True,
) -> Stage3OutcomeV1:
    plan = RetrievalPlanner().build(handoff)
    ledger = make_ledger(plan)
    response = assessment_json(
        handoff, ledger, decision=decision, sufficient=sufficient
    )
    return Stage3OutcomeV1(
        handoff_id=handoff.handoff_id,
        status=Stage3Status.ACCEPTED,
        retrieval_plan=plan,
        evidence_ledger=ledger,
        assessment=LlmDecisionAssessmentV1.model_validate_json(response),
        llm_attempts=1,
        response_digest=sha256_digest(response),
        model_version=DEFAULT_QWEN_VERSION,
        prompt_version=PROMPT_VERSION,
    )
