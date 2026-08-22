# Task 1 Knowledge Source Register

Last updated: **2026-08-13**

Every external corpus, guideline, pretrained model, embedding database, or
static knowledge asset must be recorded here before it is used in an experiment,
prompt, repository, Docker image, submission, or public artifact. Public
availability is not the same as permission for software use or redistribution.

| ID | Source | Provenance/status | Permitted project use | Blocked use | Decision |
|---|---|---|---|---|---|
| K-001 | 2026 EAU full prostate-cancer guideline PDF | User-supplied official PDF; hash recorded in `CLINICAL_REFERENCE_REVIEW.md`; live terms checked 2026-07-21 | Personal/internal reading and high-level clinical understanding | Repository copy, prompt/RAG corpus, extracted chunks, embeddings, derived rule asset, Docker, submission, or public reproduction without written permission | Blocked from software and packaging |
| K-002 | 2026 EAU pocket prostate-cancer guideline PDF | User-supplied official PDF; hash recorded in `CLINICAL_REFERENCE_REVIEW.md`; same EAU terms | Personal/internal orientation and cross-checking | Same as K-001 | Blocked from software and packaging |
| K-003 | Official baseline `resources/guidelines_db/` | Prebuilt Chroma database in official baseline; local inspection shows retrievable raw guideline chunks; participant sublicense not identified | Read-only architectural inspection | Prompts, RAG, Docker, submission, redistribution, or experiments until written scope is clarified | Blocked pending organizer/rightsholder answer |
| K-004 | NCCN guideline content | Mentioned by challenge participants; license not reviewed and no permission supplied | None beyond separately lawful personal access | Any ingestion, transformation, embedding, software use, packaging, or redistribution | Blocked pending independent review |
| K-005 | CHIMERA training release | On-disk official challenge release; use remains subject to the dataset license and challenge rules | Authorized challenge analysis and validation within the applicable terms | Unapproved redistribution or use outside the license scope | Allowed conditionally; preserve provenance |
| K-006 | CHIMERA live pages and evaluator | Official challenge web pages and GitHub evaluation implementation; active and version-sensitive | Contract verification, schema/evaluator audit, citations, and project records | Treating an old snapshot as permanently authoritative | Allowed; re-verify and pin dates/commits |
| K-007 | Qwen3-4B-Instruct-2507 | Official `Qwen/Qwen3-4B-Instruct-2507`; revision `cdbee75f17c01a7cc42f958dc650907174af0554`; Apache-2.0; model index reports 8,045,591,552 tensor bytes and the three physical shards total 8,044,982,000 bytes; per-shard SHA-256 recorded 2026-08-13 | Primary local LLM for Task 1; controlled Task 2 ablation; exact original weights and license may be packaged for Task 1 | Unpinned community fine-tunes or model substitutions without a new provenance/license/validation entry | Approved and locally materialized for Task 1; local Q4_K_M remains development-only; Task 2 did not promote it |
| K-008 | Gemma 4 E2B-it | Official `google/gemma-4-E2B-it`; Hugging Face API revision `3e22461f65e89153144f8adb70e3b8c2cc9845a7` verified 2026-08-12; Apache-2.0; used by current official baseline | Controlled model comparison after Qwen path is stable; package exact weights and license only for a frozen experiment | Silent replacement of primary model or simultaneous packaging before disk/GPU budget and validation justify it | Approved comparison model; not yet downloaded |
| K-009 | Official evaluator rationale judge `gemma4:e4b` | Exact Ollama model identifier hard-coded as the default in evaluator commit `55c7ca...`; digest `c6eb396d...`; pulled locally only to reproduce the official rationale metric | Local evaluation of frozen candidate/control rationale alignment | Submission inference, patient decision generation, or replacement of the primary Task 1 model | Exact Qwen/control replay completed 2026-08-14; local 9.6 GB copy removed after result freeze to preserve packaging space |

## Approval checklist

Before changing a blocked source to allowed, record:

1. Rights holder and authoritative license or written permission.
2. Exact source title, version, URL or file hash, and retrieval date.
3. Whether software use, AI/ML processing, modification, derivative works,
   redistribution, Docker packaging, challenge evaluation, source release, and
   publication are each covered.
4. Attribution, notice, share-alike, non-commercial, or access-control duties.
5. Whether downstream model weights, embeddings, caches, and generated outputs
   are covered.
6. The approving team member and date.
7. The experiments and deliverables that may use the source.

If any required right is unclear, keep the source blocked and use a license-clean
system design.
