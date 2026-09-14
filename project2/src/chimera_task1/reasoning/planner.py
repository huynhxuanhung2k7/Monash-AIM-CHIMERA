"""Deterministically construct evaluator-facing confidence and grounded factors."""

from __future__ import annotations

from chimera_task1.contracts.adjudication import (
    EvidenceFactorName,
    ManagementState,
    Stage3OutcomeV1,
    Stage3Status,
)
from chimera_task1.contracts.arbitration import (
    DecisionAgreement,
    DecisionArbitrationResultV1,
    DecisionOwner,
)
from chimera_task1.contracts.decision_handoff import (
    DecisionConfidence,
    DecisionHandoffV1,
    PathwayCategory,
)
from chimera_task1.contracts.output import Task1VariableWeightsV1, VariableWeight
from chimera_task1.contracts.reasoning import (
    FactorDirection,
    ReasoningEvidenceSource,
    ReasoningFactorV1,
    ReasoningPlanV1,
    Task1VariableName,
)
from chimera_task1.contracts.retrieval import Task1RevealSection

REASONING_POLICY_VERSION = "reasoning-policy-v1"

_FACTOR_VARIABLE = {
    EvidenceFactorName.AGE: Task1VariableName.AGE,
    EvidenceFactorName.PSA: Task1VariableName.PSA,
    EvidenceFactorName.PSA_TREND: Task1VariableName.PSA,
    EvidenceFactorName.PSAD: Task1VariableName.PSAD,
    EvidenceFactorName.PIRADS: Task1VariableName.PIRADS,
    EvidenceFactorName.PROSTATE_VOLUME: Task1VariableName.VOL,
    EvidenceFactorName.CSPCA: Task1VariableName.CSPCA,
    EvidenceFactorName.DRE: Task1VariableName.DRE,
    EvidenceFactorName.FAMILY_HISTORY: Task1VariableName.FH,
}
_REQUIRED_SECTION = {
    Task1VariableName.FH: Task1RevealSection.FAMILY_HISTORY,
    Task1VariableName.CSPCA: Task1RevealSection.RADIOLOGY_REPORT,
    Task1VariableName.PIRADS: Task1RevealSection.RADIOLOGY_REPORT,
    Task1VariableName.VOL: Task1RevealSection.RADIOLOGY_REPORT,
    Task1VariableName.PSAD: Task1RevealSection.RADIOLOGY_REPORT,
    Task1VariableName.DRE: Task1RevealSection.RADIOLOGY_REPORT,
}


class ReasoningPlanner:
    def build(
        self,
        *,
        handoff: DecisionHandoffV1,
        stage3_outcome: Stage3OutcomeV1,
        arbitration: DecisionArbitrationResultV1,
    ) -> ReasoningPlanV1:
        if handoff.handoff_id != arbitration.handoff_id:
            raise ValueError("arbitration handoff mismatch")
        if stage3_outcome.handoff_id != handoff.handoff_id:
            raise ValueError("Stage 3 handoff mismatch")
        confidence = self._confidence(handoff, stage3_outcome, arbitration)
        factors = self._factors(handoff, stage3_outcome, arbitration)
        weights = {name.value: VariableWeight.NOT_USED for name in Task1VariableName}
        for factor in factors:
            weights[factor.variable.value] = factor.weight
        return ReasoningPlanV1(
            plan_version=REASONING_POLICY_VERSION,
            handoff_id=handoff.handoff_id,
            arbitration_id=arbitration.arbitration_id,
            final_decision=arbitration.final_decision,
            confidence=confidence,
            management_state=self._management_state(handoff, stage3_outcome),
            variable_weights=Task1VariableWeightsV1.model_validate(weights),
            factors=factors,
            uncertainty_messages=self._uncertainty_messages(
                handoff, stage3_outcome, arbitration
            ),
            reveal_sequence=arbitration.revealed_sections,
        )

    @staticmethod
    def _confidence(
        handoff: DecisionHandoffV1,
        outcome: Stage3OutcomeV1,
        arbitration: DecisionArbitrationResultV1,
    ) -> DecisionConfidence:
        if arbitration.decision_owner is DecisionOwner.PREDICTOR_FALLBACK:
            return DecisionConfidence.UNCERTAIN
        if handoff.input_quality.critical_missing or handoff.input_quality.ood_flags:
            return DecisionConfidence.UNCERTAIN
        if handoff.input_quality.contradiction_flags:
            return DecisionConfidence.UNCERTAIN
        if arbitration.agreement is DecisionAgreement.DISAGREE:
            return DecisionConfidence.BORDERLINE
        if (
            outcome.status is Stage3Status.ACCEPTED
            and outcome.assessment is not None
            and outcome.assessment.uncertainty_reasons
        ):
            return DecisionConfidence.BORDERLINE
        return handoff.predictor.confidence

    @staticmethod
    def _management_state(
        handoff: DecisionHandoffV1,
        outcome: Stage3OutcomeV1,
    ) -> ManagementState:
        if outcome.assessment is not None:
            return outcome.assessment.management_state
        return {
            PathwayCategory.BIOPSY_NAIVE: ManagementState.INITIAL_DIAGNOSIS,
            PathwayCategory.PRIOR_NEGATIVE: (
                ManagementState.PERSISTENT_SUSPICION_AFTER_NEGATIVE_BIOPSY
            ),
            PathwayCategory.KNOWN_POSITIVE: ManagementState.UNCLEAR,
            PathwayCategory.UNCLEAR: ManagementState.UNCLEAR,
        }[handoff.structured_pathway.category]

    def _factors(
        self,
        handoff: DecisionHandoffV1,
        outcome: Stage3OutcomeV1,
        arbitration: DecisionArbitrationResultV1,
    ) -> tuple[ReasoningFactorV1, ...]:
        factors: list[ReasoningFactorV1] = []
        assessment = outcome.assessment
        if assessment is not None:
            for direction, source_factors in (
                (FactorDirection.SUPPORTS_DECISION, assessment.supporting_factors),
                (FactorDirection.OPPOSES_DECISION, assessment.opposing_factors),
            ):
                for item in source_factors:
                    variable = _FACTOR_VARIABLE.get(item.factor)
                    if variable is None or any(
                        existing.variable is variable for existing in factors
                    ):
                        continue
                    source = ReasoningEvidenceSource(item.source.value)
                    if not self._grounded(
                        variable, source, arbitration.revealed_sections
                    ):
                        continue
                    factors.append(
                        ReasoningFactorV1(
                            variable=variable,
                            weight=(
                                VariableWeight.DECISIVE
                                if not factors
                                and direction is FactorDirection.SUPPORTS_DECISION
                                and arbitration.decision_owner is DecisionOwner.LLM
                                else VariableWeight.IMPORTANT
                            ),
                            direction=direction,
                            summary=item.summary,
                            source=source,
                        )
                    )
                    if len(factors) == 4:
                        return tuple(factors)
        if not factors:
            if handoff.features.psa is not None:
                factors.append(
                    ReasoningFactorV1(
                        variable=Task1VariableName.PSA,
                        weight=VariableWeight.NOTED,
                        direction=FactorDirection.CONTEXT_ONLY,
                        summary="The current PSA was available as structured context.",
                        source=ReasoningEvidenceSource.STRUCTURED_PROMPT,
                    )
                )
            if handoff.features.age is not None:
                factors.append(
                    ReasoningFactorV1(
                        variable=Task1VariableName.AGE,
                        weight=VariableWeight.NOTED,
                        direction=FactorDirection.CONTEXT_ONLY,
                        summary="Age was available as structured context.",
                        source=ReasoningEvidenceSource.STRUCTURED_PROMPT,
                    )
                )
        return tuple(factors)

    @staticmethod
    def _grounded(
        variable: Task1VariableName,
        source: ReasoningEvidenceSource,
        reveals: tuple[Task1RevealSection, ...],
    ) -> bool:
        if variable in {Task1VariableName.AGE, Task1VariableName.PSA}:
            return source is ReasoningEvidenceSource.STRUCTURED_PROMPT or (
                source.value in {section.value for section in reveals}
            )
        required = _REQUIRED_SECTION.get(variable)
        return (
            required is not None
            and required in reveals
            and source.value == required.value
        )

    @staticmethod
    def _uncertainty_messages(
        handoff: DecisionHandoffV1,
        outcome: Stage3OutcomeV1,
        arbitration: DecisionArbitrationResultV1,
    ) -> tuple[str, ...]:
        messages: list[str] = []
        if arbitration.decision_owner is DecisionOwner.PREDICTOR_FALLBACK:
            messages.append("The routed assessment did not receive decision ownership.")
        if handoff.input_quality.critical_missing:
            messages.append("Important structured evidence is missing.")
        if handoff.input_quality.contradiction_flags:
            messages.append("The available pathway evidence is contradictory.")
        if handoff.input_quality.ood_flags:
            messages.append("At least one input is outside the validated range.")
        if (
            outcome.assessment is not None
            and not outcome.assessment.evidence_sufficient
        ):
            messages.append("Retrieved evidence did not resolve the decision context.")
        return tuple(dict.fromkeys(messages))[:4]
