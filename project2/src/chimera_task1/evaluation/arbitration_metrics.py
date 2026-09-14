"""Aggregate Stage 4 routing and reliability metrics."""

from collections import Counter
from collections.abc import Iterable

from chimera_task1.contracts.arbitration import (
    ArbitrationFallbackReason,
    ArbitrationMetricsV1,
    DecisionAgreement,
    DecisionArbitrationResultV1,
    DecisionOwner,
)


def summarize_arbitrations(
    results: Iterable[DecisionArbitrationResultV1],
) -> ArbitrationMetricsV1:
    values = tuple(results)
    owners = Counter(item.decision_owner for item in values)
    agreements = Counter(item.agreement for item in values)
    fallbacks = Counter(item.fallback_reason for item in values if item.fallback_reason)
    return ArbitrationMetricsV1(
        total=len(values),
        predictor_owned=owners[DecisionOwner.PREDICTOR],
        llm_owned=owners[DecisionOwner.LLM],
        predictor_fallback=owners[DecisionOwner.PREDICTOR_FALLBACK],
        agreements=agreements[DecisionAgreement.AGREE],
        disagreements=agreements[DecisionAgreement.DISAGREE],
        not_assessed=agreements[DecisionAgreement.NOT_ASSESSED],
        fallback_counts=tuple(
            (reason, fallbacks[reason])
            for reason in ArbitrationFallbackReason
            if fallbacks[reason]
        ),
    )
