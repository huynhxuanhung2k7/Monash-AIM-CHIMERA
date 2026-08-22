# CHIMERA Task 1 — Blocks 3–5 Agent System Handbook

Status: **Standalone onboarding and execution specification**
Owner: **xuanhung_07**
Upstream producer and reviewer: **smoovie**
Last verified: **2026-08-22**
Repository: `https://github.com/huynhxuanhung2k7/Monash-AIM-CHIMERA.git`
Repository project root after cloning: `Monash-AIM-CHIMERA/project2`

## Purpose and completion outcome

This document assumes the reader has no prior project context. It contains the
complete plan for:

3. **Block 3:** routing-aware patient-evidence retrieval and structured Qwen
   adjudication.
4. **Block 4:** deterministic decision ownership, arbitration, and explicit
   fallback.
5. **Block 5:** confidence, variable weights, reveal sequence, grounded
   explanation, safety gates, official evaluation, runtime integration, offline
   packaging, and submission qualification.

The completed system consumes one immutable upstream `DecisionHandoffV1`,
optionally retrieves approved patient sections, optionally obtains a structured
LLM assessment, freezes one final decision owner, and writes exactly:

```text
prostate-biopsy-decision.json
prostate-biopsy-decision-reasoning.json
```

## Before any work: shared-repository gate

The new `project2/` workspace is published without training data, model weights,
restricted references, secrets, or historical source. Before creating a feature
branch, clone the shared repository, install the locked environment, and confirm
that pytest, Ruff, and mypy pass.

The repository must be the transfer mechanism for source and small synthetic
fixtures. Official patient data remains outside Git. Do not synchronize
untracked code by copying folders manually.

## Task 1 from first principles

### The task

For each patient, the system answers:

> Should this patient be biopsied at the current decision point?

The decision is a bare JSON `"yes"` or `"no"`. This is not equivalent to
predicting cancer risk.

Keep separate:

1. Clinically significant prostate cancer (csPCa) risk.
2. Current biopsy recommendation conditioned on prior care.
3. Grounded explanation of the recommendation.

A known-positive patient may already be receiving treatment and not need a new
biopsy, or may be on active surveillance and need a confirmatory biopsy. Block
3 exists mainly to resolve this management context when structured evidence is
insufficient.

### Pathway and management states

The upstream handoff provides a preliminary pathway:

- `biopsy_naive`
- `prior_negative`
- `known_positive`
- `unclear`

After selective retrieval, Qwen must classify a more specific management state:

- `initial_diagnosis`
- `persistent_suspicion_after_negative_biopsy`
- `confirmatory_or_surveillance_biopsy`
- `established_disease_without_current_biopsy_indication`
- `unclear`

Qwen must not infer pathology or surveillance from PI-RADS alone.

### Clinical evidence principles

- Prostate-Specific Antigen (PSA) can rise for benign reasons; one value is not
  a reliable trajectory.
- PSA density depends on valid PSA and prostate-volume measurements.
- Prostate Imaging Reporting and Data System (PI-RADS) is MRI suspicion, not
  pathology.
- Digital Rectal Examination (DRE) modifies context but a normal exam does not
  exclude cancer.
- The supplied `cspca` score is an uncalibrated model-generated likelihood, not
  confirmed disease.
- Prior biopsy result and current management pathway change the meaning of all
  other risk evidence.

## Official contract and scoring

The live official evaluator was rechecked on 2026-08-22. Main still points to
`55c7ca21487e5fd32042e5093bf5b019fc9e6c6c`. The [official evaluator
README](https://github.com/DIAGNijmegen/CHIMERA-agent/tree/main/evaluation)
specifies:

- Exact `yes`/`no` decision gate.
- No probability belongs in either official Task 1 output file.
- Incorrect decision -> case score zero.
- Positive-class F1 for the decision component.
- Task 1 ranking = `(positive-class F1 + mean case score) / 2`.
- Correct cases are then scored on confidence, variable weights,
  important/decisive factors, tool precision, section grounding, and rationale.
- Offline Grand Challenge execution.

Consequences:

- Block 4 must freeze the best validated decision before Block 5 writes prose.
- Extra retrievals reduce tool precision.
- A variable weighted above `not_used` must have an allowed revealed source
  unless it is officially always available.
- Good prose cannot compensate for a wrong decision.

## Current system and redesign target

Current released-label diagnostics for the fixed `PI-RADS >= 4` decision:

| Metric | Current value |
|---|---:|
| Labeled cases | 91 |
| F1 for `yes` | 0.8060 |
| Sensitivity | 0.9643 |
| Specificity | 0.3143 |
| TP / FP / TN / FN | 54 / 24 / 11 / 2 |

Twenty-four of 26 errors occur in known-positive cases. The current Qwen hybrid
also scores below the deterministic control on exact evaluator ranking despite
the same F1. The target is therefore not “more LLM.” It is:

```text
validated predictor ownership for eligible cases
            +
structured Qwen adjudication only for routed cases
            +
deterministic arbitration and grounded reasoning
```

Qwen earns decision ownership only through paired validation. Otherwise it
remains explanation-only and the predictor owns/falls back for every decision.

## Repository setup from zero

Clone and enter the new project:

```bash
git clone https://github.com/huynhxuanhung2k7/Monash-AIM-CHIMERA.git
cd Monash-AIM-CHIMERA/project2
uv sync --locked
uv run pytest
uv run ruff check .
uv run mypy
```

Task 1 data is stored separately from Git. Expected layout:

```text
../train_release/task1/
  <case-id>/
    structured-prompt.json
    prostate-biopsy-decision-clinical-data.json
    prostate-modality-level-neural-representations.json
    prostate-biopsy-decision.json              # 91 labeled cases only
    prostate-biopsy-decision-reasoning.json    # 91 labeled cases only
```

There are 195 cases: 91 labeled and 104 unlabeled. Inference must not load
reference decision/reasoning. Unlabeled cases are not negative labels.

Before agent work, reproduce:

```bash
TASK1_DATASET=/absolute/path/to/train_release/task1

.venv/bin/python experiments/runner/run_task1_audit.py \
  --dataset-dir "$TASK1_DATASET" \
  --report-path reports/data_audit/task1_v2.json \
  --overwrite

.venv/bin/python experiments/runner/run_task1_dataset.py \
  --dataset-dir "$TASK1_DATASET" \
  --output-dir reports/onboarding-control \
  --engine control \
  --policy pirads_ge_4 \
  --overwrite
```

Confirm the same commit, dataset digest, case count, control metrics, and output
schema on both machines.

## Technology stack

### Shared Python stack

| Technology | Version/role |
|---|---|
| Python | `>=3.12` |
| Pydantic | `>=2.13.4`; strict frozen schemas and form validation |
| pytest | `>=8.4.2`; contract, unit, integration, and failure tests |
| Model Context Protocol (MCP) | Local stdio patient-section retrieval |
| JSON | Official input/output and internal fixture serialization |
| Git/GitHub | Protected `main`, feature branches, pull-request review |

The project uses its own small `LlmClient` abstraction. Do not add LangChain,
a cloud agent framework, REST service, or database merely because the official
baseline uses a more general agent stack.

### Local development LLM

| Item | Value |
|---|---|
| Model | `qwen3:4b-instruct-2507-q4_K_M` through Ollama |
| Interface | OpenAI-compatible local HTTP at `127.0.0.1:11434/v1` |
| Network use | Localhost only during inference |
| Setup | `./task1 setup` from `project/` |

Run:

```bash
./task1 setup
./task1 predict CASE-ID
```

### Submission LLM/runtime

| Item | Frozen value |
|---|---|
| Model ID | `Qwen/Qwen3-4B-Instruct-2507` |
| Revision | `cdbee75f17c01a7cc42f958dc650907174af0554` |
| License | Apache-2.0 |
| Precision | FP16 |
| Runtime image | `vllm/vllm-openai:v0.25.0` |
| Image digest | `sha256:fc56161ee42a011aeee78b65d0a81b6683c7d04402fd40503d14d4d6c98f07cb` |
| Platform | `linux/amd64` |
| Model mount | Read-only `/opt/ml/model` provisionally following baseline pattern |
| Network | Disabled at inference |

Gemma, guideline retrieval-augmented generation (RAG), MRI embeddings, external
APIs, and new pretrained models are not on the critical path.

### Current default generation limits

- Temperature `0.2`.
- Top-p `0.8`.
- Maximum new tokens `768`.
- Model context length `8192`.
- Seed `20260812`.
- Maximum tool rounds `3`.
- Maximum total tools `3`.
- Maximum form attempts `5`.

These are frozen configuration candidates, not permission for the LLM to call
unnecessary tools. Any change requires an experiment and version update.

## Repository map and ownership

| Path | Purpose | Blocks 3–5 authority |
|---|---|---|
| `src/chimera_task1/contracts/` | Shared schemas and enums | Shared approval only |
| `src/chimera_task1/decision/service.py` | Upstream facade | Consume only; do not modify training behavior |
| `src/chimera_task1/agent/` | Retrieval orchestration, adjudication, form fill | Own |
| `src/chimera_task1/llm/` | Qwen config, providers, contracts | Own |
| `src/chimera_task1/tools/retrieval/` | MCP registry/client/server | Own protocol-compatible policy |
| `src/chimera_task1/evidence/` | Ledger, weights, grounding, checks | Own |
| `src/chimera_task1/runtime/` | Composition, arbitration, validation, serialization | Own |
| `src/chimera_task1/evaluation/agent_metrics.py` | Agent/system metrics | Own |
| `src/chimera_task1/evaluation/official_adapter.py` | Official evaluator packaging | Own |
| `experiments/runner/` | Dataset runs, official replay, candidate freeze | Own relevant scripts |
| `tests/contract/` | Shared compatibility | Both approve |
| `tests/unit/` | Component tests | Owner |
| `tests/integration/` | Fake/real service and complete runner | Lead |
| `submission/` | Offline container and model packaging | Own; shared final review |

Do not modify predictor features, model training, calibration, threshold,
ownership margin, or artifact contents except through a reviewed shared change.
Task 2 is out of scope.

## Dependency and folder boundary

```text
contracts <- decision public facade
                    |
                    v
            DecisionHandoffV1
                    |
                    v
agent + retrieval + llm -> LlmDecisionAssessmentV1
                    |
                    v
              runtime/arbitration
                    |
                    v
evidence/reasoning -> validation -> serializer -> official outputs
```

Rules:

1. `agent/`, `evidence/`, and `runtime/` may import public handoff contracts and
   `Task1DecisionService`.
2. They may not import sklearn models, feature-column indices, training tables,
   calibrators, thresholds, labels, fold assignments, or experiment code.
3. `decision/` may not import agent/LLM/reasoning modules.
4. `runtime/` is the composition root; no other folder wires all components.
5. Shared objects live once in `contracts/`, are frozen, versioned, strict, and
   JSON-round-trip tested.
6. A contract-breaking change requires a schema-version change and both owners'
   approval.

## Required upstream API, repeated in full

Blocks 3–5 consume:

```python
class Task1DecisionService(Protocol):
    def assess(
        self,
        *,
        normalized_case: Task1NormalizedFeatures,
    ) -> DecisionHandoffV1: ...
```

### `DecisionHandoffV1`

| Field | Required content |
|---|---|
| `schema_version` | literal `"1.0"` |
| `handoff_id` | deterministic input/artifact identity; never label-derived |
| `case_id` | runtime correlation only |
| `features` | strict `DecisionFeaturesV1` |
| `structured_pathway` | preliminary pathway from visible structured evidence |
| `input_quality` | missing, invalid, contradiction, consistency, and OOD status |
| `predictor` | `PredictorAssessmentV1` |
| `routing_recommendation` | `predictor_owned` or `llm_required` |
| `routing_reasons` | closed enum tuple |
| `artifact_manifest_digest` | SHA-256 of validated artifact manifest |

### `DecisionFeaturesV1`

| Field | Exact type/range | Downstream treatment |
|---|---|---|
| `schema_version` | literal `"1.0"` | Compatibility check |
| `case_id` | non-empty string | Correlation only; never evidence or a weight |
| `age` | float `0..120` or null | Always-visible structured evidence |
| `psa` | non-negative float or null | Always-visible structured evidence |
| `previous_psa` | non-negative float or null | Private structured/derived evidence |
| `supplied_psa_velocity` | finite float or null | Use only with quality status |
| `pirads` | integer `1..5` or null | Requires evaluator-grounded radiology evidence when weighted |
| `reported_psad` | non-negative float or null | Requires radiology grounding when weighted |
| `prostate_volume` | positive float or null | Requires radiology grounding when weighted |
| `cspca_score` | float `0..1` or null | Uncalibrated supplied signal; not truth |
| `dre` | closed DRE enum | Unknown remains distinct from normal |
| `biopsy_history` | `none`, `negative`, `positive`, `unknown` | Preliminary structured pathway evidence |
| `recalculated_psad` | non-negative float or null | Deterministic derived value |
| `psad_absolute_error` | non-negative float or null | Consistency diagnostic |
| `psa_delta` | finite float or null | Deterministic derived value |
| `psa_delta_direction` | `rising`, `stable`, `falling`, `unknown` | Deterministic derived category |
| `feature_provenance` | tuple of typed entries | Audit only; never copied directly to prose |

The consumer must use this object as supplied. It must not recalculate features,
guess missing values, or import training feature code.

### `StructuredPathwayAssessmentV1`

Required fields:

- `category`: `biopsy_naive`, `prior_negative`, `known_positive`, or `unclear`.
- `confidence`: `clear` or `uncertain`.
- `source`: literal `structured_prompt`.
- `evidence`: compact non-narrative statements from structured data.
- `contradictions`: closed contradiction-code tuple.

This assessment is preliminary. Only the routed retrieval branch may refine it
using revealed evidence; refinement does not mutate the upstream object.

### `InputQualityAssessmentV1`

Required fields:

- `critical_missing`: required fields that are absent.
- `noncritical_missing`: optional fields that are absent.
- `invalid_fields`: closed rejected-field/error codes.
- `consistency_flags`: deterministic cross-field consistency codes.
- `contradiction_flags`: structured pathway/data contradiction codes.
- `ood_flags`: out-of-distribution codes.
- `input_complete`: deterministic boolean under the frozen quality policy.

### `PredictorAssessmentV1`

| Field | Exact type | Invariant/use |
|---|---|---|
| `assessment_id` | deterministic string/hash | Tied to input and artifact versions, never label |
| `decision` | `yes` or `no` | Private predicted decision supplied to the arbiter |
| `raw_probability_yes` | float `[0,1]` | Private pre-calibration diagnostic only |
| `probability_yes` | float `[0,1]` | Private calibrated diagnostic only |
| `threshold` | float `[0,1]` | Private frozen threshold |
| `signed_margin` | float `[-1,1]` | `probability_yes - threshold` |
| `absolute_margin` | float `[0,1]` | Absolute signed margin |
| `confidence` | `clear`, `borderline`, `uncertain` | Deterministic predictor confidence |
| `ownership_eligible` | boolean | Must agree with routing recommendation |
| `model_name`, `model_version` | strings | Frozen artifact identity |
| `feature_contract_version` | string | Must match feature manifest |
| `calibration_method`, `calibration_version` | strings | Explicit `none` permitted |
| `threshold_policy_version` | string | Frozen threshold policy |
| `ownership_policy_version` | string | Frozen routing policy |
| `training_data_digest` | SHA-256 string | Exact labeled-release manifest |
| `model_signals` | small closed typed tuple | Diagnostic only; never evaluator weights |
| `warnings` | closed warning enum tuple | Non-fatal warnings |

### Predictor fields used downstream

These are private fields used only between system components. They are not
submission fields and the final serializer must remove them.

- `assessment_id`
- `decision`
- `raw_probability_yes`
- calibrated `probability_yes`
- `threshold`
- `signed_margin` and `absolute_margin`
- deterministic `confidence`
- `ownership_eligible`
- model, feature, calibration, threshold, and ownership-policy versions
- training-data digest
- compact model signals and warnings

Downstream invariants:

- `decision=yes` exactly when `probability_yes >= threshold`.
- `signed_margin = probability_yes - threshold`.
- `absolute_margin = abs(signed_margin)`.
- `ownership_eligible=true` exactly matches `predictor_owned`.
- Unknown/extra fields, NaN, infinity, incompatible versions, or invalid hashes
  are rejected.
- `case_id` and model signals are never converted directly into evaluator
  variable weights.

Routing reasons:

- `high_confidence_predictor`
- `low_probability_margin`
- `pathway_unclear`
- `known_positive_not_validated`
- `critical_missingness`
- `structured_contradiction`
- `out_of_distribution`
- `artifact_policy_mismatch`

Error contract:

- Ordinary uncertainty/OOD -> valid `llm_required` handoff.
- Invalid input -> `DecisionInputError` and hard case failure.
- Artifact mismatch -> `DecisionArtifactError` and hard readiness failure.
- Inference failure -> `DecisionInferenceError`; never silently ask Qwen to
  replace an unavailable predictor.

## End-to-end Blocks 3–5 lifecycle

1. Runtime loads and normalizes a case without reference outputs.
2. Runtime calls `Task1DecisionService.assess`.
3. Contract validator rejects incompatible/invalid handoffs.
4. If `predictor_owned`, skip LLM adjudication.
5. If `llm_required`, create an explicit unresolved-evidence plan.
6. Deterministic retrieval policy authorizes only necessary MCP calls.
7. Qwen returns `LlmDecisionAssessmentV1` through strict parsing/repair.
8. Block 4 applies the arbitration truth table and freezes a decision.
9. Block 5 builds confidence, weights, factors, and reveal sequence from the
   evidence ledger.
10. Qwen writes only concise free text constrained to the frozen decision.
11. Grounding, semantic, schema, and safety gates run.
12. Serializer writes both official JSON files atomically.
13. Non-sensitive trace records versions, owner, retrievals, warnings, and
   fallback reason.

No step after arbitration can change the decision.

## Block 3 — retrieval and structured Qwen adjudication

### Enabled Task 1 evidence sections

| Section | Tool | Use |
|---|---|---|
| `previous_notes` | `get_previous_notes` | Resolve surveillance/confirmatory versus established-treatment context and biopsy-history contradictions |
| `radiology_report` | `get_mri_report` | MRI detail when MRI evidence is decision-changing |
| `psa_trend` | `get_psa_trend` | Dated trajectory and trend quality |
| `laboratory_results` | `get_lab_results` | Specific non-visible workup evidence; headline PSA is visible already |
| `family_history` | `get_family_history` | First-degree family-history modifier when unresolved |

The official evaluator recognizes a sixth section, `pathology_report`, and the
raw clinical JSON can contain it. The current Task 1 tool registry and project
output contract do not expose it. Do not read, retrieve, prompt with, or weight
it until organizers confirm decision-time availability and both owners revise
the contract. This is a leakage-control requirement.

### Retrieval policy

- Do not call Block 3 for `predictor_owned` cases.
- For preliminary `known_positive` or `unclear`, request
  `previous_notes` unless absent; empty evidence is recorded as empty.
- Retrieve another section only to answer a declared unresolved question that
  could change decision or confidence.
- Deduplicate tools. Maximum successful reveals stays within the frozen budget.
- A failed/empty retrieval cannot support a factor.
- Tool names, consulted sections, and successful results must match exactly.
- Retrieval for better prose alone is prohibited because unnecessary reveals
  lower tool precision.

Recommended deterministic planning object:

```text
RetrievalPlanV1
  handoff_id
  unresolved_questions[]
  requested_sections[]
  reason_by_section{}
  max_tools
  policy_version
```

The LLM may propose a tool, but deterministic policy approves/rejects it before
MCP execution.

### Prompt contents

Allowed:

- Frozen handoff fields needed for reasoning.
- Preliminary pathway and quality/routing reasons.
- Approved successful retrieved evidence.
- Closed management-state and output schema.
- Direct instruction to decide biopsy now, not cancer existence.

Forbidden:

- Reference decision/reasoning, evaluator outputs, labels, future treatment, or
  post-decision pathology.
- Hidden chain-of-thought request.
- Restricted EAU/NCCN text or baseline guideline database.
- Raw neural embeddings.
- Unbounded patient-history dumps not approved by retrieval policy.

### `LlmDecisionAssessmentV1`

| Field | Required meaning |
|---|---|
| `schema_version` | literal `"1.0"` |
| `assessment_id` | Deterministic from handoff, model, prompt, seed, evidence |
| `handoff_id` | Exact handoff consumed |
| `decision` | `yes` or `no` assessment |
| `management_state` | One of five closed states |
| `evidence_sufficient` | Whether LLM ownership is permitted |
| `supporting_factors` | Small typed list: factor, value/summary, source section |
| `opposing_factors` | Same structure for opposing evidence |
| `unresolved_contradictions` | Explicit conflicts |
| `consulted_sections` | Exact ordered unique successful sections |
| `uncertainty_reasons` | Missing/ambiguous evidence |
| `model_version` | Frozen Qwen identity/revision |
| `prompt_version` | Frozen adjudication prompt |
| `seed` | Frozen generation seed |
| `warnings` | Closed warning tuple |

The object contains no hidden reasoning trace. Supporting/opposing factors are
compact, user-visible evidence summaries.

### Parse and repair

1. Parse directly into the strict schema.
2. Validate handoff ID, section list, evidence sources, and allowed enums.
3. Permit bounded schema repair without adding new patient evidence.
4. If still invalid, return a typed rejected assessment to arbitration.
5. Never silently substitute a previous response or predictor decision as if it
  came from Qwen.

### Block 3 tests

- Predictor-owned case makes zero adjudication/tool calls.
- Each routing reason creates the expected retrieval plan.
- Known-positive requests previous notes.
- Duplicate, unknown, over-budget, and argument-bearing tools are rejected.
- Empty, timeout, malformed, and contradictory evidence.
- Valid/invalid assessment, insufficient evidence, unknown management state,
  ungrounded factor, and mismatched handoff ID.
- Label/reference/pathology leakage assertions.
- Frozen prompt/model/seed and cached assessment identity.

## Block 4 — decision arbiter

### Arbitration truth table

| Predictor state | LLM state | LLM promoted? | Owner | Final decision |
|---|---|---:|---|---|
| `predictor_owned` | Not called | Any | `predictor` | Predictor decision |
| `llm_required` | Valid and sufficient | Yes | `llm` | LLM decision |
| `llm_required` | Valid but insufficient | Any | `predictor_fallback` | Predictor decision |
| `llm_required` | Invalid/timeout | Any | `predictor_fallback` | Predictor decision |
| `llm_required` | Valid and sufficient | No | `predictor_fallback` | Predictor decision |
| Input/artifact/schema failure | Any | Any | None | Hard failure; no output candidate |

Rules:

- Qwen cannot override a predictor-owned case.
- Do not average model probability with verbal confidence.
- Routed disagreement is expected; if the LLM branch is promoted and evidence
  sufficient, the LLM owns that routed decision.
- Every fallback records a closed reason.
- Low-confidence predictor fallback is marked uncertain downstream.
- The arbitration result is immutable.

### `DecisionArbitrationResultV1`

Required fields:

- `schema_version`
- `arbitration_id`
- `handoff_id`
- `predictor_assessment_id`
- `llm_assessment_id` or null
- `final_decision`
- `decision_owner`: `predictor`, `llm`, `predictor_fallback`
- `fallback_reason` or null
- `final_uncertainty_reasons`
- `revealed_sections`
- `policy_version`

### Fallback reasons

Initial closed values:

- `llm_not_promoted`
- `llm_invalid`
- `llm_timeout`
- `llm_evidence_insufficient`
- `llm_contract_mismatch`
- `retrieval_failure`

### Block 4 tests

- One test per truth-table row.
- Predictor-owned branch cannot call or accept LLM assessment.
- IDs and versions must match.
- Null/duplicate owners rejected.
- Invalid fallback reason combinations rejected.
- Mutation after arbitration rejected.
- Agreement/disagreement/fallback metrics produced.

## Block 5 — reasoning, safety, evaluation, and runtime

### Official output schema

This is the complete terminal contract. It contains no probability, score,
threshold, margin, model name, routing decision, or private model diagnostic.
The system writes two JSON files per case: one decision value and one structured
reasoning object.

Exact container paths:

```text
/output/prostate-biopsy-decision.json
/output/prostate-biopsy-decision-reasoning.json
```

Decision file:

```json
"yes"
```

Reasoning file has exactly:

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
  "reveal_sequence": ["radiology_report", "previous_notes"]
}
```

The example demonstrates shape only. It is not a golden patient answer.

Before writing these files, the serializer must positively construct this
allow-listed schema; it must not serialize `DecisionHandoffV1` and delete a few
known fields afterward. A contract test must fail if any probability or other
internal field appears in either output.

Allowed confidence: `clear`, `borderline`, `uncertain`.

Allowed weights: `not_used`, `noted`, `important`, `decisive`.

### Evidence ledger and grounding

For every weighted variable, record:

- Variable name and normalized value/summary.
- Importance weight.
- Direction relative to final decision.
- Evidence source: visible structured field or successful revealed section.
- Required section under evaluator mapping.
- Short rationale and any reliability warning.

Always-visible evaluator variables currently include `age` and `psa`.
Variables such as PI-RADS, volume, csPCa, and PSA density require
`radiology_report` when weighted. Family history requires `family_history`.
The current evaluator maps `bx` to `pathology_report`, but the active project
contract does not expose pathology. Therefore keep `bx=not_used` in
evaluator-facing weights until the contradiction is formally resolved; pathway
context can still be discussed through grounded `previous_notes` without
misrepresenting evaluator grounding.

`comorbidity` is currently ungradable and should remain `not_used` unless the
official mapping changes.

### Confidence policy

Derive confidence deterministically from:

- Predictor margin and ownership eligibility.
- Predictor/LLM agreement.
- Pathway certainty.
- Critical missingness and contradictions.
- OOD warnings.
- LLM evidence sufficiency.
- Fallback state.

Guidance:

- `clear`: strong concordant evidence with no material unresolved issue.
- `borderline`: mixed evidence still favoring one decision.
- `uncertain`: missing/contradictory evidence, OOD, or low-confidence fallback.

Never use the LLM's self-reported confidence alone.

### Variable-weight policy

- Weight clinical decision importance, not raw feature importance.
- SHAP/model signals are diagnostics, not automatic evaluator weights.
- Usually only one to three factors are `decisive`.
- A factor cannot be weighted above `not_used` without valid evidence source.
- Do not double count PSA, PSA density, volume, csPCa, and MRI findings without
  an explicit rationale.

### Free-text policy

Qwen receives:

- Frozen final decision.
- Final pathway/management state.
- Two to four approved factors.
- Opposing/uncertain factors that must be acknowledged.
- Allowed evidence summaries and section names.

It must:

- Explain biopsy now, not generic cancer risk.
- Mention prior-biopsy context when relevant.
- Avoid claiming cancer without pathology.
- Avoid unsupported thresholds and invented findings.
- Remain consistent with confidence and weights.
- Never change the final decision.

### Validation gates

Before writing files:

1. Decision is valid and equals arbitration result.
2. Confidence is allowed and consistent with fallback/uncertainty.
3. All ten weight keys exist exactly once.
4. Reveal sequence contains allowed unique successful sections only.
5. Every active weight is grounded.
6. Free text contains no unsupported or contradictory claim.
7. Case ID and assessment IDs match the current case.
8. Output satisfies strict Pydantic schema.
9. Bounded repair cannot change decision or add new evidence.
10. Both files are written atomically or the case fails visibly.

### Trace policy

Persist only non-sensitive metadata:

- Case ID for local correlation.
- Handoff, predictor, LLM, and arbitration IDs.
- Model/prompt/policy versions and hashes.
- Decision owner and fallback reason.
- Tool names/sections, counts, attempts, warnings, latency, and memory summary.

Do not persist raw notes, reports, labs, family history, prompt text, model
hidden reasoning, or backend errors that can echo patient content.

## LLM branch promotion experiment

Compare predictor-only and selective-hybrid systems using the same outer test
cases and frozen upstream handoffs.

Enable LLM decision ownership only when:

- Complete selective hybrid improves mean F1 by at least `0.01` over
  predictor-only.
- It wins in at least 75% of paired outer repeats.
- Mean sensitivity remains `>= 0.90`.
- No leakage or label-dependent prompting exists.
- The assessment is generated from frozen label-free case evidence.

If it fails, keep `llm_not_promoted` and run Qwen explanation-only. This is a
successful fallback architecture, not a failed project.

## System evaluation

### Decision and routing metrics

- Positive-class F1, sensitivity, specificity, precision, balanced accuracy.
- Confusion matrix, ROC-AUC, PR-AUC, Brier score, calibration.
- Pathway-specific performance.
- Predictor-owned coverage and conditional accuracy.
- LLM route/ownership rate.
- Agreement, disagreement, invalid assessment, evidence-insufficient, and
  fallback rates.

### Official evaluator gate

- Ranking score `>= 0.6964`.
- Mean case score `> 0.5669`.
- Tool precision `>= 0.98`.
- Section grounding exactly `1.0`.
- Rationale score `>= 0.7123` when the judge is available.
- Valid output for all 195 released cases.
- Zero silent fallbacks.

Official replay is an in-sample evaluator-facing diagnostic, not external
validation. Do not tune repeatedly against it after every prompt edit.

### Reliability suite

- All 195 cases.
- Repeated seeded inference on representative cases.
- Predictor-owned, LLM-owned, disagreement, and every fallback path.
- Empty and malformed sections.
- Tool timeout and duplicate request.
- Model startup/generation/form failure.
- Schema and semantic repair.
- Output overwrite/atomicity behavior.
- No network and read-only model/input mounts.

## Planned files

New planned shared/agent files:

```text
src/chimera_task1/contracts/decision_handoff.py
src/chimera_task1/contracts/adjudication.py
src/chimera_task1/contracts/arbitration.py
src/chimera_task1/agent/adjudication.py
src/chimera_task1/agent/retrieval_planner.py
src/chimera_task1/runtime/arbitration.py
tests/contract/test_task1_decision_handoff.py
tests/contract/test_task1_adjudication.py
tests/contract/test_task1_arbitration.py
tests/fixtures/task1/decision_handoff_v1.json
```

Likely existing files to extend:

```text
src/chimera_task1/agent/orchestration.py
src/chimera_task1/agent/prompts.py
src/chimera_task1/agent/form_fill.py
src/chimera_task1/agent/state.py
src/chimera_task1/tools/retrieval/registry.py
src/chimera_task1/evidence/ledger.py
src/chimera_task1/evidence/grounding.py
src/chimera_task1/evidence/variable_weights.py
src/chimera_task1/evidence/reasoning_checks.py
src/chimera_task1/runtime/agent_runner.py
src/chimera_task1/runtime/validation_gate.py
src/chimera_task1/runtime/serializer.py
src/chimera_task1/evaluation/agent_metrics.py
src/chimera_task1/evaluation/official_adapter.py
submission/inference.py
```

File names may be refined in the contract pull request, but the dependency
direction and ownership cannot change silently.

## Test plan

### Contract tests

- Upstream handoff fake and real service compatibility.
- Strict LLM assessment and arbitration schemas.
- JSON round-trip and extra-field rejection.
- ID, version, enum, numeric, and section consistency.

### Block 3 tests

- Retrieval plan by every pathway/routing reason.
- Zero tools for predictor-owned cases.
- Previous notes for known-positive/unclear.
- Empty/failed/duplicate/unknown/over-budget retrieval.
- Valid, invalid, insufficient, contradictory, and timed-out Qwen assessment.
- No reference/pathology/restricted-source content in prompts.

### Block 4 tests

- Every truth-table row.
- Agreement and disagreement.
- LLM promoted/not promoted.
- All fallback reasons.
- Immutable decision and single owner.

### Block 5 tests

- Every confidence class and weight level.
- Grounded and deliberately ungrounded ledgers.
- Required-section mapping and active five-section contract.
- Unsupported free text, decision contradiction, overclaiming, and missing
  prior-biopsy context.
- Schema repair without decision mutation.
- Atomic output and safe trace.

### Integration tests

- Fake upstream service before real predictor exists.
- Real service without consumer code changes.
- Five-case pathway smoke set.
- Full 195-case run.
- Official flat Grand Challenge adapter.
- No-network container and read-only input/model.

## Local run workflow

Install the approved local model once:

```bash
./task1 setup
```

Create a non-reference case:

```bash
./task1 new PT-NEW-002
```

Fill:

```text
data/new_task1_cases/PT-NEW-002/structured-prompt.json
data/new_task1_cases/PT-NEW-002/prostate-biopsy-decision-clinical-data.json
```

Predict:

```bash
./task1 predict PT-NEW-002
```

Inspect:

```text
reports/new_predictions/PT-NEW-002/prostate-biopsy-decision.json
reports/new_predictions/PT-NEW-002/prostate-biopsy-decision-reasoning.json
reports/new_prediction_traces/PT-NEW-002.json
```

The new selective architecture must add owner/handoff/arbitration metadata to
the non-sensitive trace without changing official output shape.

## Offline packaging and GPU qualification

Fetch/pin the model before container build; no runtime download:

```bash
uv run --with huggingface-hub==0.36.0 \
  python experiments/runner/fetch_submission_model.py
```

Build and smoke test on Linux/amd64 GPU:

```bash
docker build --platform linux/amd64 \
  --file submission/Dockerfile \
  --tag chimera-task1:dev .

docker run --rm --platform linux/amd64 --gpus all --network none \
  --volume "$PWD/submission/smoke_test/input:/input:ro" \
  --volume "$PWD/submission/smoke_test/output:/output" \
  --volume "$PWD/models/qwen3-4b-instruct-2507:/opt/ml/model:ro" \
  chimera-task1:dev
```

Hardware acceptance:

```bash
CHIMERA_GPU_RUN_LABEL=t4 ./submission/validate_gpu.sh
CHIMERA_GPU_RUN_LABEL=a10g ./submission/validate_gpu.sh
```

Package only after organizer confirmation of the model-asset mounting rule:

```bash
./submission/do_save.sh
```

Record image/model archive hashes, source commit, model shards, prompt and
policy versions, outputs, cold-start time, per-case time, and peak GPU memory.

## GitHub workflow

Branches:

- `task1/contracts-v1`: shared contracts, fake service, fixtures, tests.
- `task1/smoovie-decision-engine`: upstream Blocks 1–2.
- `task1/xuan-agent-integration`: Blocks 3–5 against fake service.
- `task1/selective-hybrid-integration`: temporary real-service integration.

Recommended Blocks 3–5 pull requests:

1. Consumer contract tests, fake service, adjudication/arbitration contracts.
2. Deterministic retrieval plan and structured Qwen assessment.
3. Arbiter truth table and fallback trace.
4. Evidence ledger, confidence, weights, grounding, free-text gate.
5. Complete runtime and 195-case reliability.
6. Real upstream service integration and paired validation.
7. Official replay and frozen offline candidate.

Every pull request records contract version, tests, prompt/model change,
retrieval impact, privacy/leakage review, metrics, rollback, and generated
artifact/report hashes.

## ASAP execution order

### Start without waiting for the trained predictor

1. Merge shared contract models and fixture.
2. Implement a fake `Task1DecisionService` covering predictor-owned,
   low-margin, known-positive, unclear, OOD, and critical-missing cases.
3. Build Block 3, arbiter, evidence plan, and validators against the fake.
4. Prepare full reliability and evaluator harnesses.

### Integrate when the real service is ready

1. Replace fake with real service; consumer code must not change.
2. Run contract tests and five-case smoke set.
3. Run all 195 cases.
4. Run paired predictor-only versus selective-hybrid validation.
5. Enable LLM ownership only if promotion passes.
6. Run frozen official replay once for candidate selection.
7. Qualify offline GPU package.

Do not delay this path for MRI, Gemma, guideline RAG, UI work, a separate
service, or pseudo-labeling.

## Troubleshooting and decisions

- If upstream contract validation fails, stop; do not parse a bare dictionary.
- If Qwen is invalid or evidence-insufficient, use explicit predictor fallback.
- If Qwen ownership fails promotion, keep it explanation-only.
- If a retrieval is empty, record emptiness and do not cite it.
- If tool precision falls, reduce retrieval through predeclared rules rather
  than hiding actual calls from reveal sequence.
- If grounding fails, lower the variable weight or retrieve the required
  permitted section; never fabricate grounding.
- If `bx` grounding requires unavailable pathology, keep `bx=not_used` and use
  grounded notes in prose/pathway assessment.
- If Docker/model asset rules remain contradictory, obtain organizer
  confirmation before spending a submission slot.
- If a patient-data error can appear in exception text, persist only exception
  type and a safe code.

## Deliverables to the shared candidate

- `LlmDecisionAssessmentV1` and `DecisionArbitrationResultV1` contracts.
- Retrieval policy/version and tool-call tests.
- Prompt, parser, repair rules, Qwen revision, seed, and model manifest.
- Arbitration policy and fallback matrix.
- Evidence, confidence, weight, reveal, and free-text policies.
- Complete traces without patient evidence.
- Paired LLM promotion report.
- 195-case reliability report.
- Official evaluator report and ablations.
- Docker/GPU acceptance report.
- Source, model, prompt, policy, report, image, and archive hashes.

## Definition of done for Blocks 3–5

Blocks 3–5 are complete only when:

- A fresh clone reproduces environment and deterministic controls.
- Fake and real upstream services pass the same consumer tests.
- Predictor-owned cases make zero adjudication calls.
- Routed cases produce valid assessments or explicit typed rejection/fallback.
- Exactly one immutable decision owner exists for every successful case.
- Reasoning is grounded in visible or actually revealed evidence.
- All 195 cases produce valid output or a visible failure blocks promotion.
- There are zero silent fallbacks.
- LLM decision ownership is enabled only after paired promotion.
- Official evaluator and internal gates pass.
- The exact frozen candidate runs offline on required hardware.
- The repository, artifact, prompt, report, model, and container hashes are
  recorded together.

## Companion document

Blocks 1–2 are specified independently in
`docs/TASK1_BLOCKS_1_2_DECISION_ENGINE_HANDBOOK.md`. The upstream contract is
duplicated intentionally so neither handbook depends on undocumented context.
