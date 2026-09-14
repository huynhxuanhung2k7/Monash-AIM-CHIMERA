from __future__ import annotations

import asyncio
import json
from pathlib import Path

from tests.helpers import assessment_json, make_case, make_ledger

from chimera_task1.agent.retrieval_planner import RetrievalPlanner
from chimera_task1.agent.stage3 import Stage3Adjudicator
from chimera_task1.runtime import Task1AgentRunner
from chimera_task1.testing.fake_decision_service import (
    FakeDecisionScenario,
    FakeTask1DecisionService,
)
from chimera_task1.testing.fake_llm import ScriptedLlmClient
from chimera_task1.tools.retrieval.client import InMemoryRetrievalClient


def test_complete_blocks_3_5_runner_writes_valid_outputs(tmp_path: Path) -> None:
    case = make_case("integration")
    service = FakeTask1DecisionService({case.case_id: FakeDecisionScenario.LOW_MARGIN})
    handoff = service.assess(normalized_case=case)
    service.calls.clear()
    plan = RetrievalPlanner().build(handoff)
    ledger = make_ledger(plan)
    runner = Task1AgentRunner(
        decision_service=service,
        adjudicator=Stage3Adjudicator(
            retrieval_client=InMemoryRetrievalClient({}),
            llm_client=ScriptedLlmClient([assessment_json(handoff, ledger)]),
        ),
    )
    result = asyncio.run(runner.run(normalized_case=case, output_dir=tmp_path))
    assert service.calls == [case.case_id]
    assert result.decision.root.value == "yes"
    assert json.loads(result.serialized.decision_path.read_text()) == "yes"
    reasoning = json.loads(result.serialized.reasoning_path.read_text())
    assert set(reasoning) == {
        "confidence",
        "variable_weights",
        "free_text",
        "reveal_sequence",
    }


def test_predictor_owned_end_to_end_makes_zero_llm_calls(tmp_path: Path) -> None:
    case = make_case("predictor-owned")
    service = FakeTask1DecisionService(
        {case.case_id: FakeDecisionScenario.PREDICTOR_OWNED_NO}
    )
    llm = ScriptedLlmClient([])
    runner = Task1AgentRunner(
        decision_service=service,
        adjudicator=Stage3Adjudicator(
            retrieval_client=InMemoryRetrievalClient({}), llm_client=llm
        ),
    )
    result = asyncio.run(runner.run(normalized_case=case, output_dir=tmp_path))
    assert result.decision.root.value == "no"
    assert not llm.calls


def test_retrieval_failure_uses_visible_typed_fallback(tmp_path: Path) -> None:
    case = make_case("known-positive")
    service = FakeTask1DecisionService(
        {case.case_id: FakeDecisionScenario.KNOWN_POSITIVE}
    )
    runner = Task1AgentRunner(
        decision_service=service,
        adjudicator=Stage3Adjudicator(
            retrieval_client=InMemoryRetrievalClient({}),
            llm_client=ScriptedLlmClient([]),
        ),
    )
    result = asyncio.run(runner.run(normalized_case=case, output_dir=tmp_path))
    assert result.arbitration.fallback_reason is not None
    assert result.arbitration.fallback_reason.value == "retrieval_failure"
    assert result.reasoning.confidence.value == "uncertain"
