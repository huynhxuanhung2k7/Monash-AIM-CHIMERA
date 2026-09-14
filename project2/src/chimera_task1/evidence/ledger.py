"""Execute approved retrievals while persisting metadata rather than content."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from hashlib import sha256

from chimera_task1.contracts.retrieval import (
    EvidenceLedgerV1,
    RetrievalAttemptStatus,
    RetrievalAttemptV1,
    RetrievalPlanV1,
    Task1RevealSection,
)
from chimera_task1.tools.retrieval.client import RetrievalClient

_FORBIDDEN_MARKERS = (
    "pathology_report",
    "reference_decision",
    "reference_reasoning",
    "ground_truth_label",
)


@dataclass(frozen=True, slots=True)
class RetrievedEvidence:
    section: Task1RevealSection
    content: str
    content_digest: str
    truncated: bool


@dataclass(frozen=True, slots=True)
class RetrievalExecution:
    ledger: EvidenceLedgerV1
    evidence: tuple[RetrievedEvidence, ...]
    required_failure: bool


async def execute_retrieval_plan(
    plan: RetrievalPlanV1,
    client: RetrievalClient,
    *,
    timeout_seconds: float = 8.0,
    max_content_chars: int = 6000,
) -> RetrievalExecution:
    if timeout_seconds <= 0 or max_content_chars < 100:
        raise ValueError("invalid retrieval limits")
    attempts: list[RetrievalAttemptV1] = []
    evidence: list[RetrievedEvidence] = []
    required_failure = False
    for sequence, request in enumerate(plan.requests):
        raw: str | None
        error: str | None
        try:
            async with asyncio.timeout(timeout_seconds):
                raw = await client.retrieve(request.section)
        except TimeoutError:
            status = RetrievalAttemptStatus.FAILED
            error = "retrieval_timeout"
            raw = None
        except Exception:  # noqa: BLE001
            status = RetrievalAttemptStatus.FAILED
            error = "retrieval_provider_error"
            raw = None
        else:
            status = RetrievalAttemptStatus.SUCCESS
            error = None
        content = "" if raw is None else raw.strip()
        if status is RetrievalAttemptStatus.FAILED:
            attempts.append(
                RetrievalAttemptV1(
                    sequence=sequence,
                    section=request.section,
                    tool_name=request.tool_name,
                    evidence_need=request.evidence_need,
                    status=status,
                    safe_error_code=error,
                )
            )
            required_failure |= request.required
            continue
        if not content:
            attempts.append(
                RetrievalAttemptV1(
                    sequence=sequence,
                    section=request.section,
                    tool_name=request.tool_name,
                    evidence_need=request.evidence_need,
                    status=RetrievalAttemptStatus.EMPTY,
                )
            )
            required_failure |= request.required
            continue
        if any(marker in content.casefold() for marker in _FORBIDDEN_MARKERS):
            attempts.append(
                RetrievalAttemptV1(
                    sequence=sequence,
                    section=request.section,
                    tool_name=request.tool_name,
                    evidence_need=request.evidence_need,
                    status=RetrievalAttemptStatus.REJECTED,
                    safe_error_code="forbidden_evidence_marker",
                )
            )
            required_failure |= request.required
            continue
        safe = content[:max_content_chars]
        digest = f"sha256:{sha256(safe.encode()).hexdigest()}"
        evidence.append(
            RetrievedEvidence(
                section=request.section,
                content=safe,
                content_digest=digest,
                truncated=len(content) > len(safe),
            )
        )
        attempts.append(
            RetrievalAttemptV1(
                sequence=sequence,
                section=request.section,
                tool_name=request.tool_name,
                evidence_need=request.evidence_need,
                status=RetrievalAttemptStatus.SUCCESS,
                content_digest=digest,
                content_length=len(safe),
                truncated=len(content) > len(safe),
            )
        )
    return RetrievalExecution(
        ledger=EvidenceLedgerV1(handoff_id=plan.handoff_id, attempts=tuple(attempts)),
        evidence=tuple(evidence),
        required_failure=required_failure,
    )
