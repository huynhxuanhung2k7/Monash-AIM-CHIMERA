"""Versioned, compact Stage 3 structured-assessment prompts."""

from __future__ import annotations

import json
from dataclasses import dataclass

from chimera_task1.contracts.adjudication import EvidenceFactorName, ManagementState
from chimera_task1.contracts.decision_handoff import DecisionHandoffV1
from chimera_task1.evidence.ledger import RetrievedEvidence
from chimera_task1.llm.client import LlmMessage

PROMPT_VERSION = "stage3-adjudication-v1"


@dataclass(frozen=True, slots=True)
class Stage3Prompt:
    messages: tuple[LlmMessage, ...]


class Stage3PromptBuilder:
    prompt_version = PROMPT_VERSION

    def build(
        self,
        *,
        handoff: DecisionHandoffV1,
        evidence: tuple[RetrievedEvidence, ...],
        assessment_id: str,
        model_version: str,
        seed: int,
    ) -> Stage3Prompt:
        features = handoff.features
        safe_case = {
            "handoff_id": handoff.handoff_id,
            "structured_pathway": handoff.structured_pathway.model_dump(mode="json"),
            "input_quality": handoff.input_quality.model_dump(mode="json"),
            "routing_reasons": [item.value for item in handoff.routing_reasons],
            "features": {
                "age": features.age,
                "psa": features.psa,
                "previous_psa": features.previous_psa,
                "supplied_psa_velocity": features.supplied_psa_velocity,
                "pirads": features.pirads,
                "reported_psad": features.reported_psad,
                "prostate_volume": features.prostate_volume,
                "cspca_score": features.cspca_score,
                "dre": features.dre.value,
                "biopsy_history": features.biopsy_history.value,
            },
            "retrieved_evidence": [
                {"section": item.section.value, "content": item.content}
                for item in evidence
            ],
        }
        schema = {
            "schema_version": "1.0",
            "assessment_id": assessment_id,
            "handoff_id": handoff.handoff_id,
            "decision": "yes|no",
            "management_state": [item.value for item in ManagementState],
            "evidence_sufficient": "boolean",
            "supporting_factors": [item.value for item in EvidenceFactorName],
            "opposing_factors": [item.value for item in EvidenceFactorName],
            "consulted_sections": [item.section.value for item in evidence],
            "model_version": model_version,
            "prompt_version": self.prompt_version,
            "seed": seed,
        }
        return Stage3Prompt(
            messages=(
                LlmMessage(
                    role="system",
                    content=(
                        "Return one JSON assessment only. Decide whether biopsy is "
                        "indicated now; do not provide hidden reasoning, calculate "
                        "thresholds, or infer pathology."
                    ),
                ),
                LlmMessage(
                    role="user",
                    content=json.dumps(
                        {"case": safe_case, "required_contract": schema},
                        sort_keys=True,
                    ),
                ),
            )
        )

    def build_repair(
        self,
        *,
        invalid_response: str,
        safe_error_code: str,
        handoff_id: str,
        assessment_id: str,
        model_version: str,
        seed: int,
    ) -> tuple[LlmMessage, ...]:
        return (
            LlmMessage(
                role="system",
                content=(
                    "Repair the prior response to valid JSON only; add no evidence."
                ),
            ),
            LlmMessage(
                role="user",
                content=json.dumps(
                    {
                        "safe_error_code": safe_error_code,
                        "handoff_id": handoff_id,
                        "assessment_id": assessment_id,
                        "model_version": model_version,
                        "prompt_version": self.prompt_version,
                        "seed": seed,
                        "invalid_response": invalid_response[:4000],
                    },
                    sort_keys=True,
                ),
            ),
        )
