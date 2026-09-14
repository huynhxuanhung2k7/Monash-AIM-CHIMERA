"""Allow-list-only atomic serialization of the two official Task 1 outputs."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from chimera_task1.contracts.output import Task1DecisionOutput, Task1ReasoningOutputV1

DECISION_FILENAME = "prostate-biopsy-decision.json"
REASONING_FILENAME = "prostate-biopsy-decision-reasoning.json"
_OFFICIAL_FILENAMES = {DECISION_FILENAME, REASONING_FILENAME}


@dataclass(frozen=True, slots=True)
class SerializedTask1Outputs:
    decision_path: Path
    reasoning_path: Path


class Task1OutputSerializer:
    def write(
        self,
        *,
        output_dir: Path,
        decision: Task1DecisionOutput,
        reasoning: Task1ReasoningOutputV1,
    ) -> SerializedTask1Outputs:
        output_dir.mkdir(parents=True, exist_ok=True)
        unexpected = {
            path.name
            for path in output_dir.iterdir()
            if path.is_file() and path.name not in _OFFICIAL_FILENAMES
        }
        if unexpected:
            raise ValueError("output directory contains non-official files")
        decision_path = output_dir / DECISION_FILENAME
        reasoning_path = output_dir / REASONING_FILENAME
        previous = {
            decision_path: decision_path.read_bytes()
            if decision_path.exists()
            else None,
            reasoning_path: reasoning_path.read_bytes()
            if reasoning_path.exists()
            else None,
        }
        decision_temp = _prepare_temp(
            output_dir, (decision.model_dump_json() + "\n").encode()
        )
        reasoning_temp = _prepare_temp(
            output_dir, (reasoning.model_dump_json(indent=2) + "\n").encode()
        )
        try:
            os.replace(decision_temp, decision_path)
            os.replace(reasoning_temp, reasoning_path)
        except Exception:
            for path, content in previous.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    os.replace(_prepare_temp(output_dir, content), path)
            raise
        finally:
            decision_temp.unlink(missing_ok=True)
            reasoning_temp.unlink(missing_ok=True)
        return SerializedTask1Outputs(decision_path, reasoning_path)


def _prepare_temp(directory: Path, content: bytes) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=".task1-", suffix=".tmp", dir=directory)
    path = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path
