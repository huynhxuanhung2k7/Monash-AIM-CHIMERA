"""Pure deterministic Stage 4 arbitration under a versioned truth table."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256

from chimera_task1.contracts.adjudication import (
    Stage3OutcomeV1,
    Stage3RejectionReason,
    Stage3Status,
)
from chimera_task1.contracts.arbitration import (
    ArbitrationFallbackReason,
    ArbitrationUncertaintyReason,
    DecisionAgreement,
    DecisionArbitrationPolicyV1,
    DecisionArbitrationResultV1,
    DecisionOwner,
)
from chimera_task1.contracts.decision_handoff import (
    BiopsyDecision,
    DecisionHandoffV1,
    RoutingReason,
    RoutingRecommendation,
)
from chimera_task1.contracts.retrieval import Task1RevealSection

DEFAULT_ARBITRATION_POLICY_VERSION = "arbitration-policy-v1"
DEFAULT_ARBITRATION_POLICY = DecisionArbitrationPolicyV1(
    policy_version=DEFAULT_ARBITRATION_POLICY_VERSION,
    llm_decision_promoted=False,
)


@dataclass(frozen=True, slots=True)
class Stage4ContractError(RuntimeError):
    safe_code: str

    def __str__(self) -> str:
        return self.safe_code


_ROUTING_UNCERTAINTY = {
    RoutingReason.LOW_PROBABILITY_MARGIN: (
        ArbitrationUncertaintyReason.LOW_PROBABILITY_MARGIN
    ),
    RoutingReason.PATHWAY_UNCLEAR: ArbitrationUncertaintyReason.PATHWAY_UNCLEAR,
    RoutingReason.KNOWN_POSITIVE_NOT_VALIDATED: (
        ArbitrationUncertaintyReason.KNOWN_POSITIVE_NOT_VALIDATED
    ),
    RoutingReason.CRITICAL_MISSINGNESS: (
        ArbitrationUncertaintyReason.CRITICAL_MISSINGNESS
    ),
    RoutingReason.STRUCTURED_CONTRADICTION: (
        ArbitrationUncertaintyReason.STRUCTURED_CONTRADICTION
    ),
    RoutingReason.OUT_OF_DISTRIBUTION: ArbitrationUncertaintyReason.OUT_OF_DISTRIBUTION,
}
_REJECTION_FALLBACK = {
    Stage3RejectionReason.RETRIEVAL_FAILURE: (
        ArbitrationFallbackReason.RETRIEVAL_FAILURE
    ),
    Stage3RejectionReason.RETRIEVAL_POLICY_ERROR: (
        ArbitrationFallbackReason.LLM_CONTRACT_MISMATCH
    ),
    Stage3RejectionReason.LLM_TIMEOUT: ArbitrationFallbackReason.LLM_TIMEOUT,
    Stage3RejectionReason.LLM_PROVIDER_ERROR: ArbitrationFallbackReason.LLM_INVALID,
    Stage3RejectionReason.INVALID_JSON: ArbitrationFallbackReason.LLM_INVALID,
    Stage3RejectionReason.SCHEMA_INVALID: ArbitrationFallbackReason.LLM_INVALID,
    Stage3RejectionReason.CONTRACT_MISMATCH: (
        ArbitrationFallbackReason.LLM_CONTRACT_MISMATCH
    ),
    Stage3RejectionReason.UNGROUNDED_FACTOR: (
        ArbitrationFallbackReason.LLM_CONTRACT_MISMATCH
    ),
}
_FALLBACK_UNCERTAINTY = {
    reason: ArbitrationUncertaintyReason(reason.value)
    for reason in ArbitrationFallbackReason
}


class DecisionArbiter:
    def __init__(
        self, policy: DecisionArbitrationPolicyV1 = DEFAULT_ARBITRATION_POLICY
    ):
        self.policy = policy

    def arbitrate(
        self,
        *,
        handoff: DecisionHandoffV1,
        stage3_outcome: Stage3OutcomeV1 | None,
    ) -> DecisionArbitrationResultV1:
        self._validate(handoff, stage3_outcome)
        if handoff.routing_recommendation is RoutingRecommendation.PREDICTOR_OWNED:
            if stage3_outcome is not None:
                if stage3_outcome.status is not Stage3Status.SKIPPED_PREDICTOR_OWNED:
                    raise Stage4ContractError("predictor_owned_cannot_accept_llm")
                if stage3_outcome.evidence_ledger.attempts:
                    raise Stage4ContractError("predictor_owned_cannot_reveal")
            return self._result(
                handoff,
                None,
                handoff.predictor.decision,
                DecisionOwner.PREDICTOR,
                DecisionAgreement.NOT_ASSESSED,
                None,
                (),
                (),
            )

        uncertainty = tuple(
            _ROUTING_UNCERTAINTY[reason]
            for reason in handoff.routing_reasons
            if reason in _ROUTING_UNCERTAINTY
        )
        if stage3_outcome is None:
            return self._fallback(
                handoff, None, ArbitrationFallbackReason.LLM_INVALID, uncertainty
            )
        if stage3_outcome.status is Stage3Status.SKIPPED_PREDICTOR_OWNED:
            raise Stage4ContractError("llm_required_cannot_skip")
        if stage3_outcome.status is Stage3Status.REJECTED:
            assert stage3_outcome.rejection_reason is not None
            return self._fallback(
                handoff,
                stage3_outcome,
                _REJECTION_FALLBACK[stage3_outcome.rejection_reason],
                uncertainty,
            )
        assessment = stage3_outcome.assessment
        assert assessment is not None
        agreement = (
            DecisionAgreement.AGREE
            if assessment.decision is handoff.predictor.decision
            else DecisionAgreement.DISAGREE
        )
        extras: list[ArbitrationUncertaintyReason] = list(uncertainty)
        if assessment.uncertainty_reasons or assessment.unresolved_contradictions:
            extras.append(ArbitrationUncertaintyReason.LLM_REPORTED_UNCERTAINTY)
        if agreement is DecisionAgreement.DISAGREE:
            extras.append(ArbitrationUncertaintyReason.PREDICTOR_LLM_DISAGREEMENT)
        if not assessment.evidence_sufficient:
            return self._fallback(
                handoff,
                stage3_outcome,
                ArbitrationFallbackReason.LLM_EVIDENCE_INSUFFICIENT,
                tuple(extras),
            )
        if not self.policy.llm_decision_promoted:
            return self._fallback(
                handoff,
                stage3_outcome,
                ArbitrationFallbackReason.LLM_NOT_PROMOTED,
                tuple(extras),
            )
        return self._result(
            handoff,
            assessment.assessment_id,
            assessment.decision,
            DecisionOwner.LLM,
            agreement,
            None,
            _unique(tuple(extras)),
            stage3_outcome.evidence_ledger.successful_sections,
        )

    def _validate(
        self,
        handoff: DecisionHandoffV1,
        outcome: Stage3OutcomeV1 | None,
    ) -> None:
        if RoutingReason.ARTIFACT_POLICY_MISMATCH in handoff.routing_reasons:
            raise Stage4ContractError("artifact_policy_mismatch")
        if self.policy.expected_artifact_manifest_digest not in {
            None,
            handoff.artifact_manifest_digest,
        }:
            raise Stage4ContractError("artifact_manifest_digest_mismatch")
        if self.policy.expected_predictor_ownership_policy_version not in {
            None,
            handoff.predictor.ownership_policy_version,
        }:
            raise Stage4ContractError("ownership_policy_version_mismatch")
        if outcome is None:
            return
        if outcome.handoff_id != handoff.handoff_id:
            raise Stage4ContractError("stage3_handoff_mismatch")
        if outcome.status is Stage3Status.ACCEPTED:
            assessment = outcome.assessment
            assert assessment is not None
            if outcome.model_version != assessment.model_version:
                raise Stage4ContractError("llm_model_version_mismatch")
            if outcome.prompt_version != assessment.prompt_version:
                raise Stage4ContractError("llm_prompt_version_mismatch")
            if (
                assessment.consulted_sections
                != outcome.evidence_ledger.successful_sections
            ):
                raise Stage4ContractError("llm_revealed_sections_mismatch")

    def _fallback(
        self,
        handoff: DecisionHandoffV1,
        outcome: Stage3OutcomeV1 | None,
        reason: ArbitrationFallbackReason,
        uncertainty: tuple[ArbitrationUncertaintyReason, ...],
    ) -> DecisionArbitrationResultV1:
        assessment = outcome.assessment if outcome is not None else None
        agreement = DecisionAgreement.NOT_ASSESSED
        if assessment is not None:
            agreement = (
                DecisionAgreement.AGREE
                if assessment.decision is handoff.predictor.decision
                else DecisionAgreement.DISAGREE
            )
        return self._result(
            handoff,
            assessment.assessment_id if assessment else None,
            handoff.predictor.decision,
            DecisionOwner.PREDICTOR_FALLBACK,
            agreement,
            reason,
            _unique((*uncertainty, _FALLBACK_UNCERTAINTY[reason])),
            outcome.evidence_ledger.successful_sections if outcome else (),
        )

    def _result(
        self,
        handoff: DecisionHandoffV1,
        llm_id: str | None,
        decision: BiopsyDecision,
        owner: DecisionOwner,
        agreement: DecisionAgreement,
        fallback: ArbitrationFallbackReason | None,
        uncertainty: tuple[ArbitrationUncertaintyReason, ...],
        sections: tuple[Task1RevealSection, ...],
    ) -> DecisionArbitrationResultV1:
        identity = json.dumps(
            {
                "handoff": handoff.handoff_id,
                "predictor": handoff.predictor.assessment_id,
                "llm": llm_id,
                "decision": str(decision),
                "owner": owner.value,
                "agreement": agreement.value,
                "fallback": fallback.value if fallback else None,
                "uncertainty": [item.value for item in uncertainty],
                "sections": [str(item) for item in sections],
                "policy": self.policy.policy_version,
                "promoted": self.policy.llm_decision_promoted,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return DecisionArbitrationResultV1(
            arbitration_id=f"sha256:{sha256(identity.encode()).hexdigest()}",
            handoff_id=handoff.handoff_id,
            predictor_assessment_id=handoff.predictor.assessment_id,
            llm_assessment_id=llm_id,
            final_decision=decision,
            decision_owner=owner,
            agreement=agreement,
            fallback_reason=fallback,
            final_uncertainty_reasons=uncertainty,
            revealed_sections=sections,
            policy_version=self.policy.policy_version,
        )


def _unique(
    values: tuple[ArbitrationUncertaintyReason, ...],
) -> tuple[ArbitrationUncertaintyReason, ...]:
    return tuple(dict.fromkeys(values))
