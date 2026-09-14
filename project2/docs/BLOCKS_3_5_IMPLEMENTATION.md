# Blocks 3–5 Implementation Handoff

Verified: **2026-09-14**
Scope: **Task 1 consumer system in `project2/`**

## Outcome

Blocks 3–5 are implemented end to end against the contract-faithful fake
`Task1DecisionService`. A normalized case can now flow through selective
retrieval, strict structured adjudication, deterministic arbitration, grounded
reasoning, validation, and atomic serialization of the two official outputs.

## Component map

| Area | Implementation |
|---|---|
| Shared boundary | `contracts/decision_handoff.py`, `decision/service.py` |
| Stage 3 contracts | `contracts/retrieval.py`, `contracts/adjudication.py` |
| Stage 3 policy/runtime | `agent/retrieval_planner.py`, `evidence/ledger.py`, `agent/stage3.py` |
| Local inference | `llm/client.py`, `agent/prompts.py` |
| MCP evidence adapter | `tools/retrieval/mcp_client.py` |
| Stage 4 | `contracts/arbitration.py`, `arbitration/arbiter.py` |
| Stage 4 metrics | `evaluation/arbitration_metrics.py` |
| Stage 5 | `reasoning/planner.py`, `reasoning/renderer.py`, `reasoning/validation.py` |
| End-to-end runtime | `runtime/runner.py`, `runtime/serializer.py` |
| Official-output check | `evaluation/official_adapter.py` |
| Fake integration boundary | `testing/fake_decision_service.py`, `testing/fake_llm.py` |

## Safety properties

- Predictor-owned cases bypass retrieval and LLM inference.
- Routed cases use a deterministic, deduplicated, maximum-three-tool plan over
  the five enabled sections; pathology is not exposed.
- The LLM endpoint must be localhost HTTP, and generation has fixed bounded
  parameters.
- Assessment parsing is strict and permits at most one schema-repair attempt.
- Rejected, insufficient, or unpromoted assessments produce an explicit typed
  predictor fallback; artifact-policy mismatches fail hard.
- Arbitration names exactly one owner and freezes the final binary decision.
- Active output weights require visible or successfully revealed evidence;
  `bx` and `comorbidity` remain `not_used`.
- Output prose is decision-consistent and rejects cancer overclaims or private
  predictor diagnostics.
- The serializer accepts only an otherwise-clean output directory, writes only
  the two official filenames, and restores both prior files after a partial
  replacement failure.

## Verification

Run from `project2/`:

```bash
uv sync --locked
uv run pytest -q
uv run pytest --cov=chimera_task1 --cov-report=term-missing -q
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv build
```

Verified result:

- 56 tests passed.
- Ruff formatting and lint checks passed.
- Strict mypy passed across 51 source and test files.
- Branch-aware coverage was 88%.
- The source distribution and wheel built successfully.

Tests cover strict contracts, configuration, all Stage 4 truth-table rows,
bounded repair, retrieval failures, MCP tool mapping, grounded output, atomic
rollback, the complete runner, every fake routed scenario, and typed hard
failures.

## Integration boundary

The real Blocks 1–2 implementation must satisfy
`Task1DecisionService.assess(*, normalized_case) -> DecisionHandoffV1`. Swapping
the fake for that service must require no consumer-code changes.

The following are deliberately recorded as pending shared candidate gates, not
as implementation failures or fabricated verification claims:

- real-service contract compatibility;
- paired predictor-only/selective-hybrid promotion evaluation;
- replay across the released 195 cases and the official evaluator;
- frozen model and artifact provenance;
- offline container, latency/memory, and T4/A10G qualification.

Those gates require upstream artifacts, challenge data, evaluator assets, and
target hardware that are not included in this source-only implementation.
