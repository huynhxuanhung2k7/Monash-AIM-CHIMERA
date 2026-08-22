# Project2 Task 1 Working Instructions

These instructions refine the repository-root `AGENTS.md` for work under
`project2/`. The root instructions continue to apply.

## Mandatory context

Before Task 1 work, read in this order:

1. `../PROJECT_CONTEXT.md`
2. `PROJECT_CONTEXT.md`
3. `docs/BLOCKS_3_5_START_PLAN.md`
4. `../project_records/DECISION_LOG.md`
5. Any relevant root clinical, leakage, experiment, risk, or knowledge-source
   record required by `../AGENTS.md`

## Active scope

- `project2/` is the canonical new implementation root.
- `../project/` is reference-only. Do not modify it during `project2` work.
- The active workstream is Task 1 Blocks 3–5.
- Begin against a contract-faithful fake Blocks 1–2 decision service.
- Do not implement Blocks 1–2 unless the user explicitly changes ownership.
- Do not assume any old source file, dependency, artifact, test, or command has
  been migrated. Add and verify each dependency deliberately.

## Output boundary

The official output consists of:

- `/output/prostate-biopsy-decision.json`: JSON string `"yes"` or `"no"`.
- `/output/prostate-biopsy-decision-reasoning.json`: the locked structured
  reasoning object.

No probability, threshold, margin, routing value, model name, or private
predictor diagnostic may be serialized into either file.

## Historical reuse rule

Architecture and tests from `../project/` may be inspected. Reuse requires a
written reason, license/provenance check where relevant, adaptation to the new
contracts, and new tests in `project2/`. Never bulk-copy the old project and
call it a from-scratch rebuild.
