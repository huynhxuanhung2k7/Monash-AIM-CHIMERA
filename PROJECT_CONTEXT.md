# CHIMERA-Agent Task 1 Project Context

> **ACTIVE WORKSPACE RESET — 2026-08-22**
>
> The canonical implementation workspace is now `project2/`. All new Task 1
> source code, tests, configuration, reports, and implementation documentation
> must be created there unless the user explicitly changes this decision.
> `project/` is frozen as a read-only historical/reference implementation. Do
> not continue development in it and do not copy its code into `project2/`
> without an explicit component-by-component review.
>
> The first active workstream in `project2/` is **Blocks 3–5**: selective
> evidence retrieval and structured local-LLM adjudication, deterministic
> decision arbitration, and grounded reasoning/safety/runtime output. Blocks
> 3–5 must begin against a fake implementation of the frozen Blocks 1–2 API so
> work does not depend on the predictor branch being finished.
>
> Future sessions must read `project2/PROJECT_CONTEXT.md` and
> `project2/docs/BLOCKS_3_5_START_PLAN.md` before proposing or performing Task 1
> implementation work.

> Implementation handoff added 2026-08-12: see
> `project_records/TASK1_BASELINE_HANDOFF.md` for the completed deterministic
> and logistic baseline state, verified commands, reports, artifact, and next
> build sequence.

> Selective-hybrid redesign proposed 2026-08-22: see
> `project_records/TASK1_SELECTIVE_HYBRID_REBUILD_PLAN.md` for the pathway-aware
> decision architecture, validation gates, and two-person work split.

Last verified: **2026-08-22**
Scope: **Task 1 — Prostate Biopsy Decision**
Status: **`project2/` active; Blocks 3–5 first; `project/` reference-only**

> LLM implementation update, 2026-08-12: the user approved
> `Qwen/Qwen3-4B-Instruct-2507` revision `cdbee75...` as the primary local
> model, `google/gemma-4-E2B-it` revision `3e22461...` as a comparison, and
> hybrid decision ownership as the default. The earlier runner v1 is now
> explicitly the deterministic control, not the complete LLM agent or a silent
> submission fallback.

> Runner verification update, 2026-08-13: the bounded Qwen agent, five MCP
> tools, pathway-note policy, terminal form repair, grounding validators,
> short `./task1` workflow, and offline GPU Docker specification are
> implemented under `project/`. The frozen local Q4 hybrid completed all
> 195 Task 1 inputs with zero errors and zero fallbacks; 84 automated tests
> pass. The exact rationale-inclusive 91-label replay scored Qwen at 0.662
> ranking and 0.717 rationale versus the deterministic control at 0.686 and
> 0.712. Both share F1 0.806, so Qwen is not competitively promoted.
> Exact FP16 weights are downloaded and hash-recorded for a separate read-only
> Grand Challenge Model mount. GPU execution remains pending on a T4/A10G host.

## Read this first

Task 1 is currently a **clinical management decision**, not merely a cancer-risk
prediction problem. The required decision is whether prostate biopsy is
recommended now (`"yes"` or `"no"`). A csPCa probability may support that
decision, but it is neither the label nor the final output.

When documents disagree, use this precedence:

1. Current official evaluator implementation and locked output schema.
2. Live official CHIMERA-Agent pages fetched directly.
3. Current official baseline repository.
4. On-disk training release and its README.
5. Local overview documents and notebooks.

The challenge is active. Re-verify metric-, schema-, evaluator-, deadline-, and
submission-dependent claims before making a consequential decision.

All project reasoning, commentary, persistent documentation, and final answers
must be written in English unless the user explicitly changes that preference.

## Current Task 1 contract

| Item | Current interpretation |
|---|---|
| Clinical question | In the MRI-only pre-biopsy setting, should this patient undergo prostate biopsy now? |
| Decision output | `"yes"` or `"no"` in `prostate-biopsy-decision.json` |
| Reasoning output | `confidence`, ten `variable_weights`, flat `reveal_sequence`, and `free_text` in a second JSON file |
| Public primary metric | F1 score |
| Evaluator behavior | Schema check, hard Task 1 decision gate, then reasoning/tool/grounding scoring for gate-passing cases |
| Execution | Docker container, offline, official MCP interface, no external APIs or web services at inference |
| External datasets/models | Freely and publicly available under a permissive open-source license; preserve provenance and re-verify the exact rule before submission |
| Submission allowance | Up to 5 validation submissions; 1 test submission |
| Method paper | 6 pages in MICCAI Springer LNCS format, excluding references, required for final ranking eligibility |

The signed-in live Task 1, Submission, Rules, and Baseline/Evaluation pages were
rechecked on **2026-08-14**. The decision/output contract, F1-plus-rationale
wording, offline execution, five validation submissions, one test submission,
six-page paper, and T4/A10G hardware targets were unchanged.

Current published dates: registration/training release **10 July 2026**,
validation phase **10 August 2026**, test submission deadline
**10 September 2026**, and MICCAI **27 September–1 October 2026**.

The evaluator reports `decision_f1_yes`, `mean_case_score`, and `ranking_score`.
The current Task 1 leaderboard formula is explicit:
`(mean_case_score + decision_f1_yes) / 2`.

## Official evaluator snapshot

- Repository: <https://github.com/DIAGNijmegen/CHIMERA-agent/tree/main/evaluation>
- Verified commit: `55c7ca21487e5fd32042e5093bf5b019fc9e6c6c`
- Commit date: 2026-07-31
- Task 1 decision is a hard per-case gate: an incorrect `yes`/`no` decision
  produces a zero case score before granular reasoning evaluation.
- Gate-passing cases are scored on confidence agreement, variable-weight
  agreement, important/decisive factor set-F1, tool-use precision, section
  grounding, and optionally local-LLM rationale alignment.
- Tool scoring is asymmetric precision: unnecessary reveals are penalized;
  missing reference reveals are not penalized.
- If no tools are used, tool score is 1.0, but any non-`not_used` variable still
  needs appropriate source grounding unless it is always available.
- Only baseline PSA and age are marked always available in evaluator mapping.
  PI-RADS, PSA density, csPCa score, prostate volume, DRE, family history,
  prior-biopsy status, and comorbidity can require a mapped reveal.

### Material contradiction

The current baseline README says “only the final structured output is evaluated;
tool use is not scored.” The current evaluator and the live official
“Baseline and Evaluation Repositories” page explicitly score tool use and
section grounding. Follow the evaluator. Do not inherit the README statement as
an optimization assumption.

The live Submission, Rules, and Baseline/Evaluation pages also say that model
weights/resources must be inside the submitted Docker container. In contrast,
official baseline commit `1afa788e...` creates a separate `model.tar.gz` Grand
Challenge Model asset mounted at `/opt/ml/model`. The local package currently
follows that executable baseline pattern, but the contradiction is unresolved;
obtain written organizer confirmation before upload and embed the model if the
live-page wording is enforced literally.

## Local Task 1 data snapshot

Verified against `train_release/train_release/task1` on 2026-07-19:

| Item | Count |
|---|---:|
| Input case folders | 195 |
| Cases with decision labels | 91 |
| `yes` labels | 56 |
| `no` labels | 35 |
| Cases with reference reasoning | 91 |
| Cases with a non-empty MRI representation | 191 |
| MRI representation size | 1024 dimensions |

Do not treat the 104 unlabeled Task 1 cases as negative. They may be useful for
data auditing or representation analysis, but pseudo-labeling requires a
separate risk assessment.

### Descriptive rule checks on the 91 labeled cases

These are **in-sample diagnostics**, not validation estimates:

| Rule | F1 (`yes`) | Sensitivity | Precision |
|---|---:|---:|---:|
| Always `yes` | 0.762 | 1.000 | 0.615 |
| PI-RADS >= 3 | 0.794 | 1.000 | 0.659 |
| PI-RADS >= 4 | 0.806 | 0.964 | 0.692 |
| PI-RADS >= 4, or PI-RADS 3 with PSAD >= 0.15 | 0.803 | 0.982 | 0.679 |

The always-positive baseline is strong because 56 of 91 labeled cases are
positive. Any learned system must beat it out of fold and must report precision,
sensitivity, specificity, and the confusion matrix alongside F1.

## Correct clinical framing

Always separate:

1. **csPCa risk prediction** — likelihood of clinically significant prostate
   cancer.
2. **Biopsy recommendation** — whether biopsy is appropriate at the current
   decision point.
3. **Decision explanation** — which reliable, decision-time factors support or
   oppose the recommendation.

Classify each case conceptually before deciding:

- Biopsy-naive.
- Prior negative biopsy with persistent suspicion.
- Known positive biopsy with possible confirmatory/surveillance context.
- Unclear or contradictory pathway.

A high csPCa score does not automatically imply another biopsy. The score is an
uncalibrated model output, not confirmed pathology or a validated risk score.

## 2026 EAU reference review

The user supplied the 2026 full and pocket EAU prostate-cancer guidelines. They
were read as clinical references, with focused review of the diagnostic pathway,
PSA and PSA density, MRI and PI-RADS, biopsy indication, repeat-biopsy context,
patient health status, and copyright terms. Detailed provenance and a
non-reproductive synthesis are in
`project_records/CLINICAL_REFERENCE_REVIEW.md`.

The review reinforces these Task 1 concepts:

- The target is a management decision that balances the risk of missed
  clinically significant cancer against biopsy harms and overdiagnosis.
- Patient pathway must be established before risk evidence is interpreted.
- PSA is affected by benign disease, infection, retention, measurement
  conditions, recent procedures, and medications; a single value can be
  misleading.
- PSA density is useful but inherits uncertainty from PSA and prostate-volume
  measurement.
- PI-RADS describes MRI suspicion, not pathology. MRI sensitivity and predictive
  value vary with image quality, readers, sites, and population prevalence.
- Negative MRI does not automatically rule out clinically important disease;
  other risk evidence and prior-biopsy context remain relevant.
- Age alone is not an adequate management rule; health, life expectancy,
  comorbidity, preferences, and expected benefit matter.
- Published thresholds and risk calculators are not automatically calibrated to
  CHIMERA. Any operational threshold must be selected and tested inside training
  folds.

These are conceptual guardrails, not copied EAU recommendations. They do not
make EAU the challenge ground truth, and they do not resolve ambiguity in the
organizers' reference decisions.

### EAU licensing conclusion

The live EAU copyright page was verified on 2026-07-21. Its terms restrict
reproduction and use of EAU guideline content or derived products in software,
AI, LLM, and machine-learning systems without written permission. Therefore:

- Do not package the EAU PDFs, text, tables, figures, recommendation excerpts,
  extracted chunks, summaries intended as a corpus, embeddings, or derived rule
  text in this repository, a prompt, RAG store, model context, Docker image, or
  submission without written permission covering that use.
- Do not assume that paraphrasing, non-commercial participation, offline
  execution, or citation supplies permission.
- The restriction does not ban the LLM itself. The LLM can reason over CHIMERA
  patient evidence and license-audited knowledge; it simply must not be fed or
  bundled with restricted EAU material.
- The official baseline's prebuilt guideline database contains retrievable raw
  guideline chunks, so its inclusion in the official repository is not enough
  evidence that participants have a sublicense. Keep it disabled and excluded
  from deliverables until written organizer or rights-holder clarification.
- NCCN content requires its own permission review and remains blocked from
  packaging meanwhile.

The public CHIMERA forum topic requesting EAU/NCCN clarification had no organizer
answer when checked on 2026-07-21. Record any future response and its exact scope
before changing this policy. See `project_records/KNOWLEDGE_SOURCE_REGISTER.md`.
This is a conservative project compliance decision, not legal advice.

## What the official baseline is

The current official baseline head is
`1afa788efc21c0e0144706d75170b0a4cd267367` (2026-08-10). Its history was
rewritten relative to the older local clone, so the old and current heads have
no common ancestor. The local `baseline/` folder remains at
`67141cff279572e7a8ac26e24347c141f3747486` (2026-07-16), with a user change in
`model/README.md`. Treat the live head as the current scaffold and the local
clone as a historical reference.

The baseline remains a **reference submission scaffold**, not a trained Task 1
decision model.

Core components:

- LangGraph ReAct loop.
- Clinical tools served through MCP over standard input/output.
- Local guideline retrieval-augmented generation (RAG).
- Offline Gemma 4 E2B-it through vLLM by default.
- Terminal form-fill step with Pydantic validation and retries.
- Grand Challenge Docker and flat-input adapter.
- MRI feature loader and an opt-in predictor stub; no trained MRI predictor.

The baseline's RAG component is architectural reference code only under the
current project policy. Do not copy its prebuilt guideline database into a
submission unless the rights question is resolved. The rest of the agent can
operate without guideline RAG: deterministic features and predictors can supply
decision evidence, tools can reveal patient-specific records, and the LLM can
synthesize grounded reasoning into the locked schema.

### Baseline reading order

1. `baseline/README.md` — end-to-end contract and supported workflow.
2. `baseline/src/chimera_agent_baseline/output/schema.py` — locked output shape.
3. `baseline/src/chimera_agent_baseline/case_loader.py` — visible versus
   tool-gated input handling.
4. `baseline/src/chimera_agent_baseline/tools/definitions.py` and
   `baseline/src/chimera_agent_baseline/mcp_server.py` — tool boundaries.
5. `baseline/src/chimera_agent_baseline/agent/graph.py` — ReAct control flow.
6. `baseline/src/chimera_agent_baseline/agent/prompts.py`,
   `baseline/templates/prompts/agent_prompt.j2`, and
   `baseline/src/chimera_agent_baseline/agent/form_fill.py` — reasoning and
   terminal output generation.
7. `baseline/src/chimera_agent_baseline/rag.py` — local guideline retrieval.
8. `baseline/src/chimera_agent_baseline/features.py` and
   `baseline/src/chimera_agent_baseline/tools/predictor.py` — embeddings and the
   predictor extension point.
9. `baseline/inference.py`, Dockerfiles, and test inputs — platform contract.

## Recommended architecture posture

The first competitive target should be a **structured hybrid**, built on the
baseline interface:

1. A small, regularized tabular predictor provides compact decision evidence.
2. Deterministic feature computation handles PSA trend, PSA density checks,
   missingness, and pathway flags.
3. Selective MCP retrieval reveals only evidence needed to resolve the case.
4. An evidence ledger records which source supports every weighted variable.
5. The LLM synthesizes pathway-aware reasoning and fills the locked schema; it
   should not improvise calculations or act as the only predictor.
6. MRI embeddings enter only through a fold-safe auxiliary predictor that emits
   a compact score, uncertainty, and version metadata.

Required benchmark ladder:

1. Always-positive and majority baselines.
2. Simple clinical rules.
3. PI-RADS plus prior-biopsy/pathway rules.
4. Regularized logistic regression.
5. Shallow tabular model only if it adds stable out-of-fold value.
6. Structured retrieval and grounding layer.
7. Optional MRI late fusion after ablation evidence.
8. Full agent refinements only after simpler systems are stable.

## Validation posture

- Use repeated stratified cross-validation; use nested validation for feature,
  model, calibration, and threshold selection.
- Fit imputation, scaling, feature selection, PCA, calibration, and threshold
  selection inside training folds only.
- Keep patient duplicates and near-duplicates in the same fold.
- Report positive-class F1 plus sensitivity, specificity, precision, balanced
  accuracy, confusion matrix, ROC-AUC, PR-AUC, Brier score, and calibration.
- Measure both decision quality and evaluator-facing reasoning/grounding quality.
- Add only one major component per experiment and define a keep/reject rule in
  advance.

## Immediate team priorities

1. Treat `project2/` as empty: establish its Python package, strict contracts,
   tests, configuration, and runtime boundaries without assuming modules from
   `project/` already exist.
2. Freeze the Blocks 1–2 -> Blocks 3–5 handoff schema and build a deterministic
   fake `Task1DecisionService` covering predictor-owned, routed, contradictory,
   missing-data, and out-of-distribution cases.
3. Implement and test Block 3 selective retrieval and structured Qwen
   assessment against the fake service.
4. Implement Block 4 as a deterministic single-owner arbiter. Do not average
   model probabilities with LLM verbal confidence.
5. Implement Block 5 output construction, evidence grounding, validation, and
   serialization. Official output is exactly a `"yes"`/`"no"` JSON value plus
   the required reasoning object; no probability or private predictor
   diagnostic may appear in either output file.
6. Integrate the real Blocks 1–2 service only after it passes the same contract
   tests as the fake service.
7. Continue tracking unresolved organizer questions: the `bx`/pathology
   grounding mismatch, stable patient/centre identifiers and timestamps,
   model-asset packaging, and guideline-source rights.

## Live official sources

- [Task 1](https://chimera-agent.grand-challenge.org/task-1-mri-only-diagnostic-decision/)
- [Data sources and imaging](https://chimera-agent.grand-challenge.org/data-sources-and-imaging/)
- [Baseline and evaluation repositories](https://chimera-agent.grand-challenge.org/baseline-and-evaluation-repositories/)
- [Official baseline repository](https://github.com/DIAGNijmegen/chimera-agent-baseline)
- [Official evaluator](https://github.com/DIAGNijmegen/CHIMERA-agent/tree/main/evaluation)
- [Submission](https://chimera-agent.grand-challenge.org/submission/)
- [Timeline](https://chimera-agent.grand-challenge.org/challenge-timeline/)
- [Rules](https://chimera-agent.grand-challenge.org/rules/)
- [EAU copyright and terms of use](https://uroweb.org/guidelines/prostate-cancer/chapter/copyright-and-terms-of-use)
- [CHIMERA forum: permission to include EAU/NCCN guidelines](https://chimera-agent.grand-challenge.org/forum/topics/permission-to-include-eaunccn-guidelines-in-offline-submissions/)

## Stale or secondary local material

`CHIMERA-agent_Overview.md` and the Task 1 notebook use an older
csPCa-probability/AUROC framing. They may still contain useful medical or EDA
material, but they are not authoritative for the current Task 1 decision output
or optimization target.
