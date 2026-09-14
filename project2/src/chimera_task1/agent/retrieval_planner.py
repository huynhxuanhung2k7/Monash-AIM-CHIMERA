"""Deterministic minimal patient-evidence retrieval planning."""

from __future__ import annotations

from chimera_task1.contracts.decision_handoff import (
    DecisionHandoffV1,
    PathwayCategory,
    RoutingReason,
    RoutingRecommendation,
)
from chimera_task1.contracts.retrieval import (
    TOOL_BY_SECTION,
    EvidenceNeed,
    RetrievalPlanV1,
    RetrievalRequestV1,
    Task1RevealSection,
)


class RetrievalPolicyError(RuntimeError):
    pass


_FIELD_MAP = {
    "pirads": (Task1RevealSection.RADIOLOGY_REPORT, EvidenceNeed.CLARIFY_MRI_EVIDENCE),
    "psad": (Task1RevealSection.RADIOLOGY_REPORT, EvidenceNeed.CLARIFY_MRI_EVIDENCE),
    "prostate_volume": (
        Task1RevealSection.RADIOLOGY_REPORT,
        EvidenceNeed.CLARIFY_MRI_EVIDENCE,
    ),
    "psa": (Task1RevealSection.PSA_TREND, EvidenceNeed.CLARIFY_PSA_TRAJECTORY),
    "family_history": (
        Task1RevealSection.FAMILY_HISTORY,
        EvidenceNeed.CLARIFY_FAMILY_HISTORY,
    ),
}


class RetrievalPlanner:
    def __init__(
        self, *, policy_version: str = "retrieval-policy-v1", max_tools: int = 3
    ):
        if not 0 <= max_tools <= 3:
            raise ValueError("max_tools must be between zero and three")
        self.policy_version = policy_version
        self.max_tools = max_tools

    def build(self, handoff: DecisionHandoffV1) -> RetrievalPlanV1:
        if RoutingReason.ARTIFACT_POLICY_MISMATCH in handoff.routing_reasons:
            raise RetrievalPolicyError("artifact_policy_mismatch")
        if handoff.routing_recommendation is RoutingRecommendation.PREDICTOR_OWNED:
            return RetrievalPlanV1(
                handoff_id=handoff.handoff_id,
                unresolved_questions=(),
                requests=(),
                max_tools=self.max_tools,
                policy_version=self.policy_version,
            )

        needs: list[EvidenceNeed] = []
        requests: list[RetrievalRequestV1] = []

        def add(section: Task1RevealSection, need: EvidenceNeed, reason: str) -> None:
            if need not in needs:
                needs.append(need)
            if section not in {item.section for item in requests}:
                requests.append(
                    RetrievalRequestV1(
                        section=section,
                        tool_name=TOOL_BY_SECTION[section],
                        evidence_need=need,
                        reason=reason,
                    )
                )

        if handoff.structured_pathway.category in {
            PathwayCategory.KNOWN_POSITIVE,
            PathwayCategory.UNCLEAR,
        }:
            add(
                Task1RevealSection.PREVIOUS_NOTES,
                EvidenceNeed.RESOLVE_MANAGEMENT_CONTEXT,
                "Clarify the current biopsy-management pathway.",
            )
        if RoutingReason.STRUCTURED_CONTRADICTION in handoff.routing_reasons:
            add(
                Task1RevealSection.PREVIOUS_NOTES,
                EvidenceNeed.RESOLVE_PATHWAY_CONTRADICTION,
                "Resolve the structured pathway contradiction.",
            )
        if RoutingReason.LOW_PROBABILITY_MARGIN in handoff.routing_reasons:
            needs.append(EvidenceNeed.REVIEW_BORDERLINE_STRUCTURED_EVIDENCE)
        if RoutingReason.OUT_OF_DISTRIBUTION in handoff.routing_reasons:
            needs.append(EvidenceNeed.REVIEW_OUT_OF_DISTRIBUTION_INPUT)
        flags = (
            *handoff.input_quality.critical_missing,
            *handoff.input_quality.consistency_flags,
            *handoff.input_quality.contradiction_flags,
            *handoff.input_quality.ood_flags,
        )
        for flag in flags:
            for field, (section, need) in _FIELD_MAP.items():
                if field in flag.casefold():
                    add(section, need, f"Resolve input-quality issue: {flag}.")
                    break
        if len(requests) > self.max_tools:
            raise RetrievalPolicyError("retrieval_budget_exceeded")
        return RetrievalPlanV1(
            handoff_id=handoff.handoff_id,
            unresolved_questions=tuple(dict.fromkeys(needs)),
            requests=tuple(requests),
            max_tools=self.max_tools,
            policy_version=self.policy_version,
        )
