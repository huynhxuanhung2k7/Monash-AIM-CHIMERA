"""Strict parsing and grounding validation for Stage 3 assessments."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256

from pydantic import ValidationError

from chimera_task1.contracts.adjudication import (
    EvidenceSource,
    LlmDecisionAssessmentV1,
    Stage3RejectionReason,
)
from chimera_task1.contracts.decision_handoff import DecisionHandoffV1
from chimera_task1.contracts.retrieval import EvidenceLedgerV1, Task1RevealSection


def sha256_digest(value: str) -> str:
    return f"sha256:{sha256(value.encode()).hexdigest()}"


def compute_assessment_id(
    *,
    handoff: DecisionHandoffV1,
    ledger: EvidenceLedgerV1,
    model_version: str,
    prompt_version: str,
    seed: int,
) -> str:
    identity = {
        "handoff_id": handoff.handoff_id,
        "model_version": model_version,
        "prompt_version": prompt_version,
        "seed": seed,
        "evidence": [
            {"section": item.section.value, "digest": item.content_digest}
            for item in ledger.attempts
            if item.content_digest is not None
        ],
    }
    return sha256_digest(json.dumps(identity, sort_keys=True, separators=(",", ":")))


@dataclass(frozen=True, slots=True)
class AssessmentParseError(Exception):
    reason: Stage3RejectionReason
    safe_code: str

    def __str__(self) -> str:
        return self.safe_code


def parse_assessment(
    response: str,
    *,
    handoff: DecisionHandoffV1,
    ledger: EvidenceLedgerV1,
    assessment_id: str,
    model_version: str,
    prompt_version: str,
    seed: int,
) -> LlmDecisionAssessmentV1:
    try:
        assessment = LlmDecisionAssessmentV1.model_validate_json(response)
    except ValidationError as exc:
        reason = (
            Stage3RejectionReason.INVALID_JSON
            if exc.error_count() == 1 and exc.errors()[0]["type"] == "json_invalid"
            else Stage3RejectionReason.SCHEMA_INVALID
        )
        raise AssessmentParseError(reason, reason.value) from exc
    expected = (
        (assessment.assessment_id, assessment_id),
        (assessment.handoff_id, handoff.handoff_id),
        (assessment.model_version, model_version),
        (assessment.prompt_version, prompt_version),
        (assessment.seed, seed),
    )
    if any(actual != required for actual, required in expected):
        raise AssessmentParseError(
            Stage3RejectionReason.CONTRACT_MISMATCH,
            "immutable_metadata_mismatch",
        )
    if assessment.consulted_sections != ledger.successful_sections:
        raise AssessmentParseError(
            Stage3RejectionReason.CONTRACT_MISMATCH,
            "consulted_sections_mismatch",
        )
    successful = set(ledger.successful_sections)
    for factor in (*assessment.supporting_factors, *assessment.opposing_factors):
        if factor.source is EvidenceSource.STRUCTURED_PROMPT:
            continue
        try:
            section = Task1RevealSection(factor.source.value)
        except ValueError as exc:  # pragma: no cover
            raise AssessmentParseError(
                Stage3RejectionReason.UNGROUNDED_FACTOR,
                "unsupported_evidence_source",
            ) from exc
        if section not in successful:
            raise AssessmentParseError(
                Stage3RejectionReason.UNGROUNDED_FACTOR,
                "factor_source_not_retrieved",
            )
    return assessment
