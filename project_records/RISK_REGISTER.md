# Task 1 Risk Register

Last updated: **2026-08-14**

| ID | Risk | Likelihood | Impact | Required control | Current status |
|---|---|---|---|---|---|
| R-001 | Active challenge pages and evaluator change during development. | High | High | Pin verification date and commit; recheck before metric/schema/submission decisions. | Rechecked 2026-08-13; ongoing until submission |
| R-002 | Team optimizes stale AUROC/csPCa framing instead of biopsy F1. | High | High | Treat live Task 1 page and evaluator as authoritative; keep stale local overview secondary. | Controlled by context files |
| R-003 | Label meaning mixes biopsy-naive, prior-negative, and prior-positive pathways. | High | High | Manual pathway audit and explicit pathway feature; lower confidence for contradictions. | Controlled structurally: audit counts 49 biopsy-naive, 30 prior-negative, and 116 known-positive; LLM runner resolves pathway before form fill |
| R-004 | Post-decision pathology, future PSA, or later notes leak into features. | High | Critical | Record decision-time availability for every field; exclude or quarantine uncertain fields. | Unresolved release limitation: no authoritative per-document decision timestamp; no pathology tool is exposed and reference outputs are excluded |
| R-005 | Small labeled cohort causes unstable model and threshold selection. | High | High | Repeated nested validation, small feature set, strong regularization, stability reporting. | Open |
| R-006 | Always-positive policy appears deceptively competitive. | High | Medium | Report prevalence, confusion matrix, specificity, and clinical harms with F1. | Known |
| R-007 | MRI 1024-d representations overfit 91 labels. | High | High | Fold-safe PCA/reduction or regularized auxiliary head; late fusion; strict ablation. | Deferred |
| R-008 | Duplicate/near-duplicate patients leak across folds. | Medium | High | Exact/near-duplicate audit and group-aware fold construction. | No exact visible/clinical duplicates and no clinical-text pairs at 0.90 trigram Jaccard; stable patient identifiers remain unavailable |
| R-009 | Institution or scanner signals become shortcuts and fail externally. | Medium | High | Audit center/scanner proxies; use robustness and external-domain sensitivity checks. | Not measurable from released structured schema: no centre identifier; candidate does not use an explicit centre feature |
| R-010 | Agent reveals too many sections. | High | Medium | Bounded retrieval policy; cache/deduplicate calls; measure tool precision. | Control scores 0.9846, but Qwen scores 0.9000 on released labels; open competitive risk |
| R-011 | Agent assigns weight to evidence without revealing mapped source. | High | High | Evidence ledger and pre-output grounding validator. | Controlled in runner v1; training grounding 1.0 |
| R-012 | Visible prompt fields are assumed grounded although evaluator only exempts age and PSA. | High | High | Follow `section_variable_mapping.json`; verify organizer intent. | Open contradiction |
| R-013 | Baseline README statement “tool use is not scored” misguides design. | High | High | Follow current evaluator and live repositories page. | Controlled by context files |
| R-014 | Free-text reasoning hallucinates unsupported clinical details. | Medium | High | Provide only patient evidence and predictor metadata; reject ungrounded weights, MRI-as-pathology claims, calibrated csPCa claims, and unsupported cancer claims; limit to 2–4 factors; run rationale judge. | Validators repaired all 195 cases; exact judge completed with Qwen mean rationale 0.7169, but model-based judging is not clinical validation |
| R-015 | Output typo, enum, or schema failure zeros otherwise valid cases. | Medium | Critical | Locked Pydantic schema, deterministic serializer, retry limits, test fixtures. | Controlled: 195/195 Qwen cases, 0 schema/runtime errors; 84 tests pass |
| R-016 | Offline model assets or GPU memory fail on Grand Challenge. | Medium | High | Package pinned Qwen weights as the official read-only Model mount; FP16 for T4 compatibility; 8192-token context; reproducible T4/A10G Docker smoke and memory/runtime measurement. | Exact 8.05 GB weights downloaded and hash-recorded; GPU platform runs pending |
| R-017 | Five validation submissions are used for iterative leaderboard overfitting. | Medium | High | Pre-register submission hypotheses; submit only materially distinct frozen systems. | Controlled process: five slots are pre-registered and none has been spent locally |
| R-018 | Unlabeled cases are treated as negatives or pseudo-labels contaminate evaluation. | Medium | High | Keep unlabeled status explicit; no pseudo-labeling without a separate approved experiment. | Controlled by policy |
| R-019 | EAU guideline content or derivatives are embedded in prompts, RAG, software, Docker, or public outputs without written permission. | High | Critical | Exclude the PDFs and all copied, summarized-as-corpus, rule-converted, or embedded derivatives; require documented permission before use. | Blocked by policy |
| R-020 | The official baseline's prebuilt guideline database is assumed safe merely because organizers published it. | High | Critical | Treat repository availability as distinct from a sublicense; disable and exclude the database pending written scope clarification. | Open organizer question |
| R-021 | The team misreads the EAU restriction as a ban on all LLM reasoning and removes useful evidence synthesis. | Medium | High | Separate corpus licensing from model use; allow local LLM reasoning over patient evidence and license-audited assets. | Controlled by context files |
| R-022 | EAU thresholds or risk calculators are copied as universal Task 1 rules and miscalibrate across pathways or centers. | High | High | Use only conceptual guardrails; validate every operational threshold inside training folds and audit pathway interactions. | Controlled by experiment policy |
| R-023 | NCCN content is packaged without an independent permission review. | Medium | Critical | Keep NCCN content and derivatives out of the system until its own license evidence is recorded. | Blocked by policy |
| R-024 | LLM emits invalid JSON, wrong decision wording, or ungrounded weights. | High | Critical | Locked Pydantic form, eligible-variable list, grounding/consistency validation, five bounded form attempts, explicit failure for the submission candidate, and fallback-rate reporting in research modes. | Controlled in 84 tests and 195/195 real-Qwen cases; 90 cases exercised repairs, maximum 3 attempts |
| R-025 | LLM calls excessive, duplicate, unknown, or malformed tools and loses evaluator tool precision. | High | High | Five-tool allowlist, no-argument schemas, deduplication, three-call budget, bounded rounds, and tool-precision evaluation. | Bounded and schema-safe, but mean official tool precision 0.900 trails control 0.985; open competitive risk |
| R-026 | Local Q4 development results are mistaken for final FP16 submission behavior. | Medium | High | Label Ollama Q4_K_M as development-only; freeze and rerun the exact FP16 vLLM image on T4/A10G before any submission. | Open |
| R-027 | Deterministic fallback silently hides LLM failures. | Medium | High | Persist per-case trace metadata with `fallback_used`, report completion/fallback rates, and disable fallback in the short LLM command and submission image. | Controlled: all 195 cases ran with `--no-fallback`; fallback count 0; candidate defaults now fail visibly |
| R-028 | Live pages require weights inside Docker while the current official baseline ships a separate Grand Challenge Model archive. | Medium | Critical | Preserve exact package hashes, follow the baseline pattern only provisionally, obtain written organizer confirmation before upload, and embed weights if required. | Open official contradiction, reverified 2026-08-14 |

## Escalation rule

Any experiment with unresolved temporal leakage, unclear patient grouping, a
schema mismatch, or unverified knowledge-source rights must be blocked from
comparison with the reference baseline until the issue is resolved.

## Task 2 risks — 2026-08-13

| ID | Risk | Likelihood | Impact | Control | Status |
|---|---|---|---|---|---|
| R2-001 | Perfect released-label fit is mistaken for generalization. | High | Critical | Mark every hierarchical result in-sample; use a pre-registered validation slot; keep ISUP fallback. | Open external risk |
| R2-002 | Two watchful-waiting labels make rare-class logic unstable. | High | High | Keep branches transparent; do not claim clinical validation; monitor external confusion matrix. | Open |
| R2-003 | Reference labels/free text are clinically or internally discordant. | High | High | Preserve anomaly log and warnings; optimize challenge output without calling it a deployable clinical system. | Controlled in documentation |
| R2-004 | Empty reference reveals conflict with section grounding. | High | High | Freeze no-reveal candidate, measure both scores, and reopen after organizer correction. | Open official contradiction |
| R2-005 | High-dimensional MRI/slide vectors overfit 72 labels. | High | High | Fold-local PCA and missingness indicators; reject after all variants lose to control. | Controlled; components rejected |
| R2-006 | LLM adds runtime/fallbacks without enough ranking gain. | High | Medium | Strict form, deterministic fallback, cohort comparison, promotion gate. | Controlled; LLM not packaged |
| R2-007 | Unlabeled 81 cases contaminate training. | Medium | High | Loader preserves label absence; no pseudo-labeling or transductive fitting. | Controlled |
| R2-008 | Data-derived thresholds encode synthetic-release quirks. | High | High | Name policy `development_*`, retain control, require external validation before stronger claim. | Open |
| R2-009 | Docker runtime downloads or calls network. | Low | Critical | Bundle code/dependency image at build; run final smoke with `--network none`. | Controlled |
| R2-010 | Guideline-derived software asset creates rights exposure. | Medium | Critical | No guideline corpus, RAG, copied text, or derivative rule asset in Task 2 image. | Controlled |
