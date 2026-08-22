# Task 1 Experiment Registry

Last updated: **2026-08-13**

This registry is an experiment specification, not an implementation plan. Add a
row only when the hypothesis, validation protocol, leakage controls, and
keep/reject rule are explicit.

## Shared validation contract

- Repeated stratified cross-validation for performance estimation.
- Nested inner folds for preprocessing, feature selection, hyperparameters,
  calibration, and F1 threshold selection.
- Patient/group boundaries applied before any fit.
- Every transform fitted inside the corresponding training fold.
- Primary: positive-class F1.
- Secondary: sensitivity, specificity, precision, balanced accuracy, confusion
  matrix, ROC-AUC, PR-AUC, Brier score, and calibration.
- Agent experiments additionally report gate pass rate, tool precision, section
  grounding, schema failure rate, and runtime.
- Every external corpus, pretrained model, and static knowledge asset needs a
  recorded source, version, license, permitted-use rationale, and packaging
  decision before an experiment begins.
- No experiment may use EAU/NCCN PDFs, copied or paraphrased guideline corpora,
  guideline embeddings, or the baseline's prebuilt guideline database unless
  written permission explicitly covers the experiment and intended submission.

## Decision-model ladder

| ID | Status | Hypothesis | Inputs | Keep criterion |
|---|---|---|---|---|
| B-000 | Descriptive | Always-`yes` is a strong prevalence baseline. | None | Reference only; current in-sample F1 0.762. |
| B-001 | Descriptive | PI-RADS alone provides a stronger clinical rule. | PI-RADS | Re-estimate out of fold; current PI-RADS >= 4 in-sample F1 0.806. |
| B-002 | Planned | Pathway-aware rule improves errors over PI-RADS alone. | PI-RADS, prior biopsy, PSAD, DRE, age/comorbidity guardrails | Stable F1 gain without unacceptable sensitivity loss. |
| B-003 | Rejected | Elastic-net logistic regression improves generalization while remaining interpretable. | Small audited structured feature set plus missingness flags | Rejected: repeated OOF mean F1 0.7096 and 0/20 repeats beat always-`yes`; retain as a research artifact only. |
| B-004 | Conditional | A shallow tabular model captures useful nonlinear interactions. | Same audited features as B-003 | Improvement persists across repeats and is not driven by one fold or center. |
| B-005 | Conditional | Calibration and a nested F1 threshold improve decisions. | Best stable B-003/B-004 score | Better nested out-of-fold F1 and acceptable calibration; no global tuning. |
| B-006 | Deferred | MRI representation adds independent evidence. | Fold-safe compact MRI head plus best tabular score | Stable repeated out-of-fold gain after late-fusion ablation. |
| B-007 | Deferred | Ensemble reduces variance. | Only independently validated components | Gain exceeds uncertainty and complexity/runtime cost. |

## Agent-system ladder

| ID | Status | Hypothesis | Major change | Keep criterion |
|---|---|---|---|---|
| A-000 | Kept | Locked-schema deterministic output eliminates avoidable zero scores. | Serializer and validation only | Zero schema failures on all 195 Task 1 inputs and all smoke fixtures. |
| A-001 | Kept as control | Official MCP plus a fixed patient-evidence retrieval policy establishes a license-clean runner reference. | No guideline RAG; selective deterministic retrieval of CHIMERA case evidence | 0.9846 mean tool score and bounded runtime. It is an explicit comparator, not a silent candidate fallback. |
| A-002 | Kept | Evidence ledger prevents ungrounded weights and hallucinated reasoning. | Source-to-variable ledger plus output precheck | 1.0 mean section-grounding score and zero output-gate failures. |
| A-003 | Planned | Compact tabular evidence improves final decisions. | Add best B-series predictor as a supporting tool | Better nested decision F1 without worse schema/grounding/runtime reliability. |
| A-004 | Blocked | A license-audited clinical RAG source may improve predefined borderline pathway decisions. | Add only a provenance-recorded corpus whose license explicitly permits software, AI, modification, redistribution, and challenge packaging; do not use the current EAU/NCCN baseline database | Written license approval first; then improvement concentrated in predeclared borderline cases without excess tool cost or grounding errors. |
| A-005 | Deferred | MRI predictor evidence improves cases not resolved by structured data. | Add fold-safe B-006 output | Stable gain after missingness and domain-shift stress tests. |
| A-006 | Reliability kept; competitive promotion rejected | A bounded Qwen3-4B-Instruct-2507 agent improves reasoning/tool alignment while preserving the predictor's decision F1. | Replace deterministic retrieval/text generation with LLM-selected MCP tools and LLM form fill; hybrid decision remains locked to predictor | Reliability passed, but exact judged ranking 0.662 did not exceed control 0.686. Keep as complete LLM runner; do not select before held-out evidence reverses the comparison. |
| A-007 | Not promoted after exploratory spot check | LLM-owned decisions improve pathway-discordant cases. | Allow the same Qwen agent to choose yes/no after seeing predictor evidence | Repeated held-out decision F1 and ranking both exceed hybrid mode without unacceptable sensitivity loss. |
| A-008 | Planned | Gemma 4 E2B-it offers a better quality/runtime trade-off than Qwen. | Swap only the pinned LLM and tool format | Same frozen cases/prompts; improve ranking or materially reduce runtime/VRAM without worse schema/fallback rate. |

## Required experiment entry template

```text
ID:
Date:
Owner:
Hypothesis:
Single major change:
Data and labels used:
Decision-time availability check:
Knowledge-source provenance and license check:
Patient/group split rule:
Preprocessing fitted inside folds:
Threshold-selection procedure:
Primary and secondary metrics:
Expected result:
Failure interpretation:
Keep/reject criterion:
Result:
Decision:
```

## Recorded complete-runner result

```text
ID: A-001/A-002 runner v1
Date: 2026-08-12
Data and labels used: 91 labeled Version 2 training cases; all 195 inputs for runtime smoke
Decision-time availability check: structured prompt and MCP-retrieved Task 1 sections only
Knowledge-source provenance and license check: CHIMERA inputs only; no guideline corpus
Predictor: fixed pirads_ge_4 rule
Evaluator: official commit 55c7ca..., rationale judge disabled
Ranking score: 0.6884608489 (in-sample)
F1 yes: 0.8059701493
Mean case score: 0.5709515485
Mean tool score: 0.9846153846
Mean section grounding: 1.0
Decision: keep as deterministic control; do not call it the complete LLM agent, use it as a silent candidate fallback, or claim validation performance
```

## Recorded real-model integration result

```text
ID: A-006 local Q4 integration smoke
Date: 2026-08-12
Model: qwen3:4b-instruct-2507-q4_K_M (development quantization)
Mode: hybrid; deterministic fallback disabled
Data: one unlabeled synthetic new-case fixture, PT-NEW-001
Result: pass; decision and reasoning schema-valid; fallback_used=false
Agent calls: 3 total LLM calls, 1 tool round, 1 form attempt
Reveals: radiology_report and previous_notes
Warnings: none
Automated suite: 56 passed
Container: deterministic control linux/amd64 build/run passed; GPU LLM image not runnable on this Mac
Decision: keep A-006 as the implemented default runner; full frozen-cohort and FP16 GPU evaluation remains required
```

```text
ID: A-007 exploratory known-positive spot check
Date: 2026-08-12
Model: qwen3:4b-instruct-2507-q4_K_M
Mode: LLM-owned; deterministic fallback disabled
Data: two labeled prior-positive cases selected to expose opposing pathway outcomes
Result after pathway-prompt repair: one reference-no decision correct and one reference-yes decision incorrect
Failure interpretation: the 4B LLM does not reliably separate cancer risk, surveillance/confirmatory biopsy, and established treatment pathways
Decision: do not promote LLM-owned decision mode; this is an exploratory failure signal, not a performance estimate
```

```text
ID: A-006 frozen Q4 cohort benchmark
Date: 2026-08-13
Model: qwen3:4b-instruct-2507-q4_K_M (development quantization)
Mode: hybrid; pirads_ge_4 decision locked; deterministic fallback disabled
Data: all 195 Task 1 input folders; evaluator metrics use only the 91 released labels
Decision-time availability: structured prompt plus case sections returned by local official-protocol MCP stdio tools
Knowledge-source check: CHIMERA inputs and Apache-2.0 Qwen only; no guideline RAG or EAU/NCCN assets
Reliability result: 195/195 completed, 0 errors, 0 fallbacks, maximum 3 form attempts
Latency: 12.108 s mean, 9.970 s median, 26.992 s p95, 50.826 s maximum on Apple-Silicon local Q4
Warnings: 90/195 cases required at least one bounded semantic repair or safe normalization
Repeatability: one difficult case repeated three times with byte-identical decision and reasoning outputs
Official evaluator: commit 55c7ca21487e5fd32042e5093bf5b019fc9e6c6c, rationale judge disabled
Ranking score: 0.6610719183 (in-sample)
F1 yes: 0.8059701493
Mean case score: 0.5161736874
Mean tool score: 0.9000000000
Mean section grounding: 1.0000000000
Deterministic control comparison: ranking 0.6884608489 under the same evaluator
Decision: keep as complete LLM implementation and reliability-qualified candidate; exact rationale judging did not reverse the ordering, so reject competitive promotion unless held-out evidence beats the control
```

```text
ID: A-006 exact rationale-inclusive evaluator replay
Date: 2026-08-14
Evaluator: official commit 55c7ca21487e5fd32042e5093bf5b019fc9e6c6c
Judge: exact evaluator default gemma4:e4b; enabled for both frozen systems
Data: all 91 released labeled Task 1 cases; in-sample diagnostic only
Qwen: ranking 0.6618449647, mean case 0.5177197802, rationale 0.7169230769
Control: ranking 0.6864397152, mean case 0.5669092812, rationale 0.7123076923
Shared decision F1 yes: 0.8059701493
Interpretation: Qwen's 0.0046 rationale gain does not offset weaker confidence, variable-weight, and tool alignment.
Decision: competitive promotion rejected; use the control as the first validation benchmark unless held-out evidence changes the ordering
```

## Task 2 completed experiments — 2026-08-13

| ID | Validation | Result | Decision |
|---|---|---:|---|
| T2-B000 majority active treatment | In-sample descriptive | weighted F1 0.2592 | Floor only |
| T2-B001 ISUP control | Deterministic descriptive | weighted F1 0.8490 | Keep fallback |
| T2-B002 structured logistic | Repeated stratified 2-fold x50; preprocessing inside folds | best mean 0.7572, SD 0.0363, 0/50 wins | Reject |
| T2-B003 hierarchical v1 | In-sample, labels reviewed | weighted F1 1.0000 | External-validation candidate only |
| T2-A001 deterministic reasoning | Pinned evaluator, judge disabled | mean case 0.742, ranking 0.871 | Selected local candidate |
| T2-A002 Qwen LLM-owned | Full 72 released labels | F1 0.9581, ranking 0.777, 1 fallback | Do not promote |
| T2-N001 MRI PCA | Repeated stratified 2-fold x30; fold-local PCA | mean 0.4702 | Reject |
| T2-N002 biopsy PCA | Same | mean 0.6318 | Reject |
| T2-N003 MRI + biopsy PCA | Same | mean 0.5955 | Reject |
| T2-N004 structured late fusion | Same | mean 0.6301 | Reject |

Task 2 reference decisions/reasoning were never used as input features. Case
identifiers and `active_treatment_flag` were excluded. The hierarchical policy
is explicitly not called held-out evidence because it was specified after
error review. Full reports are under `project/reports/task2/`.
