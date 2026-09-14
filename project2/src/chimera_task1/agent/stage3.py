"""Stage 3 selective retrieval and structured LLM adjudication."""

from __future__ import annotations

import json
from dataclasses import dataclass

from chimera_task1.agent.adjudication import (
    AssessmentParseError,
    compute_assessment_id,
    parse_assessment,
    sha256_digest,
)
from chimera_task1.agent.prompts import Stage3PromptBuilder
from chimera_task1.agent.retrieval_planner import RetrievalPlanner, RetrievalPolicyError
from chimera_task1.contracts.adjudication import (
    LlmAssessmentWarning,
    LlmDecisionAssessmentV1,
    Stage3OutcomeV1,
    Stage3RejectionReason,
    Stage3Status,
)
from chimera_task1.contracts.decision_handoff import (
    BiopsyDecision,
    DecisionHandoffV1,
    RoutingRecommendation,
    Task1NormalizedFeatures,
)
from chimera_task1.contracts.retrieval import EvidenceLedgerV1, RetrievalPlanV1
from chimera_task1.decision.service import Task1DecisionService
from chimera_task1.evidence.ledger import execute_retrieval_plan
from chimera_task1.llm.client import (
    LlmClient,
    LlmGenerationConfig,
    LlmProviderError,
    LlmTimeoutError,
)
from chimera_task1.tools.retrieval.client import RetrievalClient

DEFAULT_QWEN_MODEL = "Qwen/Qwen3-4B-Instruct-2507"
DEFAULT_QWEN_REVISION = "cdbee75f17c01a7cc42f958dc650907174af0554"
DEFAULT_QWEN_VERSION = f"Qwen3-4B-Instruct-2507:{DEFAULT_QWEN_REVISION}"


class Stage3ContractError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Stage3RuntimeLimits:
    retrieval_timeout_seconds: float = 8.0
    max_evidence_chars: int = 6000

    def __post_init__(self) -> None:
        if self.retrieval_timeout_seconds <= 0 or self.max_evidence_chars < 100:
            raise ValueError("invalid Stage 3 runtime limits")


class Stage3Adjudicator:
    def __init__(
        self,
        *,
        retrieval_client: RetrievalClient,
        llm_client: LlmClient,
        generation_config: LlmGenerationConfig | None = None,
        planner: RetrievalPlanner | None = None,
        prompt_builder: Stage3PromptBuilder | None = None,
        limits: Stage3RuntimeLimits | None = None,
    ) -> None:
        self._retrieval = retrieval_client
        self._llm = llm_client
        self._generation = generation_config or LlmGenerationConfig(
            model=DEFAULT_QWEN_MODEL,
            model_version=DEFAULT_QWEN_VERSION,
        )
        self._planner = planner or RetrievalPlanner()
        self._prompts = prompt_builder or Stage3PromptBuilder()
        self._limits = limits or Stage3RuntimeLimits()

    async def assess(self, handoff: DecisionHandoffV1) -> Stage3OutcomeV1:
        try:
            plan = self._planner.build(handoff)
        except RetrievalPolicyError as exc:
            raise Stage3ContractError(str(exc)) from exc
        empty_ledger = EvidenceLedgerV1(handoff_id=handoff.handoff_id, attempts=())
        if handoff.routing_recommendation is RoutingRecommendation.PREDICTOR_OWNED:
            return Stage3OutcomeV1(
                handoff_id=handoff.handoff_id,
                status=Stage3Status.SKIPPED_PREDICTOR_OWNED,
                retrieval_plan=plan,
                evidence_ledger=empty_ledger,
            )
        execution = await execute_retrieval_plan(
            plan,
            self._retrieval,
            timeout_seconds=self._limits.retrieval_timeout_seconds,
            max_content_chars=self._limits.max_evidence_chars,
        )
        if execution.required_failure:
            return self._rejected(
                handoff,
                plan,
                execution.ledger,
                Stage3RejectionReason.RETRIEVAL_FAILURE,
                0,
            )
        assessment_id = compute_assessment_id(
            handoff=handoff,
            ledger=execution.ledger,
            model_version=self._generation.model_version,
            prompt_version=self._prompts.prompt_version,
            seed=self._generation.seed,
        )
        prompt = self._prompts.build(
            handoff=handoff,
            evidence=execution.evidence,
            assessment_id=assessment_id,
            model_version=self._generation.model_version,
            seed=self._generation.seed,
        )
        messages = prompt.messages
        response: str | None = None
        first_decision: BiopsyDecision | None = None
        parse_error: AssessmentParseError | None = None
        for attempt in (1, 2):
            try:
                response = await self._llm.complete(messages, self._generation)
            except LlmTimeoutError:
                return self._rejected(
                    handoff,
                    plan,
                    execution.ledger,
                    Stage3RejectionReason.LLM_TIMEOUT,
                    attempt,
                    response,
                )
            except Exception as exc:  # noqa: BLE001
                reason = Stage3RejectionReason.LLM_PROVIDER_ERROR
                if isinstance(exc, LlmProviderError):
                    reason = Stage3RejectionReason.LLM_PROVIDER_ERROR
                return self._rejected(
                    handoff, plan, execution.ledger, reason, attempt, response
                )
            try:
                assessment = parse_assessment(
                    response,
                    handoff=handoff,
                    ledger=execution.ledger,
                    assessment_id=assessment_id,
                    model_version=self._generation.model_version,
                    prompt_version=self._prompts.prompt_version,
                    seed=self._generation.seed,
                )
            except AssessmentParseError as exc:
                parse_error = exc
                if attempt == 1:
                    first_decision = _extract_decision(response)
                    messages = self._prompts.build_repair(
                        invalid_response=response,
                        safe_error_code=exc.safe_code,
                        handoff_id=handoff.handoff_id,
                        assessment_id=assessment_id,
                        model_version=self._generation.model_version,
                        seed=self._generation.seed,
                    )
                    continue
                break
            if first_decision is not None and assessment.decision is not first_decision:
                return self._rejected(
                    handoff,
                    plan,
                    execution.ledger,
                    Stage3RejectionReason.CONTRACT_MISMATCH,
                    attempt,
                    response,
                )
            if (
                attempt == 2
                and LlmAssessmentWarning.SCHEMA_REPAIRED not in assessment.warnings
            ):
                data = assessment.model_dump()
                data["warnings"] = (
                    *assessment.warnings,
                    LlmAssessmentWarning.SCHEMA_REPAIRED,
                )
                assessment = LlmDecisionAssessmentV1.model_validate(data)
            return Stage3OutcomeV1(
                handoff_id=handoff.handoff_id,
                status=Stage3Status.ACCEPTED,
                retrieval_plan=plan,
                evidence_ledger=execution.ledger,
                assessment=assessment,
                llm_attempts=attempt,
                response_digest=sha256_digest(response),
                model_version=self._generation.model_version,
                prompt_version=self._prompts.prompt_version,
            )
        assert parse_error is not None
        return self._rejected(
            handoff,
            plan,
            execution.ledger,
            parse_error.reason,
            2,
            response,
        )

    def _rejected(
        self,
        handoff: DecisionHandoffV1,
        plan: RetrievalPlanV1,
        ledger: EvidenceLedgerV1,
        reason: Stage3RejectionReason,
        attempts: int,
        response: str | None = None,
    ) -> Stage3OutcomeV1:
        return Stage3OutcomeV1(
            handoff_id=handoff.handoff_id,
            status=Stage3Status.REJECTED,
            retrieval_plan=plan,
            evidence_ledger=ledger,
            rejection_reason=reason,
            llm_attempts=attempts,
            response_digest=sha256_digest(response) if response is not None else None,
            model_version=self._generation.model_version,
            prompt_version=self._prompts.prompt_version,
        )


def _extract_decision(response: str) -> BiopsyDecision | None:
    try:
        value = json.loads(response).get("decision")
        return BiopsyDecision(value)
    except (AttributeError, json.JSONDecodeError, TypeError, ValueError):
        return None


async def run_stage3_for_case(
    *,
    normalized_case: Task1NormalizedFeatures,
    decision_service: Task1DecisionService,
    adjudicator: Stage3Adjudicator,
) -> Stage3OutcomeV1:
    return await adjudicator.assess(
        decision_service.assess(normalized_case=normalized_case)
    )
