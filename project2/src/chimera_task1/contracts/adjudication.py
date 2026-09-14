"""Strict structured assessment and Stage 3 outcome contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, model_validator

from .common import (
    SCHEMA_VERSION_V1,
    Identifier,
    NonEmptyString,
    Sha256Digest,
    StrictFrozenModel,
    ensure_unique,
)
from .decision_handoff import BiopsyDecision, SchemaVersionV1
from .retrieval import EvidenceLedgerV1, RetrievalPlanV1, Task1RevealSection


class ManagementState(StrEnum):
    INITIAL_DIAGNOSIS = "initial_diagnosis"
    PERSISTENT_SUSPICION_AFTER_NEGATIVE_BIOPSY = (
        "persistent_suspicion_after_negative_biopsy"
    )
    CONFIRMATORY_OR_SURVEILLANCE_BIOPSY = "confirmatory_or_surveillance_biopsy"
    ESTABLISHED_DISEASE_WITHOUT_CURRENT_BIOPSY_INDICATION = (
        "established_disease_without_current_biopsy_indication"
    )
    UNCLEAR = "unclear"


class EvidenceFactorName(StrEnum):
    AGE = "age"
    PSA = "psa"
    PSA_TREND = "psa_trend"
    PSAD = "psad"
    PIRADS = "pirads"
    PROSTATE_VOLUME = "prostate_volume"
    CSPCA = "cspca"
    DRE = "dre"
    BIOPSY_HISTORY = "biopsy_history"
    MANAGEMENT_CONTEXT = "management_context"
    FAMILY_HISTORY = "family_history"
    LABORATORY_CONTEXT = "laboratory_context"


class EvidenceSource(StrEnum):
    STRUCTURED_PROMPT = "structured_prompt"
    PREVIOUS_NOTES = "previous_notes"
    RADIOLOGY_REPORT = "radiology_report"
    PSA_TREND = "psa_trend"
    LABORATORY_RESULTS = "laboratory_results"
    FAMILY_HISTORY = "family_history"


class LlmAssessmentWarning(StrEnum):
    EVIDENCE_INSUFFICIENT = "evidence_insufficient"
    RETRIEVAL_EMPTY = "retrieval_empty"
    RETRIEVAL_FAILED = "retrieval_failed"
    CONTRADICTORY_EVIDENCE = "contradictory_evidence"
    SCHEMA_REPAIRED = "schema_repaired"


class EvidenceFactorV1(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    factor: EvidenceFactorName
    summary: Annotated[NonEmptyString, Field(max_length=800)]
    source: EvidenceSource


class LlmDecisionAssessmentV1(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    assessment_id: Sha256Digest
    handoff_id: Sha256Digest
    decision: BiopsyDecision
    management_state: ManagementState
    evidence_sufficient: bool
    supporting_factors: Annotated[tuple[EvidenceFactorV1, ...], Field(max_length=4)]
    opposing_factors: Annotated[tuple[EvidenceFactorV1, ...], Field(max_length=4)]
    unresolved_contradictions: Annotated[
        tuple[NonEmptyString, ...], Field(max_length=4)
    ]
    consulted_sections: tuple[Task1RevealSection, ...]
    uncertainty_reasons: Annotated[tuple[NonEmptyString, ...], Field(max_length=4)]
    model_version: Identifier
    prompt_version: Identifier
    seed: int
    warnings: tuple[LlmAssessmentWarning, ...] = ()

    @model_validator(mode="after")
    def validate_sets(self) -> LlmDecisionAssessmentV1:
        for name in (
            "consulted_sections",
            "unresolved_contradictions",
            "uncertainty_reasons",
            "warnings",
        ):
            ensure_unique(getattr(self, name), field_name=name)
        if not self.evidence_sufficient and not self.uncertainty_reasons:
            raise ValueError("insufficient evidence requires an uncertainty reason")
        return self


class Stage3Status(StrEnum):
    SKIPPED_PREDICTOR_OWNED = "skipped_predictor_owned"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Stage3RejectionReason(StrEnum):
    RETRIEVAL_FAILURE = "retrieval_failure"
    RETRIEVAL_POLICY_ERROR = "retrieval_policy_error"
    LLM_TIMEOUT = "llm_timeout"
    LLM_PROVIDER_ERROR = "llm_provider_error"
    INVALID_JSON = "invalid_json"
    SCHEMA_INVALID = "schema_invalid"
    CONTRACT_MISMATCH = "contract_mismatch"
    UNGROUNDED_FACTOR = "ungrounded_factor"


class Stage3OutcomeV1(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    handoff_id: Sha256Digest
    status: Stage3Status
    retrieval_plan: RetrievalPlanV1
    evidence_ledger: EvidenceLedgerV1
    assessment: LlmDecisionAssessmentV1 | None = None
    rejection_reason: Stage3RejectionReason | None = None
    llm_attempts: Annotated[int, Field(ge=0, le=2)] = 0
    response_digest: Sha256Digest | None = None
    model_version: Identifier | None = None
    prompt_version: Identifier | None = None

    @model_validator(mode="after")
    def validate_state(self) -> Stage3OutcomeV1:
        if self.retrieval_plan.handoff_id != self.handoff_id:
            raise ValueError("retrieval plan handoff mismatch")
        if self.evidence_ledger.handoff_id != self.handoff_id:
            raise ValueError("evidence ledger handoff mismatch")
        if self.status is Stage3Status.ACCEPTED:
            if self.assessment is None or self.rejection_reason is not None:
                raise ValueError("accepted outcome requires assessment only")
            if self.llm_attempts < 1 or self.response_digest is None:
                raise ValueError("accepted outcome requires attempt metadata")
        elif self.status is Stage3Status.REJECTED:
            if self.assessment is not None or self.rejection_reason is None:
                raise ValueError("rejected outcome requires rejection reason only")
        elif (
            any(
                value is not None
                for value in (
                    self.assessment,
                    self.rejection_reason,
                    self.response_digest,
                )
            )
            or self.llm_attempts
        ):
            raise ValueError("skipped outcome cannot contain LLM result metadata")
        return self
