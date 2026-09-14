"""Deterministic, label-free fake for developing Blocks 3-5."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from hashlib import sha256

from chimera_task1.contracts.decision_handoff import (
    BiopsyDecision,
    BiopsyHistory,
    DecisionConfidence,
    DecisionFeaturesV1,
    DecisionHandoffV1,
    InputQualityAssessmentV1,
    PathwayCategory,
    PathwayConfidence,
    PredictorAssessmentV1,
    PsaDeltaDirection,
    RoutingReason,
    RoutingRecommendation,
    StructuredPathwayAssessmentV1,
    Task1NormalizedFeatures,
)
from chimera_task1.decision.service import (
    DecisionArtifactError,
    DecisionInferenceError,
    DecisionInputError,
)


def digest(value: str) -> str:
    return f"sha256:{sha256(value.encode()).hexdigest()}"


class FakeDecisionScenario(StrEnum):
    PREDICTOR_OWNED_YES = "predictor_owned_yes"
    PREDICTOR_OWNED_NO = "predictor_owned_no"
    LOW_MARGIN = "low_margin"
    PATHWAY_UNCLEAR = "pathway_unclear"
    KNOWN_POSITIVE = "known_positive"
    CRITICAL_MISSINGNESS = "critical_missingness"
    STRUCTURED_CONTRADICTION = "structured_contradiction"
    OUT_OF_DISTRIBUTION = "out_of_distribution"
    ARTIFACT_MISMATCH = "artifact_mismatch"
    INPUT_FAILURE = "input_failure"
    ARTIFACT_FAILURE = "artifact_failure"
    INFERENCE_FAILURE = "inference_failure"


def build_fake_handoff(
    case: Task1NormalizedFeatures,
    scenario: FakeDecisionScenario,
) -> DecisionHandoffV1:
    if scenario is FakeDecisionScenario.INPUT_FAILURE:
        raise DecisionInputError("synthetic_input_failure")
    if scenario is FakeDecisionScenario.ARTIFACT_FAILURE:
        raise DecisionArtifactError("synthetic_artifact_failure")
    if scenario is FakeDecisionScenario.INFERENCE_FAILURE:
        raise DecisionInferenceError("synthetic_inference_failure")

    predictor_owned = scenario in {
        FakeDecisionScenario.PREDICTOR_OWNED_YES,
        FakeDecisionScenario.PREDICTOR_OWNED_NO,
    }
    decision = (
        BiopsyDecision.NO
        if scenario is FakeDecisionScenario.PREDICTOR_OWNED_NO
        else BiopsyDecision.YES
    )
    probability = 0.15 if decision is BiopsyDecision.NO else 0.85
    if scenario is FakeDecisionScenario.LOW_MARGIN:
        probability = 0.51

    pathway = PathwayCategory.BIOPSY_NAIVE
    pathway_confidence = PathwayConfidence.CLEAR
    biopsy_history = case.biopsy_history
    critical: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    ood: tuple[str, ...] = ()
    if predictor_owned:
        reasons = (RoutingReason.HIGH_CONFIDENCE_PREDICTOR,)
    elif scenario is FakeDecisionScenario.LOW_MARGIN:
        reasons = (RoutingReason.LOW_PROBABILITY_MARGIN,)
    elif scenario is FakeDecisionScenario.PATHWAY_UNCLEAR:
        pathway = PathwayCategory.UNCLEAR
        pathway_confidence = PathwayConfidence.UNCERTAIN
        biopsy_history = BiopsyHistory.UNKNOWN
        reasons = (RoutingReason.PATHWAY_UNCLEAR,)
    elif scenario is FakeDecisionScenario.KNOWN_POSITIVE:
        pathway = PathwayCategory.KNOWN_POSITIVE
        biopsy_history = BiopsyHistory.POSITIVE
        reasons = (RoutingReason.KNOWN_POSITIVE_NOT_VALIDATED,)
    elif scenario is FakeDecisionScenario.CRITICAL_MISSINGNESS:
        critical = ("pirads",)
        reasons = (RoutingReason.CRITICAL_MISSINGNESS,)
    elif scenario is FakeDecisionScenario.STRUCTURED_CONTRADICTION:
        contradictions = ("biopsy_pathway_conflict",)
        reasons = (RoutingReason.STRUCTURED_CONTRADICTION,)
    elif scenario is FakeDecisionScenario.OUT_OF_DISTRIBUTION:
        ood = ("psa_out_of_distribution",)
        reasons = (RoutingReason.OUT_OF_DISTRIBUTION,)
    elif scenario is FakeDecisionScenario.ARTIFACT_MISMATCH:
        reasons = (RoutingReason.ARTIFACT_POLICY_MISMATCH,)
    else:
        raise ValueError(f"unsupported scenario: {scenario}")

    feature_data = case.model_dump()
    feature_data["biopsy_history"] = biopsy_history
    features = DecisionFeaturesV1(
        **feature_data,
        recalculated_psad=None,
        psad_absolute_error=None,
        psa_delta=None,
        psa_delta_direction=PsaDeltaDirection.UNKNOWN,
    )
    margin = probability - 0.5
    predictor = PredictorAssessmentV1(
        assessment_id=digest(f"predictor:{case.case_id}:{scenario}"),
        decision=decision,
        raw_probability_yes=probability,
        probability_yes=probability,
        threshold=0.5,
        signed_margin=margin,
        absolute_margin=abs(margin),
        confidence=(
            DecisionConfidence.CLEAR
            if predictor_owned
            else DecisionConfidence.UNCERTAIN
        ),
        ownership_eligible=predictor_owned,
        model_name="synthetic_predictor",
        model_version="fake-v1",
        feature_contract_version="features-v1",
        calibration_method="none",
        calibration_version="none-v1",
        threshold_policy_version="threshold-v1",
        ownership_policy_version="ownership-v1",
        training_data_digest=digest("synthetic-no-training-data"),
    )
    return DecisionHandoffV1(
        handoff_id=digest(f"handoff:{case.case_id}:{scenario}"),
        case_id=case.case_id,
        features=features,
        structured_pathway=StructuredPathwayAssessmentV1(
            category=pathway,
            confidence=pathway_confidence,
            evidence=(f"biopsy_history={biopsy_history}",),
            contradictions=contradictions,
        ),
        input_quality=InputQualityAssessmentV1(
            critical_missing=critical,
            contradiction_flags=contradictions,
            ood_flags=ood,
            input_complete=not critical and not contradictions,
        ),
        predictor=predictor,
        routing_recommendation=(
            RoutingRecommendation.PREDICTOR_OWNED
            if predictor_owned
            else RoutingRecommendation.LLM_REQUIRED
        ),
        routing_reasons=reasons,
        artifact_manifest_digest=digest("synthetic-artifact-manifest"),
    )


class FakeTask1DecisionService:
    def __init__(
        self,
        scenarios: Mapping[str, FakeDecisionScenario],
        *,
        default_scenario: FakeDecisionScenario = FakeDecisionScenario.LOW_MARGIN,
    ) -> None:
        self._scenarios = dict(scenarios)
        self._default = default_scenario
        self.calls: list[str] = []

    def assess(self, *, normalized_case: Task1NormalizedFeatures) -> DecisionHandoffV1:
        self.calls.append(normalized_case.case_id)
        scenario = self._scenarios.get(normalized_case.case_id, self._default)
        return build_fake_handoff(normalized_case, scenario)
