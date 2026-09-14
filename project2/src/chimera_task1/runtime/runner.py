"""Blocks 3-5 composition root for one normalized Task 1 case."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from chimera_task1.agent.stage3 import Stage3Adjudicator
from chimera_task1.arbitration import DecisionArbiter
from chimera_task1.contracts.adjudication import Stage3OutcomeV1
from chimera_task1.contracts.arbitration import DecisionArbitrationResultV1
from chimera_task1.contracts.decision_handoff import (
    DecisionHandoffV1,
    Task1NormalizedFeatures,
)
from chimera_task1.contracts.output import Task1DecisionOutput, Task1ReasoningOutputV1
from chimera_task1.contracts.reasoning import ReasoningPlanV1
from chimera_task1.decision.service import Task1DecisionService
from chimera_task1.reasoning import ReasoningPlanner, ReasoningRenderer, Stage5Validator
from chimera_task1.runtime.serializer import (
    SerializedTask1Outputs,
    Task1OutputSerializer,
)


@dataclass(frozen=True, slots=True)
class Task1RunResult:
    handoff: DecisionHandoffV1
    stage3: Stage3OutcomeV1
    arbitration: DecisionArbitrationResultV1
    reasoning_plan: ReasoningPlanV1
    decision: Task1DecisionOutput
    reasoning: Task1ReasoningOutputV1
    serialized: SerializedTask1Outputs


class Task1AgentRunner:
    def __init__(
        self,
        *,
        decision_service: Task1DecisionService,
        adjudicator: Stage3Adjudicator,
        arbiter: DecisionArbiter | None = None,
        reasoning_planner: ReasoningPlanner | None = None,
        renderer: ReasoningRenderer | None = None,
        validator: Stage5Validator | None = None,
        serializer: Task1OutputSerializer | None = None,
    ) -> None:
        self._service = decision_service
        self._adjudicator = adjudicator
        self._arbiter = arbiter or DecisionArbiter()
        self._planner = reasoning_planner or ReasoningPlanner()
        self._renderer = renderer or ReasoningRenderer()
        self._validator = validator or Stage5Validator()
        self._serializer = serializer or Task1OutputSerializer()

    async def run(
        self,
        *,
        normalized_case: Task1NormalizedFeatures,
        output_dir: Path,
    ) -> Task1RunResult:
        handoff = self._service.assess(normalized_case=normalized_case)
        stage3 = await self._adjudicator.assess(handoff)
        arbitration = self._arbiter.arbitrate(
            handoff=handoff,
            stage3_outcome=stage3,
        )
        plan = self._planner.build(
            handoff=handoff,
            stage3_outcome=stage3,
            arbitration=arbitration,
        )
        decision = Task1DecisionOutput(arbitration.final_decision)
        reasoning = self._renderer.render(plan)
        self._validator.validate(
            handoff=handoff,
            arbitration=arbitration,
            ledger=stage3.evidence_ledger,
            plan=plan,
            decision=decision,
            reasoning=reasoning,
        )
        serialized = self._serializer.write(
            output_dir=output_dir,
            decision=decision,
            reasoning=reasoning,
        )
        return Task1RunResult(
            handoff=handoff,
            stage3=stage3,
            arbitration=arbitration,
            reasoning_plan=plan,
            decision=decision,
            reasoning=reasoning,
            serialized=serialized,
        )
