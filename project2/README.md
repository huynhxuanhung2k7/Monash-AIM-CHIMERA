# CHIMERA Task 1 — Project2

Status: **new canonical implementation workspace**
Started: **2026-08-22**
Initial owner/workstream: **xuanhung_07 — Blocks 3–5**
Shared scope: **complete Task 1 Blocks 1–5 repository**

## Start here

Read:

1. `PROJECT_CONTEXT.md`
2. `docs/BLOCKS_3_5_START_PLAN.md`
3. `docs/TASK1_BLOCKS_1_2_DECISION_ENGINE_HANDBOOK.md` for the upstream-owner
   contract
4. `docs/TASK1_BLOCKS_3_5_AGENT_SYSTEM_HANDBOOK.md` for the detailed downstream
   design reference

## Workspace rule

This folder starts from scratch. It does not inherit source code, environment,
artifacts, commands, or passing-test claims from `../project/`. The old folder
is a historical comparator and design reference only.

The intended implementation tree is:

```text
project2/
├── AGENTS.md
├── PROJECT_CONTEXT.md
├── README.md
├── pyproject.toml                 # create during bootstrap
├── configs/                       # versioned runtime/policy config
├── docs/
├── src/chimera_task1/
│   ├── contracts/                 # shared frozen API and outputs
│   ├── agent/                     # Block 3
│   ├── evidence/                  # Blocks 3 and 5
│   ├── arbitration/               # Block 4
│   ├── reasoning/                 # Block 5
│   ├── runtime/                   # Block 5
│   └── testing/                   # fake upstream service/fixtures
├── tests/
│   ├── contract/
│   ├── unit/
│   ├── integration/
│   └── reliability/
├── reports/                       # generated, provenance-controlled
└── submission/                    # added only after local gates pass
```

The tree is a specification, not evidence that the listed files already exist.

## Current next action

Environment bootstrap is complete. The next milestone is the contract
foundation:

1. Locked output schemas.
2. Blocks 1–2 handoff contract.
3. Fake `Task1DecisionService` and scenario fixtures.
4. Contract tests proving the fake can later be replaced without consumer
   changes.

Do not start prompt tuning or model calls before these gates pass.

## Reproducible environment

The project uses `uv` and Python 3.12. Dependency choices live in
`pyproject.toml`; exact transitive versions live in `uv.lock`. Do not commit or
share `.venv/`, because virtual environments contain machine-specific paths.

Bootstrap verified on 2026-08-22 with `uv 0.11.14` and Python `3.12.13`.
`uv lock --check`, locked synchronization, pytest, Ruff, and mypy all pass.

Initial setup after cloning:

```bash
git clone https://github.com/huynhxuanhung2k7/Monash-AIM-CHIMERA.git
cd Monash-AIM-CHIMERA/project2
uv sync --locked
uv run pytest
```

If `smoovie` is running the optional CatBoost experiment after its promotion
prerequisites are approved:

```bash
uv sync --locked --extra tabular
```

For an already-cloned repository:

```bash
cd project2
uv sync --locked
uv run pytest
```

Daily commands:

```bash
uv run pytest
uv run ruff check .
uv run mypy
```

When an approved dependency changes:

```bash
uv add <package>
uv lock
uv sync --locked
```

Commit both `pyproject.toml` and `uv.lock` in the same pull request. A teammate
then runs only `uv sync --locked`; they do not select versions manually.

### Dependency ownership

| Package | Blocks | Purpose |
|---|---|---|
| NumPy, Pandas, SciPy | 1–2 | Auditing, deterministic features, numeric transformations |
| scikit-learn, joblib | 1–2 | Fold-safe models, calibration, metrics, artifact loading |
| Pydantic | 1–5 | Strict immutable cross-folder and output contracts |
| MCP | 3 and 5 | Local standard-input/output patient-evidence tools |
| HTTPX | 3 and 5 | Local OpenAI-compatible Ollama/vLLM client transport |
| Jinja2 | 3 and 5 | Versioned prompt templates |
| pytest, coverage, Ruff, mypy | 1–5 | Tests, coverage, linting, and type checks |
| CatBoost (`tabular` extra) | 2 | Optional shallow tabular-model experiment only |

vLLM is supplied by the pinned Linux submission container and is deliberately
not installed into the shared macOS CPU environment. LangChain and guideline
RAG dependencies are intentionally excluded.
