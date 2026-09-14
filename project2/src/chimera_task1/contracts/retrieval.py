"""Strict Stage 3 retrieval-planning and evidence-ledger contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, model_validator

from .common import (
    SCHEMA_VERSION_V1,
    Identifier,
    NonEmptyString,
    Sha256Digest,
    StrictFrozenModel,
    ensure_unique,
)
from .decision_handoff import SchemaVersionV1


class Task1RevealSection(StrEnum):
    PREVIOUS_NOTES = "previous_notes"
    RADIOLOGY_REPORT = "radiology_report"
    PSA_TREND = "psa_trend"
    LABORATORY_RESULTS = "laboratory_results"
    FAMILY_HISTORY = "family_history"


class RetrievalToolName(StrEnum):
    GET_PREVIOUS_NOTES = "get_previous_notes"
    GET_MRI_REPORT = "get_mri_report"
    GET_PSA_TREND = "get_psa_trend"
    GET_LAB_RESULTS = "get_lab_results"
    GET_FAMILY_HISTORY = "get_family_history"


TOOL_BY_SECTION = {
    Task1RevealSection.PREVIOUS_NOTES: RetrievalToolName.GET_PREVIOUS_NOTES,
    Task1RevealSection.RADIOLOGY_REPORT: RetrievalToolName.GET_MRI_REPORT,
    Task1RevealSection.PSA_TREND: RetrievalToolName.GET_PSA_TREND,
    Task1RevealSection.LABORATORY_RESULTS: RetrievalToolName.GET_LAB_RESULTS,
    Task1RevealSection.FAMILY_HISTORY: RetrievalToolName.GET_FAMILY_HISTORY,
}


class EvidenceNeed(StrEnum):
    RESOLVE_MANAGEMENT_CONTEXT = "resolve_management_context"
    RESOLVE_PATHWAY_CONTRADICTION = "resolve_pathway_contradiction"
    CLARIFY_MRI_EVIDENCE = "clarify_mri_evidence"
    CLARIFY_PSA_TRAJECTORY = "clarify_psa_trajectory"
    CLARIFY_LABORATORY_CONTEXT = "clarify_laboratory_context"
    CLARIFY_FAMILY_HISTORY = "clarify_family_history"
    REVIEW_BORDERLINE_STRUCTURED_EVIDENCE = "review_borderline_structured_evidence"
    REVIEW_OUT_OF_DISTRIBUTION_INPUT = "review_out_of_distribution_input"


class RetrievalAttemptStatus(StrEnum):
    SUCCESS = "success"
    EMPTY = "empty"
    FAILED = "failed"
    REJECTED = "rejected"


class RetrievalRequestV1(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    section: Task1RevealSection
    tool_name: RetrievalToolName
    evidence_need: EvidenceNeed
    reason: NonEmptyString
    required: bool = True

    @model_validator(mode="after")
    def validate_tool_mapping(self) -> RetrievalRequestV1:
        if TOOL_BY_SECTION[self.section] is not self.tool_name:
            raise ValueError("tool_name does not match section")
        return self


class RetrievalPlanV1(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    handoff_id: Sha256Digest
    unresolved_questions: tuple[EvidenceNeed, ...]
    requests: tuple[RetrievalRequestV1, ...]
    max_tools: Annotated[int, Field(ge=0, le=3)]
    policy_version: Identifier

    @model_validator(mode="after")
    def validate_plan(self) -> RetrievalPlanV1:
        ensure_unique(self.unresolved_questions, field_name="unresolved_questions")
        ensure_unique(
            tuple(request.section for request in self.requests),
            field_name="requests.section",
        )
        if len(self.requests) > self.max_tools:
            raise ValueError("retrieval plan exceeds max_tools")
        if any(
            request.evidence_need not in self.unresolved_questions
            for request in self.requests
        ):
            raise ValueError("request evidence need is not declared")
        return self

    @property
    def requested_sections(self) -> tuple[Task1RevealSection, ...]:
        return tuple(request.section for request in self.requests)


class RetrievalAttemptV1(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    sequence: Annotated[int, Field(ge=0)]
    section: Task1RevealSection
    tool_name: RetrievalToolName
    evidence_need: EvidenceNeed
    status: RetrievalAttemptStatus
    content_digest: Sha256Digest | None = None
    content_length: Annotated[int, Field(ge=0)] = 0
    truncated: bool = False
    safe_error_code: Identifier | None = None

    @model_validator(mode="after")
    def validate_status(self) -> RetrievalAttemptV1:
        if self.status is RetrievalAttemptStatus.SUCCESS:
            if self.content_digest is None or self.content_length == 0:
                raise ValueError("successful retrieval requires content metadata")
            if self.safe_error_code is not None:
                raise ValueError("successful retrieval cannot contain error")
        else:
            if self.content_digest is not None or self.content_length:
                raise ValueError(
                    "non-success retrieval cannot contain content metadata"
                )
            if (
                self.status
                in {
                    RetrievalAttemptStatus.FAILED,
                    RetrievalAttemptStatus.REJECTED,
                }
                and self.safe_error_code is None
            ):
                raise ValueError("failed retrieval requires safe error code")
        return self


class EvidenceLedgerV1(StrictFrozenModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    handoff_id: Sha256Digest
    attempts: tuple[RetrievalAttemptV1, ...]

    @model_validator(mode="after")
    def validate_attempts(self) -> EvidenceLedgerV1:
        if tuple(item.sequence for item in self.attempts) != tuple(
            range(len(self.attempts))
        ):
            raise ValueError("attempt sequence must be contiguous")
        ensure_unique(
            tuple(item.section for item in self.attempts),
            field_name="attempts.section",
        )
        return self

    @property
    def successful_sections(self) -> tuple[Task1RevealSection, ...]:
        return tuple(
            item.section
            for item in self.attempts
            if item.status is RetrievalAttemptStatus.SUCCESS
        )
