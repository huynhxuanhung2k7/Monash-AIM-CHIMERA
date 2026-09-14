from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from tests.helpers import assessment_json, make_case, make_ledger

from chimera_task1.agent.retrieval_planner import RetrievalPlanner
from chimera_task1.agent.stage3 import Stage3Adjudicator, Stage3ContractError
from chimera_task1.decision import (
    DecisionArtifactError,
    DecisionInferenceError,
    DecisionInputError,
)
from chimera_task1.evaluation import load_official_outputs
from chimera_task1.runtime import Task1AgentRunner
from chimera_task1.testing.fake_decision_service import (
    FakeDecisionScenario,
    FakeTask1DecisionService,
)
from chimera_task1.testing.fake_llm import ScriptedLlmClient
from chimera_task1.tools.retrieval.client import InMemoryRetrievalClient


@pytest.mark.parametrize(
    "scenario",
    [
        FakeDecisionScenario.LOW_MARGIN,
        FakeDecisionScenario.PATHWAY_UNCLEAR,
        FakeDecisionScenario.KNOWN_POSITIVE,
        FakeDecisionScenario.CRITICAL_MISSINGNESS,
        FakeDecisionScenario.STRUCTURED_CONTRADICTION,
        FakeDecisionScenario.OUT_OF_DISTRIBUTION,
    ],
)
def test_every_routed_scenario_produces_valid_or_typed_output(
    scenario: FakeDecisionScenario,
    tmp_path: Path,
) -> None:
    case = make_case(f"case-{scenario.value}")
    service = FakeTask1DecisionService({case.case_id: scenario})
    handoff = service.assess(normalized_case=case)
    service.calls.clear()
    plan = RetrievalPlanner().build(handoff)
    contents = {
        request.section: f"Evidence for {request.section.value}."
        for request in plan.requests
    }
    ledger = make_ledger(plan, contents)
    runner = Task1AgentRunner(
        decision_service=service,
        adjudicator=Stage3Adjudicator(
            retrieval_client=InMemoryRetrievalClient(contents),
            llm_client=ScriptedLlmClient([assessment_json(handoff, ledger)]),
        ),
    )
    result = asyncio.run(runner.run(normalized_case=case, output_dir=tmp_path))
    restored = load_official_outputs(tmp_path)
    assert restored.decision == result.decision
    assert restored.reasoning == result.reasoning


@pytest.mark.parametrize(
    ("scenario", "error"),
    [
        (FakeDecisionScenario.INPUT_FAILURE, DecisionInputError),
        (FakeDecisionScenario.ARTIFACT_FAILURE, DecisionArtifactError),
        (FakeDecisionScenario.INFERENCE_FAILURE, DecisionInferenceError),
        (FakeDecisionScenario.ARTIFACT_MISMATCH, Stage3ContractError),
    ],
)
def test_hard_failures_write_no_output(
    scenario: FakeDecisionScenario,
    error: type[Exception],
    tmp_path: Path,
) -> None:
    case = make_case(f"case-{scenario.value}")
    runner = Task1AgentRunner(
        decision_service=FakeTask1DecisionService({case.case_id: scenario}),
        adjudicator=Stage3Adjudicator(
            retrieval_client=InMemoryRetrievalClient({}),
            llm_client=ScriptedLlmClient([]),
        ),
    )
    with pytest.raises(error):
        asyncio.run(runner.run(normalized_case=case, output_dir=tmp_path))
    assert list(tmp_path.iterdir()) == []
