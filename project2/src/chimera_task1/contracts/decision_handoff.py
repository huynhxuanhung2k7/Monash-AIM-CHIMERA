"""Versioned public handoff between Task 1 Blocks 1-2 and Blocks 3-5."""

from __future__ import annotations

from enum import StrEnum
from math import isclose
from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, model_validator

from .common import (
    SCHEMA_VERSION_V1,
    Identifier,
    NonEmptyString,
    Sha256Digest,
    StrictFrozenModel,
    ensure_unique,
)

SchemaVersionV1 = Literal["1.0"]
Probability = Annotated[FiniteFloat, Field(ge=0.0, le=1.0)]
SignedMargin = Annotated[FiniteFloat, Field(ge=-1.0, le=1.0)]
Age = Annotated[FiniteFloat, Field(ge=0.0, le=120.0)]
NonNegativeFloat = Annotated[FiniteFloat, Field(ge=0.0)]
PositiveFloat = Annotated[FiniteFloat, Field(gt=0.0)]
Pirads = Annotated[int, Field(ge=1, le=5)]


class BiopsyDecision(StrEnum):
    YES = "yes"
    NO = "no"


class DecisionConfidence(StrEnum):
    CLEAR = "clear"
    BORDERLINE = "borderline"
    UNCERTAIN = "uncertain"


class DreCategory(StrEnum):
    NORMAL = "normal"
    ABNORMAL = "abnormal"
    UNKNOWN = "unknown"


class BiopsyHistory(StrEnum):
    NONE = "none"
    NEGATIVE = "negative"
    POSITIVE = "positive"
    UNKNOWN = "unknown"


class PsaDeltaDirection(StrEnum):
    RISING = "rising"
    STABLE = "stable"
    FALLING = "falling"
    UNKNOWN = "unknown"


class PathwayCategory(StrEnum):
    BIOPSY_NAIVE = "biopsy_naive"
    PRIOR_NEGATIVE = "prior_negative"
    KNOWN_POSITIVE = "known_positive"
    UNCLEAR = "unclear"


class PathwayConfidence(StrEnum):
    CLEAR = "clear"
    UNCERTAIN = "uncertain"


class RoutingRecommendation(StrEnum):
    PREDICTOR_OWNED = "predictor_owned"
    LLM_REQUIRED = "llm_required"


class RoutingReason(StrEnum):
    HIGH_CONFIDENCE_PREDICTOR = "high_confidence_predictor"
    LOW_PROBABILITY_MARGIN = "low_probability_margin"
    PATHWAY_UNCLEAR = "pathway_unclear"
    KNOWN_POSITIVE_NOT_VALIDATED = "known_positive_not_validated"
    CRITICAL_MISSINGNESS = "critical_missingness"
    STRUCTURED_CONTRADICTION = "structured_contradiction"
    OUT_OF_DISTRIBUTION = "out_of_distribution"
    ARTIFACT_POLICY_MISMATCH = "artifact_policy_mismatch"


class FeatureSource(StrEnum):
    STRUCTURED_PROMPT = "structured_prompt"
    DETERMINISTIC_DERIVATION = "deterministic_derivation"


class ModelSignalDirection(StrEnum):
    SUPPORTS_YES = "supports_yes"
    SUPPORTS_NO = "supports_no"
    NEUTRAL = "neutral"


class FeatureProvenanceV1(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    field_name: Identifier
    source: FeatureSource
    transformation: Identifier
    version: Identifier


class ModelSignalV1(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    name: Identifier
    direction: ModelSignalDirection
    magnitude: Probability


class Task1NormalizedFeatures(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    case_id: Identifier
    age: Age | None = None
    psa: NonNegativeFloat | None = None
    previous_psa: NonNegativeFloat | None = None
    supplied_psa_velocity: FiniteFloat | None = None
    pirads: Pirads | None = None
    reported_psad: NonNegativeFloat | None = None
    prostate_volume: PositiveFloat | None = None
    cspca_score: Probability | None = None
    dre: DreCategory = DreCategory.UNKNOWN
    biopsy_history: BiopsyHistory = BiopsyHistory.UNKNOWN


class DecisionFeaturesV1(Task1NormalizedFeatures):
    recalculated_psad: NonNegativeFloat | None = None
    psad_absolute_error: NonNegativeFloat | None = None
    psa_delta: FiniteFloat | None = None
    psa_delta_direction: PsaDeltaDirection = PsaDeltaDirection.UNKNOWN
    feature_provenance: tuple[FeatureProvenanceV1, ...] = ()

    @model_validator(mode="after")
    def validate_provenance(self) -> DecisionFeaturesV1:
        ensure_unique(
            tuple(entry.field_name for entry in self.feature_provenance),
            field_name="feature_provenance.field_name",
        )
        return self


class StructuredPathwayAssessmentV1(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    category: PathwayCategory
    confidence: PathwayConfidence
    source: Literal["structured_prompt"] = "structured_prompt"
    evidence: tuple[NonEmptyString, ...] = ()
    contradictions: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def validate_ordered_sets(self) -> StructuredPathwayAssessmentV1:
        ensure_unique(self.evidence, field_name="evidence")
        ensure_unique(self.contradictions, field_name="contradictions")
        return self


class InputQualityAssessmentV1(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    critical_missing: tuple[Identifier, ...] = ()
    noncritical_missing: tuple[Identifier, ...] = ()
    invalid_fields: tuple[Identifier, ...] = ()
    consistency_flags: tuple[Identifier, ...] = ()
    contradiction_flags: tuple[Identifier, ...] = ()
    ood_flags: tuple[Identifier, ...] = ()
    input_complete: bool

    @model_validator(mode="after")
    def validate_ordered_sets(self) -> InputQualityAssessmentV1:
        for name in (
            "critical_missing",
            "noncritical_missing",
            "invalid_fields",
            "consistency_flags",
            "contradiction_flags",
            "ood_flags",
        ):
            ensure_unique(getattr(self, name), field_name=name)
        return self


class PredictorAssessmentV1(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    assessment_id: Sha256Digest
    decision: BiopsyDecision
    raw_probability_yes: Probability
    probability_yes: Probability
    threshold: Probability
    signed_margin: SignedMargin
    absolute_margin: Probability
    confidence: DecisionConfidence
    ownership_eligible: bool
    model_name: Identifier
    model_version: Identifier
    feature_contract_version: Identifier
    calibration_method: Identifier
    calibration_version: Identifier
    threshold_policy_version: Identifier
    ownership_policy_version: Identifier
    training_data_digest: Sha256Digest
    model_signals: tuple[ModelSignalV1, ...] = ()
    warnings: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def validate_probability_invariants(self) -> PredictorAssessmentV1:
        expected_margin = self.probability_yes - self.threshold
        if not isclose(self.signed_margin, expected_margin, abs_tol=1e-9):
            raise ValueError("signed_margin must equal probability_yes - threshold")
        if not isclose(self.absolute_margin, abs(self.signed_margin), abs_tol=1e-9):
            raise ValueError("absolute_margin must equal abs(signed_margin)")
        expected = (
            BiopsyDecision.YES
            if self.probability_yes >= self.threshold
            else BiopsyDecision.NO
        )
        if self.decision is not expected:
            raise ValueError("decision does not match probability and threshold")
        ensure_unique(
            tuple(signal.name for signal in self.model_signals),
            field_name="model_signals.name",
        )
        ensure_unique(self.warnings, field_name="warnings")
        return self


class DecisionHandoffV1(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    handoff_id: Sha256Digest
    case_id: Identifier
    features: DecisionFeaturesV1
    structured_pathway: StructuredPathwayAssessmentV1
    input_quality: InputQualityAssessmentV1
    predictor: PredictorAssessmentV1
    routing_recommendation: RoutingRecommendation
    routing_reasons: Annotated[tuple[RoutingReason, ...], Field(min_length=1)]
    artifact_manifest_digest: Sha256Digest

    @model_validator(mode="after")
    def validate_handoff_invariants(self) -> DecisionHandoffV1:
        if self.case_id != self.features.case_id:
            raise ValueError("case_id must match features.case_id")
        ensure_unique(self.routing_reasons, field_name="routing_reasons")
        predictor_owned = (
            self.routing_recommendation is RoutingRecommendation.PREDICTOR_OWNED
        )
        if predictor_owned != self.predictor.ownership_eligible:
            raise ValueError("routing must match predictor ownership eligibility")
        high_confidence = (
            RoutingReason.HIGH_CONFIDENCE_PREDICTOR in self.routing_reasons
        )
        if predictor_owned != high_confidence:
            raise ValueError("high-confidence reason must match predictor ownership")
        return self
