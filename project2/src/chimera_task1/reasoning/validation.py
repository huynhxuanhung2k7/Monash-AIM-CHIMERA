"""Stage 5 grounding, semantic, identity, and privacy gates."""

from __future__ import annotations

from dataclasses import dataclass

from chimera_task1.contracts.arbitration import (
    DecisionArbitrationResultV1,
    DecisionOwner,
)
from chimera_task1.contracts.decision_handoff import BiopsyDecision, DecisionHandoffV1
from chimera_task1.contracts.output import (
    Task1DecisionOutput,
    Task1ReasoningOutputV1,
    VariableWeight,
)
from chimera_task1.contracts.reasoning import ReasoningPlanV1, Task1VariableName
from chimera_task1.contracts.retrieval import EvidenceLedgerV1, Task1RevealSection

_REQUIRED = {
    Task1VariableName.FH: Task1RevealSection.FAMILY_HISTORY,
    Task1VariableName.CSPCA: Task1RevealSection.RADIOLOGY_REPORT,
    Task1VariableName.PIRADS: Task1RevealSection.RADIOLOGY_REPORT,
    Task1VariableName.VOL: Task1RevealSection.RADIOLOGY_REPORT,
    Task1VariableName.PSAD: Task1RevealSection.RADIOLOGY_REPORT,
    Task1VariableName.DRE: Task1RevealSection.RADIOLOGY_REPORT,
}
_OVERCLAIMS = ("has prostate cancer", "cancer is confirmed", "pathology confirms")
_PRIVATE_DIAGNOSTIC_MARKERS = (
    "probability_yes",
    "signed_margin",
    "ownership threshold",
    "decision threshold",
    "predictor_assessment_id",
    "llm_assessment_id",
)


@dataclass(frozen=True, slots=True)
class Stage5ValidationError(RuntimeError):
    safe_code: str

    def __str__(self) -> str:
        return self.safe_code


class Stage5Validator:
    def validate(
        self,
        *,
        handoff: DecisionHandoffV1,
        arbitration: DecisionArbitrationResultV1,
        ledger: EvidenceLedgerV1,
        plan: ReasoningPlanV1,
        decision: Task1DecisionOutput,
        reasoning: Task1ReasoningOutputV1,
    ) -> None:
        if (
            len(
                {
                    handoff.handoff_id,
                    arbitration.handoff_id,
                    ledger.handoff_id,
                    plan.handoff_id,
                }
            )
            != 1
        ):
            raise Stage5ValidationError("handoff_identity_mismatch")
        if plan.arbitration_id != arbitration.arbitration_id:
            raise Stage5ValidationError("arbitration_identity_mismatch")
        if (
            decision.root is not arbitration.final_decision
            or plan.final_decision is not decision.root
        ):
            raise Stage5ValidationError("decision_mutation")
        if reasoning.reveal_sequence != ledger.successful_sections:
            raise Stage5ValidationError("reveal_ledger_mismatch")
        if reasoning.reveal_sequence != arbitration.revealed_sections:
            raise Stage5ValidationError("reveal_arbitration_mismatch")
        if reasoning.variable_weights != plan.variable_weights:
            raise Stage5ValidationError("variable_weight_mutation")
        if (
            arbitration.decision_owner is DecisionOwner.PREDICTOR_FALLBACK
            and reasoning.confidence.value != "uncertain"
        ):
            raise Stage5ValidationError("fallback_confidence_not_uncertain")
        weights = reasoning.variable_weights.model_dump()
        for name, weight in weights.items():
            variable = Task1VariableName(name)
            if weight is VariableWeight.NOT_USED:
                continue
            if variable in {Task1VariableName.COMORBIDITY, Task1VariableName.BX}:
                raise Stage5ValidationError("prohibited_active_weight")
            required = _REQUIRED.get(variable)
            if required is not None and required not in reasoning.reveal_sequence:
                raise Stage5ValidationError("ungrounded_active_weight")
        normalized = reasoning.free_text.casefold()
        required_lead = (
            "a prostate biopsy is recommended now."
            if decision.root is BiopsyDecision.YES
            else "a prostate biopsy is not recommended now."
        )
        if not normalized.startswith(required_lead):
            raise Stage5ValidationError("free_text_decision_mismatch")
        if any(marker in normalized for marker in _OVERCLAIMS):
            raise Stage5ValidationError("unsupported_cancer_claim")
        if any(marker in normalized for marker in _PRIVATE_DIAGNOSTIC_MARKERS):
            raise Stage5ValidationError("private_diagnostic_disclosure")
