# Project2 Task 1 Context

Last updated: **2026-08-22**
Status: **from-scratch workspace; Blocks 3–5 active**
Primary owner: **xuanhung_07**
Upstream owner: **smoovie, Blocks 1–2**

## Durable session memory

This file is the first source of truth for implementation work under
`project2/`.

- The implementation starts from an empty workspace. Never assume that code,
  tests, dependencies, artifacts, or commands from `../project/` exist here.
- `../project/` is read-only reference material. Historical results remain
  useful as comparators but do not prove that `project2` works.
- Build Task 1 only. Task 2 and Task 3 are out of scope.
- Current scope is Blocks 3–5. Blocks 1–2 arrive through a jointly frozen API.
- Develop against a fake upstream service first, then swap in the real service
  without changing the consumer.
- The final challenge output never contains probability.
- Do not package EAU/NCCN guideline text, derivatives, RAG chunks, or embeddings
  without the written permissions required by the root project policy.

## Task and terminal output

The system decides whether prostate biopsy is recommended now. This is a
clinical management decision, not merely clinically significant prostate
cancer risk prediction.

Exactly two files are written:

```text
/output/prostate-biopsy-decision.json
/output/prostate-biopsy-decision-reasoning.json
```

The decision file is a JSON string: `"yes"` or `"no"`.

The reasoning file contains exactly:

- `confidence`
- `variable_weights`
- `free_text`
- `reveal_sequence`

No probability, threshold, margin, model identity, route, or internal
diagnostic is part of the terminal contract.

## Blocks 3–5 responsibility

### Block 3 — selective retrieval and structured LLM assessment

- Inspect the immutable upstream handoff.
- Retrieve only evidence necessary for a routed case.
- Track every successful reveal in an evidence ledger.
- Ask the local LLM for a strict structured assessment, not chain-of-thought.
- Reject unsupported facts, invalid enums, and schema drift.

### Block 4 — deterministic decision arbitration

- Ensure exactly one decision owner.
- Predictor-owned cases bypass LLM adjudication.
- Routed cases may use an LLM assessment only under the frozen promotion and
  evidence policies.
- Record typed disagreement and fallback reasons.
- Freeze the binary decision before reasoning prose is generated.

### Block 5 — reasoning, safety, evaluation, and runtime

- Construct evaluator-facing confidence and variable weights deterministically.
- Ground weighted variables in always-visible or actually revealed evidence.
- Generate concise free text consistent with the frozen decision.
- Run schema, grounding, semantic, reliability, and offline-runtime gates.
- Serialize only the two official output payloads.

## Upstream boundary

Blocks 3–5 consume one method:

```python
Task1DecisionService.assess(
    *,
    normalized_case: Task1NormalizedFeatures,
) -> DecisionHandoffV1
```

The handoff includes a preliminary pathway assessment, input-quality status,
the predictor's binary decision and private diagnostics, routing recommendation,
typed routing reasons, and artifact/version identity. Private diagnostics may
be used for deterministic routing but must be blocked from final serialization.

The exact V1 field contract is defined in
`docs/TASK1_BLOCKS_1_2_DECISION_ENGINE_HANDBOOK.md` and repeated for the
consumer in `docs/TASK1_BLOCKS_3_5_AGENT_SYSTEM_HANDBOOK.md`.
When implementation begins, the actual versioned Pydantic models and contract
fixtures in `project2/src/chimera_task1/contracts/` become canonical. A breaking
change requires both owners' approval and a schema-version change.

## Current technical decisions

- Python 3.12.
- Pydantic v2 strict, frozen, `extra="forbid"` transfer models.
- Pytest for contract, unit, integration, and reliability tests.
- Local Qwen through an OpenAI-compatible client for development.
- Offline vLLM is the intended submission runtime, subject to later GPU and
  packaging qualification.
- MCP over standard input/output for patient-section retrieval.
- No LangChain dependency unless a measured need justifies adding it.
- No external inference service or runtime network access.

Versions are not inherited automatically from the old project. Pin them in the
new `pyproject.toml` and provenance records when bootstrap begins.

## Environment bootstrap state

Completed on **2026-08-22**:

- `pyproject.toml` declares Python `>=3.12,<3.13`.
- `uv.lock` freezes the complete resolved dependency graph.
- The full Blocks 1–5 manifest declares NumPy, Pandas, SciPy, scikit-learn,
  joblib, Pydantic, MCP, HTTPX, and Jinja2.
- CatBoost is isolated in the optional `tabular` extra; it is not part of the
  default runtime or a promoted model.
- vLLM remains a pinned Linux container runtime and is not a host dependency.
- Development tooling includes pytest, pytest-cov, Ruff, mypy, and Pandas type
  stubs.
- `.python-version` selects Python 3.12.
- `.gitignore` excludes `.venv`, caches, generated reports, local output, and
  environment-secret files.
- The minimal `src/chimera_task1` package installs successfully.
- `uv lock --check`, `uv sync --locked`, pytest, Ruff, and mypy pass under
  Python `3.12.13` with `uv 0.11.14`.
- The optional `tabular` environment was also installed and import-tested;
  CatBoost and every declared Blocks 1–5 direct dependency import successfully.

After cloning, a teammate runs:

```bash
cd project2
uv sync --locked
```

Do not commit `.venv/`. It contains machine-specific paths and is not a
portable substitute for the committed lockfile.

## Immediate implementation gate

The next session should not begin with the LLM. Environment bootstrap is done;
it should now create and test:

1. Official decision/reasoning output models.
2. `DecisionHandoffV1` and nested cross-team models.
3. A fake `Task1DecisionService` with representative routing scenarios.
4. Consumer contract tests and serializer deny-list tests proving that no
   probability reaches terminal output.

Only after this foundation passes should Block 3 retrieval and LLM assessment
be implemented.

## Required references

- Root active context: `../PROJECT_CONTEXT.md`
- Detailed Blocks 3–5 handbook:
  `docs/TASK1_BLOCKS_3_5_AGENT_SYSTEM_HANDBOOK.md`
- Upstream Blocks 1–2 handbook:
  `docs/TASK1_BLOCKS_1_2_DECISION_ENGINE_HANDBOOK.md`
- Decision log: `../project_records/DECISION_LOG.md`
- Leakage register and experiment registry under `../project_records/`
- Clinical and knowledge-source restrictions required by `../AGENTS.md`
