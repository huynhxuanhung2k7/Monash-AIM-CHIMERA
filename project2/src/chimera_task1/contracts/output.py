"""Locked evaluator-facing Task 1 output contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import ConfigDict, Field, RootModel, model_validator

from .common import NonEmptyString, StrictFrozenModel, ensure_unique
from .decision_handoff import BiopsyDecision, DecisionConfidence
from .retrieval import Task1RevealSection


class VariableWeight(StrEnum):
    NOT_USED = "not_used"
    NOTED = "noted"
    IMPORTANT = "important"
    DECISIVE = "decisive"


class Task1VariableWeightsV1(StrictFrozenModel):
    age: VariableWeight = VariableWeight.NOT_USED
    fh: VariableWeight = VariableWeight.NOT_USED
    cspca: VariableWeight = VariableWeight.NOT_USED
    pirads: VariableWeight = VariableWeight.NOT_USED
    vol: VariableWeight = VariableWeight.NOT_USED
    psa: VariableWeight = VariableWeight.NOT_USED
    comorbidity: VariableWeight = VariableWeight.NOT_USED
    psad: VariableWeight = VariableWeight.NOT_USED
    dre: VariableWeight = VariableWeight.NOT_USED
    bx: VariableWeight = VariableWeight.NOT_USED


class Task1ReasoningOutputV1(StrictFrozenModel):
    confidence: DecisionConfidence
    variable_weights: Task1VariableWeightsV1
    free_text: Annotated[NonEmptyString, Field(max_length=1800)]
    reveal_sequence: tuple[Task1RevealSection, ...] = ()

    @model_validator(mode="after")
    def validate_reveals(self) -> Task1ReasoningOutputV1:
        ensure_unique(self.reveal_sequence, field_name="reveal_sequence")
        return self


class Task1DecisionOutput(RootModel[BiopsyDecision]):
    model_config = ConfigDict(frozen=True, strict=True)
