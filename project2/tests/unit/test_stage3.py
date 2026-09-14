from __future__ import annotations

import asyncio

from tests.helpers import assessment_json, make_handoff, make_ledger

from chimera_task1.agent.retrieval_planner import RetrievalPlanner
from chimera_task1.agent.stage3 import Stage3Adjudicator
from chimera_task1.contracts.adjudication import Stage3RejectionReason, Stage3Status
from chimera_task1.contracts.retrieval import EvidenceLedgerV1, Task1RevealSection
from chimera_task1.llm.client import LlmTimeoutError
from chimera_task1.testing.fake_decision_service import FakeDecisionScenario
from chimera_task1.testing.fake_llm import ScriptedLlmClient
from chimera_task1.tools.retrieval.client import InMemoryRetrievalClient


def test_predictor_owned_bypasses_retrieval_and_llm() -> None:
    handoff = make_handoff(FakeDecisionScenario.PREDICTOR_OWNED_YES)
    retrieval = InMemoryRetrievalClient({})
    llm = ScriptedLlmClient([])
    result = asyncio.run(
        Stage3Adjudicator(retrieval_client=retrieval, llm_client=llm).assess(handoff)
    )
    assert result.status is Stage3Status.SKIPPED_PREDICTOR_OWNED
    assert not retrieval.calls and not llm.calls


def test_known_positive_retrieves_previous_notes_and_accepts() -> None:
    handoff = make_handoff(FakeDecisionScenario.KNOWN_POSITIVE)
    plan = RetrievalPlanner().build(handoff)
    note = "Current surveillance plan."
    ledger = make_ledger(plan, {Task1RevealSection.PREVIOUS_NOTES: note})
    response = assessment_json(
        handoff,
        ledger,
        factor="management_context",
        source="previous_notes",
    )
    result = asyncio.run(
        Stage3Adjudicator(
            retrieval_client=InMemoryRetrievalClient(
                {Task1RevealSection.PREVIOUS_NOTES: note}
            ),
            llm_client=ScriptedLlmClient([response]),
        ).assess(handoff)
    )
    assert result.status is Stage3Status.ACCEPTED
    assert result.evidence_ledger.successful_sections == (
        Task1RevealSection.PREVIOUS_NOTES,
    )


def test_invalid_json_gets_one_repair() -> None:
    handoff = make_handoff()
    ledger = EvidenceLedgerV1(handoff_id=handoff.handoff_id, attempts=())
    result = asyncio.run(
        Stage3Adjudicator(
            retrieval_client=InMemoryRetrievalClient({}),
            llm_client=ScriptedLlmClient(["bad", assessment_json(handoff, ledger)]),
        ).assess(handoff)
    )
    assert result.status is Stage3Status.ACCEPTED
    assert result.llm_attempts == 2


def test_timeout_and_required_retrieval_failure_are_typed() -> None:
    low = make_handoff()
    timeout = asyncio.run(
        Stage3Adjudicator(
            retrieval_client=InMemoryRetrievalClient({}),
            llm_client=ScriptedLlmClient([LlmTimeoutError("timeout")]),
        ).assess(low)
    )
    assert timeout.rejection_reason is Stage3RejectionReason.LLM_TIMEOUT

    known = make_handoff(FakeDecisionScenario.KNOWN_POSITIVE)
    failure = asyncio.run(
        Stage3Adjudicator(
            retrieval_client=InMemoryRetrievalClient({}),
            llm_client=ScriptedLlmClient([]),
        ).assess(known)
    )
    assert failure.rejection_reason is Stage3RejectionReason.RETRIEVAL_FAILURE


def test_prompt_excludes_private_predictor_diagnostics_and_pathology() -> None:
    handoff = make_handoff()
    ledger = EvidenceLedgerV1(handoff_id=handoff.handoff_id, attempts=())
    llm = ScriptedLlmClient([assessment_json(handoff, ledger)])
    asyncio.run(
        Stage3Adjudicator(
            retrieval_client=InMemoryRetrievalClient({}), llm_client=llm
        ).assess(handoff)
    )
    prompt = "\n".join(message.content for message in llm.calls[0][0])
    for forbidden in ("raw_probability_yes", '"threshold"', "pathology_report"):
        assert forbidden not in prompt
