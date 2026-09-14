"""Public service protocol owned by Blocks 1-2."""

from __future__ import annotations

from typing import Protocol

from chimera_task1.contracts.decision_handoff import (
    DecisionHandoffV1,
    Task1NormalizedFeatures,
)


class DecisionInputError(RuntimeError):
    pass


class DecisionArtifactError(RuntimeError):
    pass


class DecisionInferenceError(RuntimeError):
    pass


class Task1DecisionService(Protocol):
    def assess(
        self,
        *,
        normalized_case: Task1NormalizedFeatures,
    ) -> DecisionHandoffV1: ...
