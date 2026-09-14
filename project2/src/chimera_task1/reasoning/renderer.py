"""Render constrained free text without reopening the frozen decision."""

from __future__ import annotations

from chimera_task1.contracts.decision_handoff import BiopsyDecision
from chimera_task1.contracts.output import Task1ReasoningOutputV1
from chimera_task1.contracts.reasoning import ReasoningPlanV1


class ReasoningRenderer:
    def render(self, plan: ReasoningPlanV1) -> Task1ReasoningOutputV1:
        lead = (
            "A prostate biopsy is recommended now."
            if plan.final_decision is BiopsyDecision.YES
            else "A prostate biopsy is not recommended now."
        )
        factor_text = " ".join(factor.summary for factor in plan.factors[:4])
        uncertainty = " ".join(plan.uncertainty_messages)
        management = {
            "initial_diagnosis": "This is an initial diagnostic decision.",
            "persistent_suspicion_after_negative_biopsy": (
                "Prior negative-biopsy context was considered in the current decision."
            ),
            "confirmatory_or_surveillance_biopsy": (
                "The current surveillance or confirmatory-biopsy context was "
                "considered."
            ),
            "established_disease_without_current_biopsy_indication": (
                "Established-disease management context was considered separately "
                "from cancer risk."
            ),
            "unclear": "The current management pathway remains unclear.",
        }[plan.management_state.value]
        text = " ".join(
            part for part in (lead, management, factor_text, uncertainty) if part
        )
        return Task1ReasoningOutputV1(
            confidence=plan.confidence,
            variable_weights=plan.variable_weights,
            free_text=text,
            reveal_sequence=plan.reveal_sequence,
        )
