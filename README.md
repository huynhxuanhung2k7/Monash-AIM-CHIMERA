# Monash AIM CHIMERA — Task 1

This repository contains the from-scratch `project2` implementation workspace
for CHIMERA-Agent Task 1: prostate biopsy recommendation.

## Team split

- `smoovie`: Blocks 1–2 — data, deterministic features, pathway assessment,
  decision predictor, validation, and the upstream handoff service.
- `xuanhung_07`: Blocks 3–5 — selective evidence retrieval, structured local
  LLM assessment, arbitration, grounded reasoning, safety, and runtime.

## Setup

Install `uv`, then run:

```bash
git clone https://github.com/huynhxuanhung2k7/Monash-AIM-CHIMERA.git
cd Monash-AIM-CHIMERA/project2
uv sync --locked
uv run pytest
uv run ruff check .
uv run mypy
```

The committed `pyproject.toml` and `uv.lock` define the shared Python 3.12
environment for Blocks 1–5. Do not commit `.venv/`.

## Read before development

1. `AGENTS.md`
2. `PROJECT_CONTEXT.md`
3. `project2/AGENTS.md`
4. `project2/PROJECT_CONTEXT.md`
5. `project2/README.md`
6. `project2/docs/BLOCKS_3_5_START_PLAN.md`
7. `project2/docs/TASK1_BLOCKS_1_2_DECISION_ENGINE_HANDBOOK.md`
8. `project2/docs/TASK1_BLOCKS_3_5_AGENT_SYSTEM_HANDBOOK.md`

## Repository safety boundary

Training cases, local models, restricted clinical references, PDFs/books,
generated outputs, archives, secrets, and virtual environments are excluded.
Obtain the official Task 1 data separately and keep it outside version control.

The official output is only the binary `"yes"`/`"no"` decision and the locked
structured-reasoning payload. Internal probability and model diagnostics must
never appear in challenge output.
