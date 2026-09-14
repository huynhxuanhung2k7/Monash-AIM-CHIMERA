"""Strict immutable contracts for Stage 4 decision arbitration."""

from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from .common import (
    SCHEMA_VERSION_V1,
    Identifier,
    Sha256Digest,
    StrictFrozenModel,
    ensure_unique,
)
from .decision_handoff import BiopsyDecision, SchemaVersionV1
from .retrieval import Task1RevealSection


class DecisionOwner(StrEnum):
    PREDICTOR = "predictor"
    LLM = "llm"
    PREDICTOR_FALLBACK = "predictor_fallback"


class DecisionAgreement(StrEnum):
    NOT_ASSESSED = "not_assessed"
    AGREE = "agree"
    DISAGREE = "disagree"


class ArbitrationFallbackReason(StrEnum):
    LLM_NOT_PROMOTED = "llm_not_promoted"
    LLM_INVALID = "llm_invalid"
    LLM_TIMEOUT = "llm_timeout"
    LLM_EVIDENCE_INSUFFICIENT = "llm_evidence_insufficient"
    LLM_CONTRACT_MISMATCH = "llm_contract_mismatch"
    RETRIEVAL_FAILURE = "retrieval_failure"


class ArbitrationUncertaintyReason(StrEnum):
    LOW_PROBABILITY_MARGIN = "low_probability_margin"
    PATHWAY_UNCLEAR = "pathway_unclear"
    KNOWN_POSITIVE_NOT_VALIDATED = "known_positive_not_validated"
    CRITICAL_MISSINGNESS = "critical_missingness"
    STRUCTURED_CONTRADICTION = "structured_contradiction"
    OUT_OF_DISTRIBUTION = "out_of_distribution"
    LLM_NOT_PROMOTED = "llm_not_promoted"
    LLM_INVALID = "llm_invalid"
    LLM_TIMEOUT = "llm_timeout"
    LLM_EVIDENCE_INSUFFICIENT = "llm_evidence_insufficient"
    LLM_CONTRACT_MISMATCH = "llm_contract_mismatch"
    RETRIEVAL_FAILURE = "retrieval_failure"
    LLM_REPORTED_UNCERTAINTY = "llm_reported_uncertainty"
    PREDICTOR_LLM_DISAGREEMENT = "predictor_llm_disagreement"


class DecisionArbitrationPolicyV1(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    policy_version: Identifier
    llm_decision_promoted: bool
    expected_artifact_manifest_digest: Sha256Digest | None = None
    expected_predictor_ownership_policy_version: Identifier | None = None


class DecisionArbitrationResultV1(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    arbitration_id: Sha256Digest
    handoff_id: Sha256Digest
    predictor_assessment_id: Sha256Digest
    llm_assessment_id: Sha256Digest | None = None
    final_decision: BiopsyDecision
    decision_owner: DecisionOwner
    agreement: DecisionAgreement
    fallback_reason: ArbitrationFallbackReason | None = None
    final_uncertainty_reasons: tuple[ArbitrationUncertaintyReason, ...] = ()
    revealed_sections: tuple[Task1RevealSection, ...] = ()
    policy_version: Identifier

    @model_validator(mode="after")
    def validate_state(self) -> DecisionArbitrationResultV1:
        ensure_unique(self.final_uncertainty_reasons, field_name="uncertainty")
        ensure_unique(self.revealed_sections, field_name="revealed_sections")
        fallback = self.decision_owner is DecisionOwner.PREDICTOR_FALLBACK
        if fallback != (self.fallback_reason is not None):
            raise ValueError("fallback reason must match fallback owner")
        if self.decision_owner is DecisionOwner.PREDICTOR and (
            self.llm_assessment_id is not None or self.revealed_sections
        ):
            raise ValueError("predictor owner cannot contain LLM evidence")
        if self.decision_owner is DecisionOwner.LLM and self.llm_assessment_id is None:
            raise ValueError("LLM owner requires assessment")
        assessed = self.llm_assessment_id is not None
        if assessed == (self.agreement is DecisionAgreement.NOT_ASSESSED):
            raise ValueError("agreement status must match assessment availability")
        if fallback and not self.final_uncertainty_reasons:
            raise ValueError("fallback requires uncertainty reason")
        return self


class ArbitrationMetricsV1(StrictFrozenModel):
    total: int
    predictor_owned: int
    llm_owned: int
    predictor_fallback: int
    agreements: int
    disagreements: int
    not_assessed: int
    fallback_counts: tuple[tuple[ArbitrationFallbackReason, int], ...] = ()

    @model_validator(mode="after")
    def validate_counts(self) -> ArbitrationMetricsV1:
        values = (
            self.total,
            self.predictor_owned,
            self.llm_owned,
            self.predictor_fallback,
            self.agreements,
            self.disagreements,
            self.not_assessed,
        )
        if any(value < 0 for value in values):
            raise ValueError("metric count cannot be negative")
        if (
            self.predictor_owned + self.llm_owned + self.predictor_fallback
            != self.total
        ):
            raise ValueError("owner counts must sum to total")
        if self.agreements + self.disagreements + self.not_assessed != self.total:
            raise ValueError("agreement counts must sum to total")
        if sum(count for _, count in self.fallback_counts) != self.predictor_fallback:
            raise ValueError("fallback counts must sum to fallback total")
        ensure_unique(
            tuple(reason for reason, _ in self.fallback_counts), field_name="fallback"
        )
        return self

    @property
    def fallback_rate(self) -> float:
        return self.predictor_fallback / self.total if self.total else 0.0

    @property
    def disagreement_rate(self) -> float:
        assessed = self.agreements + self.disagreements
        return self.disagreements / assessed if assessed else 0.0
