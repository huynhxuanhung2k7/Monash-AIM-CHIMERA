"""Read and revalidate an official Task 1 output directory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from chimera_task1.contracts.output import Task1DecisionOutput, Task1ReasoningOutputV1
from chimera_task1.runtime.serializer import DECISION_FILENAME, REASONING_FILENAME


@dataclass(frozen=True, slots=True)
class ValidatedOfficialOutputs:
    decision: Task1DecisionOutput
    reasoning: Task1ReasoningOutputV1


def load_official_outputs(output_dir: Path) -> ValidatedOfficialOutputs:
    expected = {DECISION_FILENAME, REASONING_FILENAME}
    actual = {path.name for path in output_dir.iterdir() if path.is_file()}
    if actual != expected:
        raise ValueError("output directory must contain exactly two official files")
    return ValidatedOfficialOutputs(
        decision=Task1DecisionOutput.model_validate_json(
            (output_dir / DECISION_FILENAME).read_text()
        ),
        reasoning=Task1ReasoningOutputV1.model_validate_json(
            (output_dir / REASONING_FILENAME).read_text()
        ),
    )
