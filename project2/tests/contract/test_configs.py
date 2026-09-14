from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from chimera_task1.agent.prompts import PROMPT_VERSION
from chimera_task1.agent.stage3 import DEFAULT_QWEN_MODEL, DEFAULT_QWEN_REVISION
from chimera_task1.arbitration import DEFAULT_ARBITRATION_POLICY_VERSION
from chimera_task1.reasoning import REASONING_POLICY_VERSION
from chimera_task1.runtime.serializer import DECISION_FILENAME, REASONING_FILENAME


def load(name: str) -> dict[str, Any]:
    path = Path(__file__).parents[2] / "configs" / name
    with path.open("rb") as stream:
        return tomllib.load(stream)


def test_frozen_stage_configs_match_code() -> None:
    stage3 = load("stage3.toml")
    assert stage3["llm"]["model"] == DEFAULT_QWEN_MODEL
    assert stage3["llm"]["revision"] == DEFAULT_QWEN_REVISION
    assert stage3["prompt"]["version"] == PROMPT_VERSION
    stage4 = load("stage4.toml")
    assert stage4["arbitration"]["policy_version"] == (
        DEFAULT_ARBITRATION_POLICY_VERSION
    )
    assert stage4["arbitration"]["llm_decision_promoted"] is False
    stage5 = load("stage5.toml")
    assert stage5["reasoning"]["policy_version"] == REASONING_POLICY_VERSION
    assert stage5["output"]["decision_filename"] == DECISION_FILENAME
    assert stage5["output"]["reasoning_filename"] == REASONING_FILENAME
