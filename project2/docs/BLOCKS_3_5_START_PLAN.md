# Project2 Blocks 3–5 Start Plan

Status: **active implementation sequence**
Workspace: **`project2/` only**
Owner: **xuanhung_07**
Upstream collaborator: **smoovie, Blocks 1–2**

## Objective

Build the consumer half of the Task 1 selective-hybrid system from scratch:

```text
normalized case
  -> fake or real Task1DecisionService
  -> validated DecisionHandoffV1
  -> Block 3 selective retrieval / structured LLM assessment
  -> Block 4 deterministic single-owner arbitration
  -> frozen yes/no decision
  -> Block 5 grounded reasoning / validation / serialization
  -> two official JSON files
```

The first milestone is not a working chatbot. It is a contract-tested skeleton
that can consume either the fake or real Blocks 1–2 service and cannot leak
private predictor fields into output.

## Non-negotiable boundaries

- Do not modify or import source directly from `../project/`.
- Do not depend on training tables, labels, fold assignments, sklearn objects,
  or predictor feature-column internals.
- Do not let the LLM perform PSA arithmetic, thresholding, routing, or final
  arbitration.
- Do not expose hidden chain-of-thought.
- Do not reveal unavailable `pathology_report` data under the current active
  Task 1 tool contract.
- Do not include probability in challenge output.
- Do not add restricted guideline RAG.

## Bootstrap sequence

### Gate 0.1 — repository foundation

Status: **completed and verified 2026-08-22**.

Create:

- `pyproject.toml` with Python 3.12 and deliberately pinned direct dependencies.
- `src/chimera_task1/` package.
- `tests/contract`, `tests/unit`, `tests/integration`, and `tests/reliability`.
- Minimal formatter/linter/type-check configuration only if the team will run
  it consistently.

Acceptance:

- Fresh virtual environment installs the package.
- One smoke import and one empty test run succeed from documented commands.
- No undeclared dependency is imported.

Verified with Python `3.12.13`, `uv 0.11.14`, the committed `uv.lock`, one
passing bootstrap test, clean Ruff output, and clean strict mypy output.

### Gate 0.2 — terminal output contracts

Create strict frozen models for:

- Binary decision root value: `yes | no`.
- Confidence: `clear | borderline | uncertain`.
- Ten variable weights with
  `not_used | noted | important | decisive`.
- The five currently enabled reveal sections.
- Reasoning payload with only `confidence`, `variable_weights`, `free_text`, and
  `reveal_sequence`.

Acceptance:

- Unknown fields and duplicate reveals fail.
- Both `yes` and `no` round-trip as JSON strings.
- Any probability-like or internal diagnostic field fails output validation.

### Gate 0.3 — cross-team handoff contracts

Create V1 strict frozen models for:

- Normalized case input.
- Decision features.
- Preliminary pathway assessment.
- Input-quality assessment.
- Predictor assessment.
- Decision handoff and routing reasons.
- Typed input, artifact, and inference errors.

Acceptance:

- Contract fixture round-trips through JSON.
- NaN, infinity, extra fields, unknown enums, and incompatible versions fail.
- Handoff case/artifact identities are internally consistent.
- Both owners approve the fixture before parallel implementation diverges.

### Gate 0.4 — fake upstream service

Implement deterministic fixtures for at least:

1. High-confidence predictor-owned `yes`.
2. High-confidence predictor-owned `no`.
3. Low-margin routed case.
4. Unclear pathway.
5. Known-positive pathway requiring context.
6. Critical missingness.
7. Structured contradiction.
8. Out-of-distribution case.
9. Artifact mismatch hard failure.
10. Inference hard failure.

Acceptance:

- Blocks 3–5 import only the service protocol and transfer models.
- The fake has no labels or reference reasoning.
- Consumer tests can later run unchanged against the real service.

## Block 3 sequence

### 3.1 Retrieval authorization

Implement deterministic evidence-need codes and map each to the smallest
allowed section set. Current enabled sections are:

- `previous_notes`
- `radiology_report`
- `psa_trend`
- `laboratory_results`
- `family_history`

Every request, success, failure, and returned source fragment receives a typed
ledger entry. The declared `reveal_sequence` is derived from successful ledger
entries, never invented by the LLM.

### 3.2 Structured LLM request

The LLM receives only:

- Compact validated handoff information needed for the routed case.
- Retrieved patient evidence authorized for that case.
- Closed pathway, decision, confidence, and evidence-reference enums.
- A strict instruction to return the assessment schema only.

The response contains an assessment, not final challenge output and not hidden
chain-of-thought. Use bounded parse/repair; schema-invalid or unsupported output
is rejected with a typed reason.

### 3.3 Block 3 acceptance

- Predictor-owned cases make zero adjudication calls.
- Routed cases make no unauthorized calls.
- Tool and model call budgets are enforced.
- Evidence references resolve to actual ledger entries.
- Deterministic replay under the same fixture is stable enough for tests.

## Block 4 sequence

Create a pure arbiter whose inputs are the immutable handoff, optional validated
LLM assessment, and frozen policy version.

Required outcomes:

- Predictor-owned -> predictor decision.
- Routed + accepted promoted assessment -> LLM decision.
- Routed + missing/rejected assessment -> explicit policy-defined result or
  visible failure; never a silent fallback.
- Artifact/version mismatch -> hard failure.

The result records exactly one owner, the final binary decision, agreement or
disagreement, typed reason, and policy version. It contains no final prose.

Acceptance:

- One test per truth-table row.
- No double owner and no ownerless successful result.
- The decision becomes immutable before Block 5.
- LLM verbal confidence is never averaged with model probability.

## Block 5 sequence

### 5.1 Deterministic reasoning plan

Construct confidence, variable weights, important/decisive factors, and reveal
sequence from arbitration, pathway, quality, and evidence-ledger state.

### 5.2 Grounded free text

Generate concise text that:

- Matches the frozen decision.
- Mentions only supported decision-time facts.
- Separates cancer risk from current biopsy indication.
- Acknowledges missing or contradictory evidence when relevant.
- Does not claim cancer without valid pathology.

### 5.3 Validation and serialization

Run schema, grounding, semantic consistency, reveal-ledger equality, forbidden
field, and reliability gates. Positively construct the allow-listed output
objects; never serialize the internal handoff and then delete known fields.

Write only:

```text
/output/prostate-biopsy-decision.json
/output/prostate-biopsy-decision-reasoning.json
```

Acceptance:

- Exact output keys and enums.
- No probability or other private diagnostic.
- Zero duplicate or undeclared reveals.
- Every non-`not_used` variable satisfies evaluator grounding policy.
- All reliability fixtures either produce valid outputs or fail visibly under
  the declared policy.

## Integration gate

Replace the fake service with `smoovie`'s real service only when:

- The same contract fixture and consumer suite pass.
- Schema and artifact-policy versions match.
- Blocks 3–5 require no import or behavior change.
- A joint pull request records the contract hash and accepted artifact manifest.

## Definition of the first completed milestone

The Blocks 3–5 foundation is complete when a fresh environment can run all fake
service scenarios through the output validator, predictor-owned cases bypass
the LLM, routed cases follow bounded retrieval/assessment paths, the arbiter
always names one owner, and the two output payloads contain no probability or
private fields.
