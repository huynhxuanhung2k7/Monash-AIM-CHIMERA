# Task 1 Selective-Hybrid Rebuild Plan

Status: **Proposed**
Last updated: **2026-08-22**
Scope: **CHIMERA-Agent Task 1 — prostate biopsy recommendation**
Owners: **smoovie — Blocks 1–2, Data/Pathway and Decision Predictor;**
**xuanhung_07 — Blocks 3–5, Large Language Model (LLM) Adjudication,
Arbitration, Reasoning, Safety, Evaluation, and Integration**

Official-contract verification: **2026-08-22.** The live official evaluator
repository still has `55c7ca21487e5fd32042e5093bf5b019fc9e6c6c` as the latest
main-branch commit. Its README continues to specify binary `yes`/`no`, the hard
decision gate, Task 1 ranking as the mean of positive-class F1 and mean case
score, and six evaluator reveal names. Sources: [official evaluator
README](https://github.com/DIAGNijmegen/CHIMERA-agent/tree/main/evaluation) and
[verified commit](https://github.com/DIAGNijmegen/CHIMERA-agent/commit/55c7ca21487e5fd32042e5093bf5b019fc9e6c6c).

Execution is split into two self-contained owner handbooks:

- `project/docs/TASK1_BLOCKS_1_2_DECISION_ENGINE_HANDBOOK.md` for `smoovie`.
- `project/docs/TASK1_BLOCKS_3_5_AGENT_SYSTEM_HANDBOOK.md` for `xuanhung_07`.

The internal predictor may calculate probability for calibration and routing,
but the official output contains no probability: only the binary decision and
the required structured-reasoning file.

## Decision

Do not rebuild the complete repository. Preserve the reliable Task 1 contracts,
loaders, normalization, Model Context Protocol (MCP) interface, evidence ledger,
serializer, and offline packaging. Concentrate the rebuild on the decision
engine and on the connection between clinical-pathway context and decision
ownership.

Use a **selective hybrid**:

- A calibrated pathway-aware predictor owns cases only when its evidence and
  out-of-fold confidence gate are satisfied.
- Cases with low predictor confidence, unresolved pathway context, critical
  missingness, or out-of-distribution warnings enter a structured local LLM
  adjudication branch.
- The LLM branch may own a decision only after it earns promotion against the
  predictor-only system. Invalid or evidence-insufficient LLM output falls back
  explicitly to the predictor and records the reason.
- After the final decision is frozen, deterministic evidence planning supplies
  confidence, variable weights, and reveal sections. The LLM writes only the
  concise grounded free-text explanation.

## Why this redesign is necessary

The current hybrid locks every binary decision to Prostate Imaging Reporting
and Data System (`PI-RADS`) `>= 4`. Qwen selects
tools and writes reasoning but cannot correct the decision. On the 91 released
labels, the rule produces F1 `0.8060`, 54 true positives, 24 false positives,
11 true negatives, and 2 false negatives. Sensitivity is `0.9643`, but
specificity is only `0.3143`.

A pathway audit shows that 24 of the 26 decision errors occur in known-positive
cases: 22 false positives and 2 false negatives. Biopsy-naive cases have no
released-label error under the current rule, and prior-negative cases have two
false positives. This is an in-sample development finding, not external
validation. It establishes the primary hypothesis: the current system confuses
cancer or magnetic resonance imaging (MRI) risk with whether another biopsy is
indicated in the patient's current management pathway.

The current Qwen reasoning layer also reduces the exact released-label ranking
from `0.6864` for the deterministic control to `0.6618`, despite identical F1.
The main losses are variable-weight, decisive-factor, and tool alignment. The
redesign therefore treats decision quality and evaluator-facing reasoning as
two separate optimization problems.

## Preserved and changed components

### Preserve

- Locked Task 1 input, decision, and reasoning schemas.
- Version 2 strict loading, normalization, and reference-output isolation.
- Official MCP stdio protocol and patient-section allowlist.
- Evidence ledger, section-grounding validator, semantic consistency checks,
  bounded repair, and locked serialization.
- Grand Challenge flat adapter, offline runtime, model provenance, and package
  verification.
- Always-yes, `pirads_ge_4`, deterministic-control, and logistic-v0 results as
  mandatory comparators.

### Redesign

- Direct and deterministic derived features used for the biopsy decision.
- Pathway classification before decision ownership is selected.
- A calibrated pathway-aware decision predictor.
- Predictor confidence, completeness, contradiction, and out-of-distribution
  assessment.
- Structured LLM management-state assessment for routed uncertain cases.
- Deterministic arbitration between predictor and LLM assessments.
- Evaluator-aligned retrieval, confidence, variable weights, and final
  explanation.

### Defer

- Raw or reduced MRI-representation models.
- Ensembles beyond independently promoted components.
- Gemma comparison until the Qwen architecture is frozen.
- Any external clinical corpus or guideline retrieval-augmented generation
  (RAG).
- Pseudo-labeling of the 104 unlabeled cases.

## Target architecture

```text
Grand Challenge inputs
  -> existing contract validation and loading
  -> normalized direct features
  -> deterministic pathway and consistency features
  -> calibrated pathway-aware predictor
  -> confidence and evidence gate
       -> eligible high-confidence case: predictor owns decision
       -> uncertain/context-dependent case:
            deterministic selective retrieval
            -> structured Qwen management and biopsy assessment
  -> deterministic decision arbiter
       -> predictor | validated LLM | explicit predictor fallback
  -> deterministic reasoning plan
       confidence + variable weights + reveal sequence + top factors
  -> LLM free-text synthesis constrained to the frozen decision
  -> existing grounding, semantic, schema, and serialization gates
  -> unchanged Task 1 output files
```

## Five-block implementation architecture

This is one process inside the existing offline Task 1 application, not five
network services. The integration boundary is a versioned Python/Pydantic
contract. This avoids local HTTP overhead, duplicated schemas, startup races,
and unnecessary Docker complexity.

```text
Existing Task 1 loader and normalization
               |
               v
+---------------------------------------------------------------+
| smoovie branch                                                |
|                                                               |
| Block 1: Data, deterministic features, and structured pathway |
|               |                                               |
|               v                                               |
| Block 2: Calibrated decision predictor and ownership gate     |
+----------------------------+----------------------------------+
                             |
                    DecisionHandoffV1
                             |
+----------------------------v----------------------------------+
| xuanhung_07 branch                                            |
|                                                               |
| Block 3: Selective retrieval and structured Qwen adjudication |
|               |                                               |
|               v                                               |
| Block 4: Deterministic ownership and decision arbiter         |
|               |                                               |
|               v                                               |
| Block 5: Reasoning plan, grounding, evaluator, runtime, Docker|
+---------------------------------------------------------------+
                             |
                             v
            Existing locked Task 1 JSON outputs
```

The dependency direction is one-way: Blocks 3–5 may import the public
contracts and inference facade from Blocks 1–2. They must not import training
scripts, cross-validation objects, fold assignments, labels, or unfrozen model
objects.

## Detailed block build plan

### Block 1 — Data, features, and preliminary pathway (`smoovie`)

Purpose: convert the existing normalized case into a small, auditable,
decision-time feature object. This block does not make the final recommendation.

Build:

1. Freeze a field inventory for every structured-prompt field: medical meaning,
   type, unit, accepted range, soft-missing values, decision-time availability,
   leakage status, and whether it is included in each feature experiment.
2. Preserve the existing strict loader and normalization; add a new
   `DecisionFeaturesV1` layer rather than teaching the model to interpret raw
   JSON or free text.
3. Produce direct features for age, Prostate-Specific Antigen (PSA), previous
   PSA, supplied PSA velocity, PI-RADS, reported PSA density, prostate volume,
   supplied clinically significant prostate cancer (csPCa) score, Digital
   Rectal Examination (DRE), and structured biopsy history.
4. Produce deterministic derived features: recalculated PSA density when both
   PSA and volume are valid, reported-versus-recalculated PSA-density error,
   PSA delta, PSA delta direction, missingness counts, invalid-range flags,
   unknown-category flags, and consistency flags.
5. Produce a preliminary structured pathway assessment from visible biopsy
   history only: `biopsy_naive`, `prior_negative`, `known_positive`, or
   `unclear`. It must be named preliminary because previous notes are still
   masked and Block 3 may refine the management state after retrieval.
6. Keep raw `medical_history`, previous notes, reports, case identifiers,
   pathology, future treatment, reference reasoning, and neural embeddings out
   of the first predictor feature matrix.
7. Produce field-level provenance so downstream code can distinguish
   `direct`, `derived`, `missing`, `invalid`, and `not_available`.

Block 1 output:

- `DecisionFeaturesV1`.
- `StructuredPathwayAssessmentV1`.
- `InputQualityAssessmentV1`.
- A frozen feature-name/order manifest for every trained artifact.

Block 1 completion criteria:

- The same case always produces the same feature object.
- All ranges, categories, and missing values are tested.
- Recalculated values never overwrite reported values silently.
- A forbidden-field test proves that labels, reference outputs, pathology,
  future treatment, IDs, narratives, and embeddings are absent.
- Feature generation works for all 195 released cases, including the 104
  unlabeled cases, without treating an unlabeled case as `no`.

### Block 2 — Decision predictor and routing gate (`smoovie`)

Purpose: produce the strongest defensible biopsy-decision estimate and state
whether the predictor has earned ownership of this specific case. This is the
highest-priority block because wrong decisions receive zero case score before
reasoning is evaluated.

Training architecture:

```text
DecisionFeaturesV1
  -> fold-local imputation and categorical encoding
  -> candidate classifier
  -> raw probability of biopsy=yes
  -> fold-local calibration
  -> sensitivity-constrained threshold
  -> probability margin + pathway/input/OOD checks
  -> PredictorAssessmentV1
```

Candidate ladder, always evaluated through the same nested-validation harness:

1. Always-yes and current `PI-RADS >= 4` controls.
2. Existing five-feature logistic-v0 control.
3. Elastic-net logistic regression using F0–F3 feature sets.
4. Shallow histogram gradient boosting with tightly bounded depth/leaves.
5. CatBoost with conservative depth, regularization, early stopping inside the
   inner folds, and a recorded dependency/license review before packaging.
6. A pathway-specialized candidate only if simpler pooled models leave a stable
   known-positive error pattern. It must not be selected from in-sample pathway
   metrics alone.

Model-selection rules:

- Fit every imputer, encoder, scaler, feature selector, model, calibrator,
  threshold, and ownership margin inside the appropriate training fold.
- Compare Platt/sigmoid and isotonic calibration only when the inner-fold sample
  size supports them; otherwise retain uncalibrated probability and mark the
  calibration method explicitly.
- Select the yes/no threshold inside inner folds to maximize positive-class F1
  subject to sensitivity `>= 0.90`.
- Prefer the simplest eligible candidate within `0.01` mean outer F1 of the
  best eligible model.
- Do not tune against the 104 unlabeled cases, reference reasoning, or the
  frozen official replay.
- Report pooled and pathway-specific confusion matrices. A known-positive gain
  is not acceptable if it causes unstable biopsy-naive or prior-negative harm.

Case-ownership gate:

The predictor may set `ownership_eligible=true` only when all conditions hold:

- Model and feature manifests load and their hashes match.
- Required preprocessing and calibration versions match the artifact.
- No critical feature is invalid.
- Preliminary pathway is not `unclear`.
- No unresolved contradiction or out-of-distribution flag is active.
- Absolute calibrated-probability margin from the threshold meets the
  fold-selected margin.
- The margin achieved at least `0.85` conditional accuracy and `0.30` coverage
  in inner out-of-fold predictions.
- For `known_positive`, at least ten owned inner out-of-fold examples exist and
  conditional accuracy is at least `0.85`; otherwise every such case routes to
  Block 3.

Block 2 artifacts:

- Frozen preprocessing/model pipeline.
- Calibrator, or explicit `none` calibration record.
- Decision threshold and ownership-margin policy.
- Feature manifest with ordered fields and types.
- Training-data digest, code revision, random seeds, dependency versions, and
  nested-validation report.
- `PredictorArtifactManifestV1` used to validate the runtime artifact before
  any case is processed.

Block 2 completion criteria:

- Repeated nested-validation report contains all required metrics and paired
  comparisons.
- Runtime predictions match the frozen fold-independent artifact.
- Probability, threshold, decision, and margin are mathematically consistent.
- Every case returns either an eligible predictor decision or an explicit route
  to Block 3; there is no ambiguous `None` ownership state.
- Predictor failures are typed and observable; they never silently become a
  default `yes` or an unrestricted LLM decision.

### Block 3 — Selective retrieval and Qwen adjudication (`xuanhung_07`)

Purpose: resolve cases that the predictor cannot safely own, especially unclear
or known-positive management pathways. Qwen is a structured adjudicator, not a
wrapper that merely rewrites the predictor output.

Current enabled Task 1 patient-evidence sections:

| Section | Tool | Primary use |
|---|---|---|
| `previous_notes` | `get_previous_notes` | Confirmatory/surveillance versus established-treatment context; contradictions in biopsy history |
| `radiology_report` | `get_mri_report` | MRI context when PI-RADS or MRI-derived factors are decision-changing |
| `psa_trend` | `get_psa_trend` | Dated trajectory when trend quality can change the decision |
| `laboratory_results` | `get_lab_results` | Specific non-visible workup evidence; headline PSA is already visible |
| `family_history` | `get_family_history` | First-degree family-history modifier when unresolved and decision-changing |

The official evaluator recognizes a sixth name, `pathology_report`, and the raw
clinical JSON may contain that field. The current Task 1 tool registry and
locked project output schema do not expose it. Neither branch may use or reveal
it until the organizers confirm decision-time availability and the team updates
the contract deliberately. This prevents post-decision leakage and keeps the
branches compatible with the active runtime.

Retrieval policy:

- Call Block 3 only when `routing_recommendation="llm_required"`.
- Require `previous_notes` for preliminary `known_positive` or `unclear`
  pathways unless the section is empty; record empty evidence explicitly.
- Retrieve other sections only for a declared unresolved question. The LLM may
  request from the five-name allowlist, but deterministic policy approves or
  rejects the request and enforces deduplication and the tool budget.
- Do not retrieve a section merely to improve prose. Tool scoring is precision-
  only, so unnecessary reveals directly reduce the case score.
- Put only the handoff packet, approved retrieved evidence, output schema, and
  decision question in the prompt. Never include labels, reference reasoning,
  evaluator results, or hidden ground truth.

Qwen must return `LlmDecisionAssessmentV1`, not final Task 1 JSON. Required
content: decision, management state, evidence sufficiency, supporting and
opposing factors, unresolved contradictions, consulted sections, and a compact
uncertainty explanation. It must not return chain-of-thought.

Block 3 completion criteria:

- All outputs validate or are explicitly rejected.
- Consulted sections exactly equal successful tool results.
- An empty or failed retrieval cannot be described as supporting evidence.
- The same frozen model/prompt/seed produces stable structured assessments
  within the agreed reproducibility tolerance.
- LLM decision ownership remains feature-flagged off until paired validation
  passes the promotion rule.

### Block 4 — Decision arbiter (`xuanhung_07`)

Purpose: choose exactly one decision owner and freeze the binary decision before
confidence, variable weights, reveal sequence, or free text are generated.

Arbitration truth table:

| Predictor state | LLM state | Owner | Final decision |
|---|---|---|---|
| Eligible | Not called | `predictor` | Predictor decision |
| LLM required | Valid and evidence-sufficient; LLM branch promoted | `llm` | LLM decision |
| LLM required | Invalid, timeout, or evidence-insufficient | `predictor_fallback` | Predictor decision, even though it is low-confidence |
| LLM required | Valid but LLM branch not promoted | `predictor_fallback` | Predictor decision; LLM may inform explanation only if grounded |
| Artifact/schema failure | Any | No owner | Stop the case and report a hard runtime failure |

Rules:

- Qwen cannot override a predictor-owned high-confidence case.
- The arbiter never averages a probability with LLM verbal confidence.
- Disagreement is allowed only in routed cases; if the LLM branch is promoted,
  a valid evidence-sufficient LLM assessment owns that routed decision.
- Every fallback has a machine-readable reason.
- The arbiter emits `DecisionArbitrationResultV1`; later stages receive this
  immutable result and cannot change `final_decision`.

Block 4 completion criteria:

- Unit tests cover every row of the truth table.
- Exactly one owner exists for every successful case.
- Assessment IDs and artifact versions in the result match the inputs.
- Decision mutation after arbitration is rejected.
- Fallback and disagreement rates appear in the evaluation report.

### Block 5 — Reasoning, safety, evaluation, and runtime (`xuanhung_07`)

Purpose: turn the frozen decision into evaluator-aligned, grounded output and
prove that the complete system is reliable offline.

Build:

1. Construct deterministic confidence from probability margin, predictor/LLM
   agreement, pathway certainty, missingness, contradictions, evidence
   sufficiency, fallback state, and out-of-distribution status.
2. Construct variable weights from an evidence ledger. Model importance or
   SHAP values are supporting diagnostics, not automatic `decisive` labels.
3. Construct the reveal sequence from successful retrieval calls only.
4. Choose two to four top factors consistent with the frozen decision; usually
   only one to three should be `decisive`.
5. Ask Qwen to write concise free text from the frozen decision and supplied
   grounded factors. It cannot introduce new facts or reverse the decision.
6. Run section-grounding, semantic consistency, schema, and bounded repair
   gates before serialization.
7. Run exact official-evaluator replay, 195-case reliability, repeated-seed
   checks, offline Docker, latency/memory, and T4/A10G acceptance.

Block 5 completion criteria:

- Both official Task 1 output files are schema-valid for all 195 cases.
- Reveal sequence, weights, and free text agree with actually retrieved
  evidence.
- Grounding is `1.0`, there are zero silent fallbacks, and all decision owners
  are traceable.
- The exact frozen artifact and prompt pass offline and hardware checks.
- The LLM branch remains disabled if it fails the paired promotion gate.

## Public integration application programming interface (API)

### Packaging decision

Use an in-process Python API under `chimera_task1`, with Pydantic models and
JSON round-trip tests. Do not add REST, FastAPI, a socket, or a subprocess at
this boundary. JSON serialization exists for artifacts/tests; runtime calls are
typed Python calls.

Recommended public facade:

```python
class Task1DecisionService(Protocol):
    def assess(
        self,
        *,
        normalized_case: Task1NormalizedFeatures,
    ) -> DecisionHandoffV1: ...
```

The facade accepts the existing normalized case because both Block 1 feature
construction and Block 2 prediction belong to smoovie. Blocks 3–5 must not have
to reproduce feature engineering. The service must reject a raw clinical-data
document, labels, reference outputs, or a mismatched case ID at this boundary.

Blocks 3–5 may import only:

- the existing `Task1NormalizedFeatures` input contract
- `DecisionFeaturesV1`
- `StructuredPathwayAssessmentV1`
- `InputQualityAssessmentV1`
- `PredictorAssessmentV1`
- `PredictorArtifactManifestV1`
- `DecisionHandoffV1`
- `Task1DecisionService`
- documented typed exceptions

### `DecisionHandoffV1`

This is the required return object from `smoovie`'s service. Fields are frozen,
`extra="forbid"`, and JSON serializable.

| Field | Type | Required meaning |
|---|---|---|
| `schema_version` | literal `"1.0"` | Contract compatibility |
| `handoff_id` | string | Deterministic hash of case input plus frozen artifact versions; contains no label |
| `case_id` | string | Runtime correlation only; excluded from all feature matrices |
| `features` | `DecisionFeaturesV1` | Audited direct/derived predictor features and provenance |
| `structured_pathway` | `StructuredPathwayAssessmentV1` | Preliminary pathway from visible structured evidence |
| `input_quality` | `InputQualityAssessmentV1` | Missing, invalid, consistency, contradiction, and OOD information |
| `predictor` | `PredictorAssessmentV1` | Frozen model assessment described below |
| `routing_recommendation` | `predictor_owned` or `llm_required` | Required next action |
| `routing_reasons` | tuple of enums | Why ownership was granted or denied |
| `artifact_manifest_digest` | SHA-256 string | Runtime artifact identity |

### `PredictorAssessmentV1`

Required fields:

| Field | Type | Invariant |
|---|---|---|
| `assessment_id` | string | Deterministic from handoff/model versions |
| `decision` | `yes` or `no` | Must equal calibrated probability compared with threshold |
| `raw_probability_yes` | float `[0,1]` | Model output before calibration |
| `probability_yes` | float `[0,1]` | Calibrated probability, or raw probability when calibration method is `none` |
| `threshold` | float `[0,1]` | Frozen fold-selected operating threshold |
| `signed_margin` | float `[-1,1]` | `probability_yes - threshold` |
| `absolute_margin` | float `[0,1]` | Absolute signed margin |
| `confidence` | `clear`, `borderline`, or `uncertain` | Deterministic policy output, not LLM confidence |
| `ownership_eligible` | boolean | Must agree with routing recommendation |
| `model_name` / `model_version` | strings | Frozen selected candidate |
| `feature_contract_version` | string | Must match `DecisionFeaturesV1` manifest |
| `calibration_method` / `calibration_version` | strings | Explicitly `none` when absent |
| `threshold_policy_version` | string | Frozen sensitivity-constrained policy |
| `ownership_policy_version` | string | Frozen margin/pathway policy |
| `training_data_digest` | SHA-256 string | Exact labeled training release used |
| `model_signals` | tuple | Small diagnostic list of variable, direction, and magnitude; not evaluator weights |
| `warnings` | tuple of enums | Non-fatal runtime/model warnings |

The service must return the complete `DecisionHandoffV1` for every valid
normalized case. Returning only `decision`, only `probability_yes`, a bare
dictionary, an sklearn model, or a mutable dataframe is not contract-compliant.

### Downstream contracts owned by `xuanhung_07`

`LlmDecisionAssessmentV1` consumes one immutable `DecisionHandoffV1` plus
successful retrieval results. It must return:

| Field | Required meaning |
|---|---|
| `assessment_id` | Deterministic ID tied to handoff, prompt, model, seed, and consulted evidence |
| `handoff_id` | Exact upstream handoff used |
| `decision` | Structured `yes` or `no` assessment for this routed case |
| `management_state` | One of the five allowed Task 1 management states |
| `evidence_sufficient` | Whether the evidence supports LLM ownership |
| `supporting_factors` | Small structured list of factor, value/summary, and source section |
| `opposing_factors` | Same structure for evidence against the recommendation |
| `unresolved_contradictions` | Explicit unresolved conflicts |
| `consulted_sections` | Exact ordered unique successful retrieval sections |
| `uncertainty_reasons` | Missing or ambiguous evidence affecting the decision |
| `model_version`, `prompt_version`, `seed` | Reproducibility metadata |

`DecisionArbitrationResultV1` consumes the handoff and optional valid LLM
assessment. It must return:

| Field | Required meaning |
|---|---|
| `arbitration_id` | Deterministic ID for the complete arbitration input |
| `handoff_id` | Exact upstream handoff |
| `predictor_assessment_id` | Exact predictor assessment |
| `llm_assessment_id` | Exact LLM assessment or `null` when not called/invalid |
| `final_decision` | Immutable final `yes` or `no` |
| `decision_owner` | `predictor`, `llm`, or `predictor_fallback` |
| `fallback_reason` | Closed enum or `null` |
| `final_uncertainty_reasons` | Information used later to derive confidence |
| `revealed_sections` | Successful sections available to the reasoning ledger |
| `policy_version` | Frozen arbitration policy |

Allowed `routing_reasons` should be a closed enum, initially:

- `high_confidence_predictor`
- `low_probability_margin`
- `pathway_unclear`
- `known_positive_not_validated`
- `critical_missingness`
- `structured_contradiction`
- `out_of_distribution`
- `artifact_policy_mismatch`

`artifact_policy_mismatch` should normally be a hard startup failure. It remains
in the enum so a rejected handoff can be diagnosed in tests; production must not
continue to Qwen with incompatible artifacts.

### Example handoff

```json
{
  "schema_version": "1.0",
  "handoff_id": "sha256:...",
  "case_id": "runtime-case-id",
  "features": {
    "schema_version": "1.0",
    "pirads": 4,
    "psa": 8.2,
    "reported_psad": 0.18,
    "recalculated_psad": 0.17,
    "prostate_volume": 48.0,
    "biopsy_history": "positive"
  },
  "structured_pathway": {
    "category": "known_positive",
    "confidence": "clear",
    "source": "structured_prompt"
  },
  "input_quality": {
    "critical_missing": [],
    "invalid_fields": [],
    "contradiction_flags": [],
    "ood_flags": []
  },
  "predictor": {
    "assessment_id": "sha256:...",
    "decision": "yes",
    "raw_probability_yes": 0.71,
    "probability_yes": 0.68,
    "threshold": 0.54,
    "signed_margin": 0.14,
    "absolute_margin": 0.14,
    "confidence": "borderline",
    "ownership_eligible": false,
    "model_name": "selected-pathway-model",
    "model_version": "1.0.0",
    "feature_contract_version": "1.0",
    "calibration_method": "sigmoid",
    "calibration_version": "1.0",
    "threshold_policy_version": "1.0",
    "ownership_policy_version": "1.0",
    "training_data_digest": "sha256:...",
    "model_signals": [],
    "warnings": []
  },
  "routing_recommendation": "llm_required",
  "routing_reasons": ["known_positive_not_validated"],
  "artifact_manifest_digest": "sha256:..."
}
```

The example is structural, not a recommendation for a real patient and not a
golden expected prediction.

### Error contract

- Ordinary missingness, pathway uncertainty, or OOD is data, not an exception;
  return a valid handoff with `llm_required`.
- Invalid source schema or impossible values raise `DecisionInputError`; stop
  before either model runs.
- Missing/corrupt/incompatible model artifacts raise `DecisionArtifactError`;
  stop the case and container readiness check.
- Unexpected inference failures raise `DecisionInferenceError`; the runtime
  records them and fails visibly. Do not convert them into `yes`, `no`, or an
  unrestricted LLM decision.
- No API response may contain labels, reference reasoning, fold IDs, training
  rows, raw clinical narratives, or hidden chain-of-thought.

### Contract tests required before parallel integration

1. Both branches validate the same committed JSON examples.
2. JSON serialize/deserialize round trips without information loss.
3. Extra fields, unknown enums, NaN, infinity, inconsistent decision/probability,
   incorrect margin, and ownership/routing disagreement are rejected.
4. `case_id` never appears in the model feature matrix or artifact training
   manifest.
5. Blocks 3–5 run against a fake `Task1DecisionService` before the real model is
   ready.
6. The real service passes the same tests without changes to Blocks 3–5.

## Internal data-contract summary

The public integration API above is normative. This section summarizes the
clinical contents and prohibitions used by those versioned models.

### `DecisionFeaturesV1`

Allowed core inputs:

- Pathway category and pathway-certainty flags.
- PI-RADS, PSA, PSA density, prostate volume, age, DRE, and biopsy history.
- Previous PSA, PSA change, and an audited PSA-velocity quality indicator.
- Reported-versus-recalculated PSA-density consistency.
- Missingness, unknown-category, contradiction, and out-of-distribution flags.
- Supplied csPCa score only as a separately ablated feature.

Forbidden inputs:

- Case identifiers or institution shortcuts.
- Reference decisions, reasoning, confidence, weights, or reveal sequences.
- Post-decision pathology, treatment decisions, or `active_treatment_flag`.
- Raw clinical narratives in the tabular model.
- Neural representations in the first rebuild.
- Labels or pseudo-labels from the 104 unlabeled cases.

### `PredictorAssessmentV1` summary

Required fields:

- `decision`
- calibrated `probability_yes`
- fold-selected decision `threshold`
- probability `margin`
- `pathway`
- `input_complete`
- `contradiction_flags`
- `ood_flags`
- `high_confidence`
- model, feature-contract, calibration, and threshold versions

### `LlmDecisionAssessmentV1` summary

Required fields:

- `decision`
- `management_state`
- `evidence_sufficient`
- supporting factors
- opposing factors
- unresolved contradictions
- source sections actually consulted

Allowed management states:

- `initial_diagnosis`
- `persistent_suspicion_after_negative_biopsy`
- `confirmatory_or_surveillance_biopsy`
- `established_disease_without_current_biopsy_indication`
- `unclear`

The assessment must not contain hidden chain-of-thought, improvise numerical
calculations, treat PI-RADS as pathology, or treat the supplied csPCa score as
confirmed cancer.

### `DecisionArbitrationResultV1` summary

Required fields:

- `final_decision`
- `decision_owner`: `predictor`, `llm`, or `predictor_fallback`
- predictor and LLM assessment identifiers
- `fallback_reason`, when applicable
- final confidence class and uncertainty reasons

The arbiter freezes the decision before evaluator-facing reasoning is created.

## Feature and model experiment ladder

Evaluate feature sets one major addition at a time:

1. `F0`: pathway plus PI-RADS.
2. `F1`: F0 plus PSA, PSA density, volume, age, DRE, missingness, and
   consistency flags.
3. `F2`: F1 plus the supplied csPCa score.
4. `F3`: F2 plus deterministic longitudinal PSA features.

Compare:

1. Always-yes and current PI-RADS rules.
2. Existing logistic-v0 control.
3. Elastic-net pathway-aware logistic regression.
4. A shallow sklearn gradient-boosting model.
5. A pathway-specialized candidate that protects the simpler pathways while
   learning the known-positive branch.

Select the simplest eligible model within `0.01` mean out-of-fold F1 of the
best eligible model. No model is promoted merely because it fits the 91 labels
well in-sample.

## Confidence and ownership policy

Inside each inner validation loop:

1. Select the decision threshold that maximizes positive-class F1 subject to
   sensitivity of at least `0.90`.
2. Select a probability-margin cutoff from `0.05`, `0.10`, `0.15`, `0.20`, and
   `0.25`.
3. Predictor ownership requires conditional accuracy of at least `0.85`,
   coverage of at least `30%`, complete critical inputs, no unresolved pathway
   contradiction, and no out-of-distribution warning.
4. Predictor ownership for known-positive patients additionally requires at
   least ten inner out-of-fold owned cases and conditional accuracy of at least
   `0.85`. If this is not demonstrated, all known-positive cases route to LLM
   adjudication.
5. If no margin satisfies the requirements, the predictor owns no uncertain
   cases in that fold.

Qwen assessments use only frozen, label-free case evidence and a fixed prompt,
model revision, and seed. Cache one assessment per case so fold-specific labels
never enter the LLM prompt.

The LLM decision branch is enabled only if the complete selective hybrid beats
the predictor-only system by at least `0.01` mean F1 in at least 75% of paired
outer repeats while preserving the sensitivity floor. Otherwise Qwen remains
explanation-only.

## Retrieval and reasoning policy

- Use deterministic retrieval decisions rather than unconstrained LLM tool
  selection.
- Previous notes are required when known-positive context must be resolved.
- Retrieve radiology, PSA trend, laboratory results, or family history only
  when a declared evidence rule requires the section.
- Deduplicate tools and retain the existing call budget.
- Generate confidence from predictor margin, pathway certainty, missingness,
  contradictions, model agreement, and out-of-distribution evidence.
- Generate variable weights and decisive factors from the evidence ledger.
- Usually mark only one to three factors `decisive`.
- Ask the LLM to express the frozen decision using two to four supplied factors;
  it may not change the decision or invent evidence.

## Validation contract

Use repeated nested stratified cross-validation:

- Outer loop: 5 folds by 20 repeats.
- Inner loop: 4 folds.
- Random seed: `20260721`.
- Fit imputation, encoding, scaling, feature selection, calibration, threshold,
  and confidence margin inside the corresponding training folds.
- Apply visible duplicate checks before split creation. Continue to state that
  true patient and centre grouping cannot be proven without organizer IDs.

Report positive-class F1, sensitivity, specificity, precision, balanced
accuracy, confusion matrix, ROC-AUC, PR-AUC, Brier score, calibration,
pathway-specific results, routing coverage, LLM ownership, and fallback rate.

### Decision promotion gate

- Mean outer F1 at least `0.816`.
- At least 75% of repeats beat the current `0.806` rule.
- F1 standard deviation no greater than `0.03`.
- Mean sensitivity at least `0.90`.
- Mean specificity at least `0.40`.
- No temporal, patient-level, preprocessing, textual, or target leakage.

### Frozen official-evaluator gate

- Ranking score at least `0.6964`.
- Mean case score above `0.5669`.
- Tool precision at least `0.98`.
- Section grounding exactly `1.0`.
- Rationale score at least `0.7123`.
- Valid outputs for all 195 released cases.
- Zero silent fallbacks.

The official replay remains an in-sample evaluator-facing diagnostic. It does
not replace external validation.

## Two-person work split

### smoovie — Blocks 1–2

Primary folders:

- `features/`, `pathway/`, `decision/`, and ML-validation modules.
- Public decision contracts and the inference-only service facade.
- Predictor artifacts and model reports; never agent prompts or final form fill.

Detailed deliverables:

- Reproduce and freeze the current decision metrics and pathway error table.
- Own the data dictionary, decision-time field audit, and predictor leakage
  tests.
- Implement `DecisionFeaturesV1`, provenance, quality flags, and preliminary
  structured pathway assessment.
- Implement F0–F3 feature ablations through one common dataset builder.
- Implement repeated nested validation and paired repeat-level comparisons.
- Compare logistic regression, conservative gradient boosting, and CatBoost
  without changing the handoff contract.
- Implement calibration selection, sensitivity-constrained threshold selection,
  and predictor ownership-margin selection inside inner folds.
- Implement `PredictorArtifactManifestV1`, artifact loading checks, and
  `Task1DecisionService`.
- Produce pathway-specific metrics, routing coverage, calibration plots/data,
  failure analysis, and a frozen candidate recommendation.
- Supply a deterministic fake artifact for integration tests before final model
  selection.

smoovie must not modify:

- Qwen prompts, retrieval decisions, decision arbitration, evaluator-facing
  variable weights, final reasoning, serializer behavior, or Docker entrypoint,
  except through a reviewed shared-contract pull request.

### xuanhung_07 — Blocks 3–5

Primary folders:

- `agent/`, `llm/`, `evidence/`, `runtime/`, Task 1 retrieval tooling, official
  evaluator adapter, and packaging/integration configuration.
- Consumer-side contract tests and fake decision service.

Detailed deliverables:

- Freeze and validate `LlmDecisionAssessmentV1` and
  `DecisionArbitrationResultV1`.
- Build a fake `Task1DecisionService` immediately so Blocks 3–5 do not wait for
  model training.
- Implement deterministic uncertainty-driven retrieval against the five
  enabled Task 1 sections.
- Implement the structured Qwen adjudication prompt, parser, evidence-
  sufficiency rules, bounded repair, caching, and typed rejection reasons.
- Implement the arbitration truth table, explicit fallback trace, and immutable
  final decision.
- Build deterministic confidence, variable-weight, decisive-factor, and reveal
  planning from actual evidence.
- Constrain Qwen to grounded free-text synthesis after the decision is frozen.
- Run official evaluator replay, 195-case reliability, rationale analysis,
  selective-hybrid versus predictor-only comparison, and branch ablations.
- Own the integration runner, offline container, model provenance, and T4/A10G
  acceptance.

xuanhung_07 must not modify:

- Predictor training data, feature order, preprocessing, calibration,
  thresholds, model artifacts, or ownership-margin logic except through a
  reviewed shared-contract pull request.

### Shared responsibilities

- Merge the contract-only pull request before feature implementation diverges.
- Review every change to shared contracts.
- Review leakage and pathway assumptions together.
- Integrate only after unit-level exit criteria pass.
- Apply promotion rules without discretionary metric shopping.
- Freeze the selected candidate, reports, model, source, container, and hashes
  together.

## GitHub collaboration workflow

Use a protected `main` branch. Do not develop directly on `main` and do not
share one long-lived working branch.

Branches:

- `task1/contracts-v1`: short-lived shared branch for public schemas, example
  payloads, typed exceptions, and contract tests. Both people approve its pull
  request.
- `task1/smoovie-decision-engine`: Blocks 1–2 implementation.
- `task1/xuan-agent-integration`: Blocks 3–5 implementation against the fake
  service.
- `task1/selective-hybrid-integration`: temporary integration branch created
  only after both work branches pass their own gates.

Pull-request rules:

1. Each pull request names the block, contract version, tests run, artifacts or
   reports changed, leakage impact, and rollback behavior.
2. Changes to public contract models, enum values, artifact manifest, or
   decision-owner semantics require approval from both people.
3. Model-only changes must not modify agent behavior; agent-only changes must
   pass consumer contract tests without rebuilding the predictor.
4. Generated model binaries do not enter ordinary commits until a candidate is
   promoted and the repository's artifact-storage policy is agreed.
5. Rebase or merge `main` frequently; avoid copying files manually between
   branches.
6. Tag the exact frozen candidate and record source, model, prompt, evaluator,
   dependency, and result hashes together.

Recommended pull-request sequence:

1. PR-1: contract models, examples, fake decision service, and contract tests.
2. PR-2A: Block 1 features/pathway with no trained model dependency.
3. PR-2B: Block 3 structured assessment and retrieval against the fake service.
4. PR-3A: Block 2 validation/model candidates and frozen predictor service.
5. PR-3B: Blocks 4–5 arbiter, reasoning plan, and system gates.
6. PR-4: integration branch with real predictor artifact and complete paired
   evaluation.
7. PR-5: frozen submission candidate only after all promotion gates pass.

## ASAP critical path

`ASAP` means shorten dependency waiting, not skip validation.

### Start immediately, together

- Freeze `DecisionHandoffV1`, `PredictorAssessmentV1`, routing enums, exception
  behavior, and example JSON.
- Add producer and consumer contract tests.
- Reproduce the current control metrics and save hashes.
- Agree that pathology and reference outputs are forbidden.

### Then work in parallel

smoovie:

- Finish Block 1 and the validation harness first.
- Deliver a deterministic fake predictor service using the real handoff schema.
- Run the candidate ladder and freeze the best eligible predictor last.

xuanhung_07:

- Build Block 3 against the fake service.
- Build the arbiter and reasoning gates before connecting the real Qwen model.
- Prepare evaluator and reliability harnesses while model experiments run.

### Integrate at the earliest safe point

- Replace the fake decision service with smoovie's real frozen inference facade;
  no consumer code should change.
- Run a five-case pathway smoke set, then all 195 cases, then paired nested
  comparison for labeled cases.
- If the predictor-only system passes but the selective LLM does not, ship the
  predictor with Qwen explanation-only rather than delaying for an unproven LLM
  decision branch.

### Do not put these on the critical path

- MRI embeddings, new pretrained models, guideline RAG, Gemma comparison,
  pseudo-labels, user-interface work, or a separate service architecture.

## Milestones and exit criteria

### M0 — Contract and baseline freeze (shared)

Deliverables: reproduced current metrics, frozen evaluator commit, error-by-
pathway audit, and source/result hashes.

Exit: Qwen and control results reproduce within deterministic expectations.

### M1 — Evidence and feature contract (smoovie leads; shared approval)

Deliverables: approved field inventory, forbidden-field tests,
`DecisionFeaturesV1`, and temporal/leakage limitations.

Exit: both owners approve every candidate field and its decision-time status.

### M2 — Predictor-only candidates (smoovie)

Deliverables: nested-validation harness, feature ablations, predictor models,
calibration, threshold, and confidence gate.

Exit: a predictor-only candidate passes the promotion gate or is formally
rejected while the current rule remains the control.

### M3 — Structured LLM adjudication (xuanhung_07)

Deliverables: frozen assessment schema, prompt, deterministic retrieval policy,
cached label-free assessments, and failure tests.

Exit: no reference output reaches the prompt and every assessment is schema-
valid or explicitly rejected.

### M4 — Selective arbitration (xuanhung_07)

Deliverables: predictor/LLM arbiter, observable fallback, decision ownership
trace, and final reasoning plan.

Exit: the selective hybrid passes paired nested comparison or the LLM decision
branch is disabled.

### M5 — System evaluation (xuanhung_07 leads; shared review)

Deliverables: complete nested metrics, pathway confusion matrices, official
evaluator replay, 195-case reliability, and ablation report.

Exit: all decision and evaluator gates are applied and one candidate is selected
without using a challenge submission as an iterative tuning loop.

### M6 — Candidate freeze and submission qualification (shared)

Deliverables: frozen model and prompt versions, source/report hashes, offline
container, and T4/A10G acceptance evidence.

Exit: the exact candidate passes schema, latency, memory, offline, grounding,
and fallback checks and the packaging contradiction is resolved.

## Required tests

- Biopsy-naive PI-RADS-low and PI-RADS-high cases.
- Prior-negative persistent-suspicion and low-suspicion cases.
- Known-positive confirmatory/surveillance biopsy and established-treatment
  contexts.
- Unclear or contradictory biopsy history.
- Missing PI-RADS, inconsistent PSA density, extreme numeric values, unknown
  categories, and out-of-distribution cases.
- Predictor ownership, LLM routing, agreement, disagreement, invalid LLM output,
  evidence-insufficient output, and explicit predictor fallback.
- Grounded and ungrounded weights, duplicate tools, unnecessary tools, and
  reveal precision.
- Repeated seeded inference and trace reproducibility.
- Assertions that forbidden pathology, treatment, reference, ID, and future
  fields never enter features or prompts.
- Complete 195-case execution, Grand Challenge adapter, and offline container.

## Submission-slot policy

Pre-register the five validation slots as:

1. Current deterministic control.
2. Best internally promoted predictor-only system.
3. Selective hybrid only if it beats predictor-only under the paired gate.
4. Evaluator-reasoning ablation only if it materially improves mean case score.
5. Reserved contingency; do not spend it without a new frozen hypothesis.

Use the single test submission only for the final frozen candidate.

## Constraints and open issues

- The official evaluator was re-verified on 2026-08-22. Main still points to
  `55c7ca21487e5fd32042e5093bf5b019fc9e6c6c`; re-check before spending a
  validation or test submission.
- The release has no stable patient or centre identifier and no authoritative
  per-document decision timestamp.
- The baseline-style separate Model archive remains provisional until the
  organizers resolve whether weights must be embedded inside Docker.
- EAU, NCCN, the baseline guideline database, and derived guideline assets
  remain excluded without written permission covering software and submission
  use.
- Qwen remains the first comparison model; Gemma and MRI are deferred until the
  architecture earns promotion.

## Final recommendation

Begin with M0 and M1 together, then let smoovie and xuanhung_07 work in parallel
behind the frozen public contract. The first competitive objective is a
predictor-only pathway-aware system. The LLM earns decision ownership only as a
validated adjudicator for uncertain and management-context cases. If it does
not improve repeated out-of-fold performance, retain it solely for grounded
explanation.
