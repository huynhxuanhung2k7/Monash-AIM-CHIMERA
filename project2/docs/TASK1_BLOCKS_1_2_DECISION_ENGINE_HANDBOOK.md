# CHIMERA Task 1 — Blocks 1–2 Decision Engine Handbook

Status: **Standalone onboarding and execution specification**
Owner: **smoovie**
Reviewer and downstream consumer: **xuanhung_07**
Last verified: **2026-08-22**
Repository: `https://github.com/huynhxuanhung2k7/Monash-AIM-CHIMERA.git`
Repository project root after cloning: `Monash-AIM-CHIMERA/project2`

## Purpose and completion outcome

This document assumes the reader has never seen CHIMERA, this repository, the
data, or the current architecture. It contains everything required to take
ownership of:

1. **Block 1:** validated decision-time data, deterministic features, quality
   assessment, and preliminary clinical-pathway classification.
2. **Block 2:** predictor training, nested validation, calibration, threshold
   selection, case-ownership gating, artifact freezing, and the public handoff
   service consumed by Blocks 3–5.

The final deliverable is not a notebook or a model file by itself. It is a
tested, versioned, inference-only Python service:

```python
Task1DecisionService.assess(
    normalized_case=task1_case,
) -> DecisionHandoffV1
```

Blocks 3–5 must be able to replace their fake service with this real service
without changing consumer code.

## Before any work: shared-repository gate

The new `project2/` workspace is published without training data, model weights,
restricted references, secrets, or the historical implementation. Before
creating a feature branch, `smoovie` must clone the shared repository, run the
locked setup below, and confirm that pytest, Ruff, and mypy pass.

Both owners must work from Git commits and reviewed branches. Do not transfer
untracked source or artifacts through chat or AirDrop. Official patient data is
obtained separately and remains outside Git.

## Task 1 from first principles

### The question

For each patient, Task 1 asks:

> Should this patient be biopsied at the current decision point?

The system must output exactly one bare JSON string:

```json
"yes"
```

or:

```json
"no"
```

This is a management decision, not simply a prediction that cancer exists.

### Three problems that must remain separate

1. **Clinically significant prostate cancer (csPCa) risk:** estimated
   probability that important cancer is present.
2. **Biopsy recommendation:** whether a biopsy is indicated now given the
   patient's current care pathway.
3. **Explanation:** the decision-time factors supporting or opposing the
   recommendation.

A patient can have high cancer risk or already confirmed cancer without needing
another immediate biopsy. Conversely, a known-positive patient undergoing
active surveillance may require a scheduled confirmatory biopsy. The model must
learn the Task 1 label, not substitute generic cancer-risk prediction.

### Preliminary pathway categories

- `biopsy_naive`: no prior biopsy is recorded.
- `prior_negative`: a prior biopsy was negative; persistent suspicion may or
  may not justify another biopsy.
- `known_positive`: a positive biopsy or established cancer is recorded; the
  later agent must distinguish surveillance/confirmatory biopsy from established
  treatment context.
- `unclear`: biopsy status is missing, invalid, or contradictory.

Block 1 creates only a **preliminary structured pathway** from always-visible
structured evidence. Block 3 may refine management state after retrieving
previous notes. Block 1 must not read masked narratives to improve training.

### Core variables

- Prostate-Specific Antigen (PSA): prostate-specific but not cancer-specific.
- PSA density: PSA divided by prostate volume. It is meaningful only when PSA
  and volume are reliable and measured at the relevant decision time.
- Prostate Imaging Reporting and Data System (PI-RADS): MRI suspicion score
  from 1 to 5; it is not pathology.
- Digital Rectal Examination (DRE): structured physical-exam category; a normal
  result does not exclude cancer.
- `bx`: structured prior-biopsy history: none, negative, positive, or unknown.
- `cspca`: supplied model-generated csPCa likelihood. It is not confirmed
  disease, and its incremental value must be tested by ablation.
- PSA history: previous value, supplied velocity, and—only in later retrieved
  evidence—a dated trend. Block 1 uses only decision-time structured values.

## Official contract and scoring

The live official evaluator was rechecked on 2026-08-22. The latest main commit
is `55c7ca21487e5fd32042e5093bf5b019fc9e6c6c`. The [official evaluator
README](https://github.com/DIAGNijmegen/CHIMERA-agent/tree/main/evaluation)
specifies:

- Task 1 output is binary `yes`/`no`.
- No probability is part of the Grand Challenge output contract.
- An incorrect decision receives case score zero before reasoning is judged.
- Positive-class F1 is the decision metric.
- Task 1 ranking is `(positive-class F1 + mean case score) / 2`.
- The final system runs offline through the Grand Challenge interface.

Blocks 1–2 optimize decision quality, but they must also return enough reliable
metadata for Blocks 3–5 to construct grounded reasoning.

There are two different interfaces and they must not be confused:

1. **Private internal handoff:** Blocks 1–2 may pass calibrated probability,
   threshold, and margin to Blocks 3–5 so routing and confidence are
   deterministic and testable.
2. **Official challenge output:** Block 5 serializes only the binary decision
   and the required structured-reasoning object. It must remove every private
   predictor diagnostic, including probability and threshold.

For avoidance of doubt, the terminal files are:

```text
/output/prostate-biopsy-decision.json
/output/prostate-biopsy-decision-reasoning.json
```

`prostate-biopsy-decision.json` contains one JSON string:

```json
"yes"
```

`prostate-biopsy-decision-reasoning.json` contains a structured-reasoning
object with exactly these top-level keys:

```json
{
  "confidence": "clear",
  "variable_weights": {
    "age": "not_used",
    "fh": "not_used",
    "cspca": "not_used",
    "pirads": "important",
    "vol": "not_used",
    "psa": "noted",
    "comorbidity": "not_used",
    "psad": "important",
    "dre": "not_used",
    "bx": "not_used"
  },
  "free_text": "A concise grounded explanation consistent with the frozen decision.",
  "reveal_sequence": ["radiology_report"]
}
```

This is a shape example, not a recommended answer for any patient. Blocks 1–2
do not write either file; they only supply the private handoff consumed by the
downstream owner.

## Current baseline and why it is being rebuilt

The current hybrid freezes every binary decision to `PI-RADS >= 4`. Qwen
retrieves evidence and writes reasoning but cannot correct the decision.

Released-label diagnostic result:

| Metric | Current value |
|---|---:|
| Labeled cases | 91 |
| Yes / no labels | 56 / 35 |
| F1 for `yes` | 0.8060 |
| Sensitivity | 0.9643 |
| Specificity | 0.3143 |
| True positive / false positive | 54 / 24 |
| True negative / false negative | 11 / 2 |

Twenty-four of the 26 errors occur in the known-positive pathway: 22 false
positives and 2 false negatives. This is an in-sample diagnostic, not external
validation. It motivates a pathway-aware predictor but does not prove which
model will generalize.

## Local project layout

Clone and enter the Python project:

```bash
git clone https://github.com/huynhxuanhung2k7/Monash-AIM-CHIMERA.git
cd Monash-AIM-CHIMERA/project2
uv sync --locked --extra tabular
uv run pytest
```

Important paths relative to `project2/`:

| Path | Purpose | Blocks 1–2 responsibility |
|---|---|---|
| `pyproject.toml` | Python version and CPU dependencies | Preserve; add reviewed dependencies only |
| `src/chimera_task1/contracts/` | Shared input/output and new handoff models | Shared ownership; both reviewers required |
| `src/chimera_task1/data/` | Discovery, strict loading, normalization | Preserve and extend conservatively |
| `src/chimera_task1/features/` | Feature objects and transformations | `smoovie` owns |
| `src/chimera_task1/pathway/` | Preliminary pathway and contradictions | `smoovie` owns structured stage |
| `src/chimera_task1/decision/` | Predictors, calibration, threshold, artifacts, public facade | `smoovie` owns |
| `src/chimera_task1/evaluation/` | Predictor validation and metrics | `smoovie` owns model-specific files |
| `experiments/baselines/` | Baseline, validation, training entrypoints | `smoovie` owns relevant scripts |
| `tests/contract/` | Cross-branch schema compatibility | Shared approval |
| `tests/unit/` | Feature/model/unit validation | Component owner |
| `tests/integration/` | Real-service consumer compatibility | `xuanhung_07` leads; both review |
| `artifacts/` | Frozen eligible model artifacts | Generated only after promotion |
| `reports/validation/` | Development reports | Generated; selectively version summaries |

Do not modify Task 2 folders. Do not modify `agent/`, `llm/`, `evidence/`,
`runtime/`, or `submission/` except through a shared contract change approved by
`xuanhung_07`.

## Technology stack

### Required and already declared

| Technology | Version/role |
|---|---|
| Python | `>=3.12` |
| Pydantic | `>=2.13.4`; frozen strict transfer objects |
| scikit-learn | `>=1.6.1`; preprocessing, logistic regression, gradient boosting, calibration |
| joblib | `>=1.4.2`; frozen sklearn artifact serialization |
| pytest | `>=8.4.2`; contract, unit, and integration tests |
| Git/GitHub | protected `main`, feature branches, reviewed pull requests |

### Optional experiment dependency

CatBoost is not currently declared. It may be added only in a separate reviewed
experiment pull request after:

- License and version are recorded.
- Linux/amd64 CPU inference and Docker packaging are tested.
- Artifact size and startup time are measured.
- The same public handoff API is preserved.
- The candidate demonstrates stable nested-validation value.

Do not add pandas, a database, FastAPI, REST, a notebook-only pipeline, a cloud
service, or a feature store unless a measured requirement emerges. The intended
runtime boundary is an in-process typed Python service.

## Environment setup

From `chimera/project`:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m pytest -q
```

Record:

```bash
.venv/bin/python --version
.venv/bin/python -m pip freeze
git rev-parse HEAD
```

Do not commit `.venv` or `pip freeze` output containing local paths. Save the
environment report under an agreed non-sensitive report path if it is meant to
be versioned.

## Data acquisition and expected layout

The authorized CHIMERA-Agent Version 2 Task 1 data is separate from Git. It has
195 cases: 91 labeled and 104 unlabeled.

Expected repository-relative location on the original machine:

```text
CHIMERA/train_release/task1/
  <case-id>/
    structured-prompt.json
    prostate-biopsy-decision-clinical-data.json
    prostate-modality-level-neural-representations.json
    prostate-biopsy-decision.json              # labeled cases only
    prostate-biopsy-decision-reasoning.json    # labeled cases only
```

Each teammate may store it elsewhere and pass an absolute `--dataset-dir`.
Never commit this directory. Never interpret a missing decision file as `no`.
The 104 unlabeled cases may test runtime robustness but cannot train, calibrate,
select thresholds, or estimate decision performance.

Record a dataset digest or a manifest of per-file digests so both teammates can
prove they used the same release without sharing patient data through Git.

## Baseline reproduction gate

Set a local shell variable or substitute the absolute path directly:

```bash
TASK1_DATASET=/absolute/path/to/train_release/task1
```

Run the audit:

```bash
.venv/bin/python experiments/runner/run_task1_audit.py \
  --dataset-dir "$TASK1_DATASET" \
  --report-path reports/data_audit/task1_v2.json \
  --overwrite
```

Run deterministic controls:

```bash
.venv/bin/python experiments/baselines/run_baselines.py \
  --dataset-dir "$TASK1_DATASET" \
  --report-path reports/validation/deterministic_v2.json \
  --overwrite
```

Run the existing logistic control:

```bash
.venv/bin/python experiments/baselines/run_ml_baseline.py \
  --dataset-dir "$TASK1_DATASET" \
  --report-path reports/validation/logistic_v0_oof.json \
  --overwrite
```

Run the current complete deterministic system:

```bash
.venv/bin/python experiments/runner/run_task1_dataset.py \
  --dataset-dir "$TASK1_DATASET" \
  --output-dir reports/onboarding-control \
  --engine control \
  --policy pirads_ge_4 \
  --overwrite
```

The two teammates compare case count, label count, confusion matrix, output
schema, report hashes, Python version, and source commit. Do not repeatedly run
until random numbers happen to agree; diagnose any difference.

## Blocks 1–2 architecture

```text
LoadedTask1Case
  -> existing strict normalization
  -> DecisionFeaturesV1
  -> StructuredPathwayAssessmentV1
  -> InputQualityAssessmentV1
  -> frozen preprocessing pipeline
  -> candidate classifier
  -> private raw probability_yes
  -> frozen calibrator or explicit calibration=none
  -> sensitivity-constrained threshold
  -> binary decision and private probability margins
  -> ownership policy: margin + pathway + quality + OOD
  -> PredictorAssessmentV1
  -> DecisionHandoffV1
```

No label, reference reasoning, case identifier, narrative, fold number, or
future information may enter the feature matrix.

## Folder and dependency contract

Dependency direction:

```text
contracts <- data <- features/pathway <- decision/service
                                            |
                                            v
                                  DecisionHandoffV1
                                            |
                                            v
                               agent/runtime consumers
```

Rules:

1. New cross-branch models live in
   `src/chimera_task1/contracts/decision_handoff.py`.
2. The public inference facade lives in
   `src/chimera_task1/decision/service.py`.
3. Training-only code lives in `evaluation/` or `experiments/`, not in the
   service facade.
4. `decision/` must not import `agent/`, `llm/`, `evidence/`, `runtime/`, final
   form fill, or evaluator-facing reasoning.
5. Blocks 3–5 may import the facade and contracts. They must not import an
   sklearn pipeline, feature-column constants, calibration internals, training
   tables, labels, or fold assignments.
6. All transfer models use `extra="forbid"`, `frozen=True`, finite numeric
   validation, closed enums, and schema version `1.0`.
7. Every transfer model must survive JSON serialization and deserialization.
8. Contract changes require both owners' approval and a version change when
   backward compatibility is broken.

## Exact public API

Conceptual signature:

```python
class Task1DecisionService(Protocol):
    def assess(
        self,
        *,
        normalized_case: Task1NormalizedFeatures,
    ) -> DecisionHandoffV1: ...
```

The service owns both Block 1 feature construction and Block 2 prediction.
The consumer supplies the existing normalized case and receives one immutable
handoff. The consumer must not reconstruct features.

### `DecisionFeaturesV1`

| Field | Type/range | Model use |
|---|---|---|
| `schema_version` | literal `"1.0"` | Compatibility only |
| `case_id` | non-empty string | Metadata only; prohibited from feature matrix |
| `age` | float `0..120` or null | Candidate feature |
| `psa` | non-negative float or null | Candidate feature |
| `previous_psa` | non-negative float or null | F3 candidate feature |
| `supplied_psa_velocity` | finite float or null | F3 candidate; quality flag required |
| `pirads` | integer `1..5` or null | Core candidate feature |
| `reported_psad` | non-negative float or null | Candidate feature |
| `prostate_volume` | positive float or null | Candidate feature |
| `cspca_score` | float `0..1` or null | F2 candidate only; ablate separately |
| `dre` | closed DRE enum | Candidate categorical feature |
| `biopsy_history` | `none`, `negative`, `positive`, `unknown` | Core pathway feature |
| `recalculated_psad` | non-negative float or null | Derived when PSA and volume valid |
| `psad_absolute_error` | non-negative float or null | Consistency feature |
| `psa_delta` | finite float or null | Derived F3 candidate |
| `psa_delta_direction` | `rising`, `stable`, `falling`, `unknown` | Derived F3 candidate |
| `feature_provenance` | tuple of typed entries | Audit only, not direct model input |

Raw medical history and all masked clinical narratives are excluded from V1.
Unknown must remain distinct from negative or normal.

### `StructuredPathwayAssessmentV1`

Required fields:

- `category`: `biopsy_naive`, `prior_negative`, `known_positive`, or `unclear`.
- `confidence`: `clear` or `uncertain`.
- `source`: literal `structured_prompt`.
- `evidence`: compact non-narrative structured statements.
- `contradictions`: typed contradiction codes.

This object is preliminary. It cannot claim active surveillance, confirmatory
biopsy, or established-treatment context without Block 3 retrieving evidence.

### `InputQualityAssessmentV1`

Required fields:

- `critical_missing`: tuple of required missing field names.
- `noncritical_missing`: tuple of other missing field names.
- `invalid_fields`: tuple of rejected field/error codes.
- `consistency_flags`: tuple including reported/recalculated conflicts.
- `contradiction_flags`: tuple of structured pathway/data conflicts.
- `ood_flags`: tuple of out-of-distribution codes.
- `input_complete`: boolean derived deterministically from the policy version.

### `PredictorAssessmentV1`

This object is private inter-component telemetry. It is not either of the two
Grand Challenge output files and must never be serialized into them.

| Field | Type | Invariant |
|---|---|---|
| `assessment_id` | deterministic string/hash | Tied to case input and artifact versions, never label |
| `decision` | `yes` or `no` | Equals probability compared with threshold |
| `raw_probability_yes` | float `[0,1]` | Classifier output before calibration |
| `probability_yes` | float `[0,1]` | Calibrated output or raw when method is `none` |
| `threshold` | float `[0,1]` | Frozen selected threshold |
| `signed_margin` | float `[-1,1]` | `probability_yes - threshold` |
| `absolute_margin` | float `[0,1]` | Absolute signed margin |
| `confidence` | `clear`, `borderline`, `uncertain` | Deterministic predictor confidence |
| `ownership_eligible` | boolean | Must agree with routing decision |
| `model_name`, `model_version` | strings | Frozen artifact identity |
| `feature_contract_version` | string | Must equal feature manifest |
| `calibration_method`, `calibration_version` | strings | Explicit `none` allowed |
| `threshold_policy_version` | string | Frozen sensitivity-constrained policy |
| `ownership_policy_version` | string | Frozen routing policy |
| `training_data_digest` | SHA-256 string | Exact labeled release manifest |
| `model_signals` | small typed tuple | Diagnostic direction/magnitude, never evaluator weights |
| `warnings` | closed warning enum tuple | Non-fatal warnings |

The probability fields exist solely to validate the decision boundary and
support routing. The downstream serializer has an explicit deny-list for
`raw_probability_yes`, `probability_yes`, `threshold`, `signed_margin`, and
`absolute_margin`.

### `DecisionHandoffV1`

Required return object:

| Field | Type |
|---|---|
| `schema_version` | literal `"1.0"` |
| `handoff_id` | deterministic hash |
| `case_id` | runtime correlation metadata |
| `features` | `DecisionFeaturesV1` |
| `structured_pathway` | `StructuredPathwayAssessmentV1` |
| `input_quality` | `InputQualityAssessmentV1` |
| `predictor` | `PredictorAssessmentV1` |
| `routing_recommendation` | `predictor_owned` or `llm_required` |
| `routing_reasons` | closed enum tuple |
| `artifact_manifest_digest` | SHA-256 string |

Initial routing reasons:

- `high_confidence_predictor`
- `low_probability_margin`
- `pathway_unclear`
- `known_positive_not_validated`
- `critical_missingness`
- `structured_contradiction`
- `out_of_distribution`
- `artifact_policy_mismatch`

An artifact-policy mismatch is a hard production failure, even though it has a
typed diagnostic code for tests.

### Error behavior

- Ordinary missingness, pathway uncertainty, or OOD returns a valid handoff with
  `llm_required`; it is not an exception.
- Invalid source schema or impossible values raise `DecisionInputError`.
- Missing, corrupt, or incompatible artifacts raise `DecisionArtifactError`.
- Unexpected inference failures raise `DecisionInferenceError`.
- No error silently returns `yes`, `no`, or unrestricted LLM ownership.
- No handoff contains labels, reference reasoning, fold IDs, training rows, raw
  narratives, or hidden chain-of-thought.

## Block 1 execution plan

### Stage 1.1 — Data dictionary and leakage register

For every raw and derived field, document:

- Raw JSON name and normalized name.
- Medical meaning, type, unit, expected range, and missing tokens.
- Whether it was available before the biopsy decision.
- Whether it overlaps another field.
- Planned feature set: F0, F1, F2, F3, audit-only, or forbidden.
- Potential temporal, textual, patient-level, preprocessing, or target leakage.
- Tests required before use.

Explicitly forbid:

- Reference decision and reasoning.
- Reference confidence, variable weights, and reveal sequence.
- Pathology or treatment information obtained after the current decision.
- Raw previous notes, reports, family history narratives, and laboratory lists.
- Case identifiers, archive identifiers, and institution shortcuts.
- Neural representations in the first rebuild.
- Pseudo-labels for the 104 unlabeled cases.

Exit: both owners approve every field and its decision-time status.

### Stage 1.2 — Deterministic feature builder

Build features through pure deterministic functions. Given the same normalized
case and feature-contract version, output bytes must be stable after canonical
JSON serialization.

Requirements:

- Preserve reported and recalculated PSA density as separate fields.
- Never divide by missing, zero, negative, or invalid volume.
- Preserve unknown categories instead of coercing them to negative.
- Store missingness and invalidity explicitly.
- Make PSA longitudinal calculations deterministic; do not ask the LLM to
  calculate them.
- Ensure `case_id` is dropped before the model matrix is assembled.
- Keep feature names and order in a versioned manifest.

### Stage 1.3 — Preliminary pathway classifier

Structured rules:

- `bx=none` -> `biopsy_naive`, unless a structured contradiction exists.
- `bx=negative` -> `prior_negative`.
- `bx=positive` -> `known_positive`.
- `bx=unknown`, invalid, or contradictory -> `unclear`.

Do not parse masked notes in Blocks 1–2. Block 3 owns pathway refinement.

### Stage 1.4 — Quality and OOD policy

Define critical versus noncritical missingness before viewing performance.
Build OOD flags from training-fold ranges or robust distributions inside each
training fold. Do not compute global quantiles before splitting.

An OOD flag does not determine `yes` or `no`; it prevents predictor ownership
and routes the case to the downstream adjudicator.

## Block 2 execution plan

### Stage 2.1 — Freeze simple comparators

Every experiment report must include:

1. Always-yes.
2. `PI-RADS >= 4`.
3. Existing five-feature logistic-v0.
4. Current deterministic complete system when evaluator-facing comparison is
   relevant.

### Stage 2.2 — Feature ablation ladder

- F0: preliminary pathway plus PI-RADS.
- F1: F0 plus PSA, reported/recalculated PSA density, volume, age, DRE,
  missingness, and consistency flags.
- F2: F1 plus supplied csPCa score.
- F3: F2 plus deterministic previous-PSA and velocity-quality features.

Add one major feature family at a time. Keep only stable incremental value.

### Stage 2.3 — Model ladder

Evaluate through one validation interface:

1. Elastic-net logistic regression.
2. Conservative sklearn histogram gradient boosting.
3. CatBoost only after dependency approval.
4. A pathway-specialized model only after pooled candidates show stable,
   repeated known-positive weakness.

Avoid deep neural networks, raw MRI embeddings, large ensembles, and arbitrary
hyperparameter searches with only 91 labels.

### Stage 2.4 — Nested validation

Required design:

- Outer: 5 stratified folds by 20 repeats.
- Inner: 4 stratified folds.
- Base seed: `20260721`; derive and record child seeds deterministically.
- Fit preprocessing, feature selection, model, calibration, threshold, and
  ownership margin inside the relevant training fold.
- Keep all outer-test cases untouched until the complete inner selection is
  frozen.
- Continue to state that true patient/centre grouping is unverified because
  stable group identifiers are unavailable.

Report:

- Positive-class F1, sensitivity, specificity, precision, balanced accuracy.
- Confusion matrix.
- ROC-AUC, PR-AUC, Brier score, and calibration data.
- Pathway-specific results.
- Routing coverage and conditional owned-case accuracy.
- Repeat-level paired differences against controls.
- Model, feature, threshold, and calibration selections by fold.

### Stage 2.5 — Calibration and threshold

Compare sigmoid/Platt calibration and isotonic calibration only inside inner
training. With small calibration samples, prefer the simpler stable method or
explicit `none`.

Select threshold to maximize positive-class F1 subject to sensitivity
`>= 0.90`. Do not select a threshold on the complete 91 labels and then report
cross-validation as if it were independent.

### Stage 2.6 — Predictor ownership gate

Select ownership margins from `0.05`, `0.10`, `0.15`, `0.20`, and `0.25`
inside inner validation.

`ownership_eligible=true` requires:

- Compatible artifact and feature manifest.
- No critical invalidity.
- Preliminary pathway not `unclear`.
- No unresolved structured contradiction or OOD flag.
- Probability margin meeting the selected cutoff.
- At least `0.85` conditional accuracy and `0.30` coverage in inner OOF data.
- For known-positive cases, at least ten owned inner OOF cases and conditional
  accuracy `>= 0.85`; otherwise route every known-positive case.

If no margin passes, the predictor owns no uncertain cases. Do not relax the
gate merely to increase coverage.

### Stage 2.7 — Candidate selection

Decision promotion gate:

- Mean outer F1 `>= 0.816`.
- At least 75% of repeats beat current F1 `0.806`.
- F1 standard deviation `<= 0.03`.
- Mean sensitivity `>= 0.90`.
- Mean specificity `>= 0.40`.
- No discovered leakage.

Among eligible candidates, select the simplest model within `0.01` mean outer
F1 of the best eligible model.

### Stage 2.8 — Frozen artifact

Create `PredictorArtifactManifestV1` containing:

- Schema, feature-contract, model, calibration, threshold-policy, and
  ownership-policy versions.
- Training-data digest.
- Source commit.
- Dependency versions and platform.
- Random seeds.
- Ordered feature manifest.
- Serialized artifact filename, byte size, and SHA-256.
- Validation-report filename and SHA-256.
- Promotion decision and approving reviewers.

Load and verify every hash before processing the first runtime case.

## Planned files

New planned public files:

```text
src/chimera_task1/contracts/decision_handoff.py
src/chimera_task1/decision/service.py
tests/contract/test_task1_decision_handoff.py
tests/fixtures/task1/decision_handoff_v1.json
```

Likely Block 1–2 files to extend or add:

```text
src/chimera_task1/features/feature_contract.py
src/chimera_task1/features/derived.py
src/chimera_task1/features/longitudinal.py
src/chimera_task1/features/missingness_flags.py
src/chimera_task1/pathway/state.py
src/chimera_task1/pathway/classifier.py
src/chimera_task1/pathway/contradictions.py
src/chimera_task1/decision/calibration.py
src/chimera_task1/decision/threshold.py
src/chimera_task1/decision/confidence.py
src/chimera_task1/decision/model_artifact.py
src/chimera_task1/evaluation/nested_validation.py
src/chimera_task1/evaluation/splits.py
```

Names may be adjusted through the contract pull request, but the ownership and
dependency direction may not change silently.

## Required tests

### Contract tests

- Reject extra fields, unknown enum values, booleans as numbers, NaN, infinity,
  negative invalid clinical values, and mismatched case IDs.
- Reject inconsistent probability/threshold/decision.
- Reject incorrect signed or absolute margin.
- Reject `ownership_eligible=true` with `llm_required`.
- JSON round-trip every public model.
- Prove the fake and real service satisfy the same protocol.

### Feature tests

- Normal and every soft-missing token.
- PI-RADS 1–5 and invalid values.
- DRE and biopsy-history categories, aliases, unknowns, and invalid strings.
- PSA-density calculation with valid, zero, negative, and missing volume.
- Reported/recalculated inconsistency.
- PSA delta and direction.
- Feature order stability.
- Forbidden fields absent from the matrix.

### Pathway tests

- Biopsy-naive, prior-negative, known-positive, and unclear.
- Unknown versus none.
- Contradictory structured evidence.
- No claim of surveillance/treatment without retrieved notes.

### Validation tests

- Preprocessing fitted only on training folds.
- Threshold/calibration/margin selected only inside inner folds.
- Reproducible split seeds.
- Both labels exist in fitted training partitions.
- Metrics handle zero denominators.
- Unlabeled cases never enter supervised folds.

### Artifact/service tests

- Correct manifest loads.
- Missing, corrupt, wrong-version, and wrong-hash artifacts fail before
  inference.
- Runtime assessment is deterministic for a fixed artifact/input.
- All 195 valid normalized cases return a handoff or typed hard failure.
- Consumer fake-service integration tests also pass with the real service.

## GitHub workflow

Branches:

- `task1/contracts-v1`: shared contract-only pull request; both approve.
- `task1/smoovie-decision-engine`: Blocks 1–2 work.
- `task1/xuan-agent-integration`: downstream work against fake service.
- `task1/selective-hybrid-integration`: temporary integration branch after both
  workstreams pass their gates.

Recommended Blocks 1–2 pull requests:

1. Contract models, fixture, typed exceptions, and protocol.
2. Feature/quality/pathway layer with tests; no new model.
3. Nested-validation harness and frozen controls.
4. Candidate models and ablation reports.
5. Calibration, threshold, ownership gate, and artifact manifest.
6. Real service replacing fake service on integration branch.

Every pull request states files changed, contract version, tests, leakage
impact, generated artifacts, result interpretation, and rollback behavior.

## Handoff package to `xuanhung_07`

Provide all of the following together:

- Public contracts and JSON example.
- `Task1DecisionService` inference facade.
- Frozen model artifact and manifest.
- Unit, contract, and integration test results.
- Complete nested-validation and ablation report.
- Selected threshold, calibration, and ownership policies.
- Pathway-specific metrics and routing coverage.
- Known limitations, unresolved data issues, and typed failure behavior.
- Source, dataset, artifact, and report hashes.
- One fake-service fixture and at least five real handoff fixtures covering all
  pathway/routing cases without reference answers.

Do not hand off an interactive notebook, undocumented dataframe, mutable
pipeline, or model file without its manifest and service.

## Troubleshooting and decision rules

- If no model beats the control gate, retain `PI-RADS >= 4` as the decision
  control and document the failed hypotheses. Do not promote an in-sample win.
- If CatBoost improves mean F1 but is unstable, prefer the stable simpler model.
- If calibration is unstable, use explicit `none`; do not report an unvalidated
  probability as calibrated.
- If no ownership margin reaches required accuracy/coverage, route cases to
  Block 3 instead of weakening the gate.
- If known-positive ownership lacks at least ten validation cases, route all
  known-positive cases.
- If an artifact hash/version fails, stop. Do not use a previous artifact
  silently.
- If a feature's decision-time availability is uncertain, exclude it until the
  issue is resolved.

## Definition of done for Blocks 1–2

Blocks 1–2 are complete only when:

- A fresh clone reproduces CPU setup and controls.
- Every feature has a data-dictionary and leakage decision.
- `DecisionFeaturesV1`, pathway, quality, predictor, artifact, and handoff
  contracts are frozen and jointly approved.
- Nested validation, calibration, thresholding, and ownership selection are
  fold-safe.
- A candidate passes the promotion gate or a formal no-promotion conclusion is
  recorded.
- The artifact and report are hashed and reproducible.
- The real service passes the same consumer tests as the fake service.
- No training internals leak across the folder boundary.
- `xuanhung_07` can consume `DecisionHandoffV1` without modifying Blocks 3–5.

## Companion document

Blocks 3–5 are specified independently in
`docs/TASK1_BLOCKS_3_5_AGENT_SYSTEM_HANDBOOK.md`. That document repeats the
handoff contract intentionally so neither owner needs undocumented context.
