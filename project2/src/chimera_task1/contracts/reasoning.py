"""Internal immutable Stage 5 reasoning-plan contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, model_validator

from .adjudication import ManagementState
from .common import (
    Identifier,
    NonEmptyString,
    Sha256Digest,
    StrictFrozenModel,
    ensure_unique,
)
from .decision_handoff import BiopsyDecision, DecisionConfidence
from .output import Task1VariableWeightsV1, VariableWeight
from .retrieval import Task1RevealSection


class Task1VariableName(StrEnum):
    AGE = "age"
    FH = "fh"
    CSPCA = "cspca"
    PIRADS = "pirads"
    VOL = "vol"
    PSA = "psa"
    COMORBIDITY = "comorbidity"
    PSAD = "psad"
    DRE = "dre"
    BX = "bx"


class FactorDirection(StrEnum):
    SUPPORTS_DECISION = "supports_decision"
    OPPOSES_DECISION = "opposes_decision"
    CONTEXT_ONLY = "context_only"


class ReasoningEvidenceSource(StrEnum):
    STRUCTURED_PROMPT = "structured_prompt"
    PREVIOUS_NOTES = "previous_notes"
    RADIOLOGY_REPORT = "radiology_report"
    PSA_TREND = "psa_trend"
    LABORATORY_RESULTS = "laboratory_results"
    FAMILY_HISTORY = "family_history"


class ReasoningFactorV1(StrictFrozenModel):
    variable: Task1VariableName
    weight: VariableWeight
    direction: FactorDirection
    summary: Annotated[NonEmptyString, Field(max_length=800)]
    source: ReasoningEvidenceSource


class ReasoningPlanV1(StrictFrozenModel):
    plan_version: Identifier
    handoff_id: Sha256Digest
    arbitration_id: Sha256Digest
    final_decision: BiopsyDecision
    confidence: DecisionConfidence
    management_state: ManagementState
    variable_weights: Task1VariableWeightsV1
    factors: Annotated[tuple[ReasoningFactorV1, ...], Field(max_length=4)]
    uncertainty_messages: Annotated[tuple[NonEmptyString, ...], Field(max_length=4)]
    reveal_sequence: tuple[Task1RevealSection, ...]

    @model_validator(mode="after")
    def validate_plan(self) -> ReasoningPlanV1:
        ensure_unique(
            tuple(item.variable for item in self.factors), field_name="factors"
        )
        ensure_unique(self.uncertainty_messages, field_name="uncertainty_messages")
        ensure_unique(self.reveal_sequence, field_name="reveal_sequence")
        active = {
            Task1VariableName(name)
            for name, value in self.variable_weights.model_dump().items()
            if value is not VariableWeight.NOT_USED
        }
        if active != {factor.variable for factor in self.factors}:
            raise ValueError("factor variables must exactly match active weights")
        return self
