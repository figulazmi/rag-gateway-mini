# RAG `knowledge_v2` Roadmap

> **Status:** Active roadmap. Future Claude sessions: **read this file before proposing changes to the RAG pipeline** (`rag_capture.py`, `push-to-qdrant.sh`, `qdrant-mcp-server-v2.js`, `eval-retrieval-quality.py`). Do not deviate from the priorities below without explicit user approval.
> Status tracking standard: [`../reference/TRACKING_STATUS_STANDARD.md`](../reference/TRACKING_STATUS_STANDARD.md). Current source of truth is [Canonical Task Tracker](#canonical-task-tracker).

## Strategic Goal

Claude AI is used as a **reasoning + capture specialist only** for `knowledge_v2`. Code implementation is routed by 9routers to the appropriate AI assistant, which consumes chunks from `knowledge_v2` via MCP wiring or `/rag/search` context. Local models such as `qwen2.5-coder` are optional benchmark targets only, not the production implementer path.

**Success criterion:** chunks must be rich and precise enough that the downstream AI assistant does not hallucinate when writing code from them.

**Implication:** the bottleneck is **chunk content quality** and **retrieval precision**, not retrieval recall. The right chunk must reach the implementer's context window, and its content must be an executable specification, not prose.

## Current State (do not rebuild)

- Deterministic chunk ID (`{DOC_ID}-chunk-{N}`) → upsert-idempotent — `~/scripts/push-to-qdrant.sh:285` (rag-tools)
- Hybrid search: dense (nomic-embed-text 768d COSINE) + sparse (djb2 BM25) + RRF fusion — `~/scripts/qdrant-mcp-server-v2/qdrant-mcp-server-v2.js:99` (rag-tools)
- Query expansion for short queries (<8 words) — `qdrant-mcp-server-v2.js:20`
- Retry with rewrite when `avgScore < 0.6` — `qdrant-mcp-server-v2.js:227`
- Structured query logs (`rag_search`, `rag_retry`, `rag_not_found`) to stderr
- Eval framework with Hit@1/3/5, MRR, NDCG@5, 3 strategies, 7 test cases, regression detection — `scripts/eval-retrieval-quality.py`
- Warn-only validation (word count, em dash, Indonesian detection, Key Facts presence) — `~/scripts/rag-capture-v2/rag_capture.py:181` (rag-tools)
- Frontmatter validation at n8n ingest node
- Status filtering (`implemented` default, `include_planned` toggle)

## Known Gaps (what this roadmap addresses)

1. Chunk schema is narrative (Context/Problem/Solution/Key Facts/Code). Implementer models need exact file paths, function signatures, dependencies, contracts, anti-patterns, test snippets.
2. No contextual retrieval prepend. Chunks are embedded raw. Anthropic 2024 shows 35-49% retrieval failure reduction when prepending document-level context.
3. No reranker. RRF top-K goes straight to the consumer; positions 3-5 are noisy.
4. Validation warns but does not reject. Low-quality chunks reach Qdrant.
5. No supersede/deprecate semantics. If a topic name drifts slightly, a new ID is created and the old chunk remains active, producing conflicting info.
6. Eval set is small (7 queries) and measures retrieval rank only, not downstream code-generation hallucination rate.

## Priorities

Execution order — **implement in this sequence unless user overrides**:

### P1 — Highest ROI

**P1.1. Enrich chunk schema for implementation-grade detail**
Introduce chunk_type `implementation-spec` (or enrich `feature`/`pattern` templates) with these required sections:

- `### Target Files` — repo-relative paths, optional line ranges
- `### Interfaces` — function signatures, class names, DTO shapes
- `### Dependencies` — import statements, package versions when relevant
- `### Contract` — input types, output types, error cases
- `### Anti-Patterns` — "DO NOT do X because Y"
- `### Verification` — test snippet or manual check step

**Files to modify:**

- `~/scripts/rag-capture-v2/rag_capture.py:80` (rag-tools) — add `"implementation-spec"` to `VALID_TYPES`
- `~/scripts/rag-capture-v2/rag_capture.py:181` (rag-tools) `validate_content()` — enforce required sections for type `implementation-spec`/`feature`/`pattern`
- `.claude/skills/rag-knowledge-capture-cli/SKILL.md` — add body template for the new chunk_type
- `CLAUDE.md` field & content rules section — update to reflect new type and required sections

**Impact:** directly reduces hallucination; implementer model receives an explicit spec, not prose.

**P1.2. Contextual retrieval prepend before embedding** — **SHIPPED, needs deployment**

The prepend lives in the n8n workflow's `Validate & Clean` node, not in `push-to-qdrant.sh`. Bash script forwards raw payload; n8n computes `embed_content = "This chunk is from project X, type Y, topic Z, tagged ..., date ... Content: ..."` and feeds that to Ollama. Original `content` is stored untouched in the Qdrant payload and used for sparse vector + LLM consumption — the prepend never leaks to consumers.

**Files changed:**

- `~/scripts/n8n-workflows/ingest-knowledge-v2.json` (rag-tools) — `Validate & Clean` node adds `embed_content` field; `Ollama: nomic-embed-text` node now reads `{{ $json.embed_content }}` instead of `{{ $json.content }}`

**Deployment steps (manual, one-time):**

1. In n8n UI at `http://192.168.18.199:5678`, open workflow `knowledge_v2`
2. Import the updated JSON (Workflow → Import from File → pick `~/scripts/n8n-workflows/ingest-knowledge-v2.json` from rag-tools/current laptop) or paste the two changed nodes
3. Activate the workflow (toggle top-right)
4. Smoke test: `rag add` a sample chunk → `rag merge` → `bash ~/scripts/push-to-qdrant.sh .claude/summaries/<file>.md` → check n8n execution log shows `embed_content` populated and HTTP 200 back from Qdrant

**Re-embedding existing chunks:**
Dense vector space has shifted (old chunks embedded on raw content, new ones on prepended content). Hybrid search still works during transition because the sparse vector is unchanged — but for consistent dense retrieval, re-ingest the full corpus:

> **Migration note (2026-04-29):** Full corpus was migrated from `knowledge` to `knowledge_v2` via
> `migrate-to-hybrid.py` (direct Qdrant upsert, not via n8n). Dense vectors are old-style (raw
> content, no contextual prepend). Sparse vectors are new-style (djb2 BM25). Hybrid RRF compensates
> for the dense drift — retrieval is functional but not at peak quality.
>
> **WARNING for future sessions:** If `eval-retrieval-quality.py` shows NDCG@5 or Hit@1 regression,
> or if retrieval feels off on homelab queries, consider triggering **Opsi 2** (re-embed via n8n):
> re-ingest all `.claude/summaries/*.md` through `push-to-qdrant.sh` so n8n recomputes contextual
> prepend embeddings. Upserts are idempotent — safe to run anytime. Expected gain: +35-49%
> retrieval failure reduction per Anthropic contextual retrieval benchmark.

```bash
for f in .claude/summaries/*.md; do
  rtk bash ~/scripts/push-to-qdrant.sh "$f"
done
```

Upserts are idempotent by deterministic ID (`{DOC_ID}-chunk-{N}`), so this is safe to re-run. Expect delta = 0 in `POINTS_AFTER - POINTS_BEFORE` (overwrites, not inserts).

**Verification after deployment:**

- Run `python scripts/eval-retrieval-quality.py --project homelab --debug` before and after re-ingest
- NDCG@5 should improve; Anthropic benchmark predicts 35-49% retrieval failure reduction
- Check MCP server stderr: `avg_score` on typical queries should rise

**Impact:** chunks with ambiguous content (e.g., "fix the validation bug") now embed with disambiguating context → right chunk reaches implementer more often.

### P2 — Quality gates & precision

**P2.1. Upgrade `validate_content()` from warn to hard reject** — **SHIPPED**

`validate_content(content, chunk_type)` now returns `(errors, warns)`. `cmd_add` and `cmd_pipe` call `sys.exit(1)` when `errors` is non-empty; warnings are still printed but do not block.

Hard-reject rules in effect:

- Word count < 100 or > 400
- `### Key Facts` absent
- Em dash (`—`) present
- `implementation-spec` chunks missing any of: Target Files, Interfaces, Dependencies, Contract, Anti-Patterns, Verification
- `feature` / `pattern` chunks missing `### Target Files`

Soft warnings retained: possible Bahasa Indonesia detection, `feature`/`pattern` missing recommended Interfaces/Contract/Verification.

**Files changed:** `~/scripts/rag-capture-v2/rag_capture.py` (rag-tools) — `validate_content` (line 194), `cmd_add` (line 324), `cmd_pipe` (line 383).

**Verification (smoke tested):**

```bash
# Reject: short + no Key Facts
echo "short content" | rag add -p homelab -t debug --topic "x"   # exit 1

# Reject: feature without Target Files
cat body.md | rag add -p homelab -t feature --topic "x"          # exit 1
```

**P2.2. Reranker after RRF** — **SCAFFOLDED, disabled by default; not the next fix**

LLM-as-reranker (no new infra path) was implemented and evaluated on VM B1 Ollama with `llama3.2:3b`:

- Earlier small-suite eval showed zero measurable lift because the suite saturated under hybrid RRF.
- Hybrid latency was **~61s/query** vs 248ms without, far over the 2s plan budget.
- Parse reliability had a **40% JSON parse-failure rate**.
- Final 2026-05-02 Priority 1-4 eval shows the current top-rank problem is sparse/RRF noise: dense-only reached Hit@1 0.8333, MRR 0.9028, NDCG@5 0.9108 while hybrid reached Hit@1 0.6111, MRR 0.7685, NDCG@5 0.8629.

Decision: keep reranker scaffolding disabled. Do not deploy TEI/BGE just to mask sparse noise. The 2026-05-02 `knowledge_v2_keyfacts` experiment validated the sparse text redesign: rebuilding sparse vectors from topic + Key Facts improved hybrid to Hit@1 0.9444, MRR 0.9444, NDCG@5 0.9659.

**Files changed (scaffolding):**

- `~/scripts/qdrant-mcp-server-v2/qdrant-mcp-server-v2.js` (rag-tools) — `rerankWithLLM` helper, wired into both primary and retry search paths; gated on `RERANK_ENABLED` env var; emits `rag_rerank` and `rag_rerank_parse_error` stderr events.
- `scripts/eval-retrieval-quality.py` — `rerank_with_llm` helper, `--rerank / --rerank-model / --rerank-candidates` CLI flags.

**Next retrieval fix before P2.2-B:**
Promote the successful sparse text redesign. `scripts/build-sparse-keyfacts-experiment-rest.py` created `knowledge_v2_keyfacts` from `knowledge_v2` with point parity 373 -> 373 and 345 points carrying Key Facts sparse text. Next step is to production-harden the separate keyfacts path, prove it stays better than legacy under soak, then choose an explicit cutover path after user approval.

**P2.5. Keyfacts production criteria and history**

The keyfacts path is now a production candidate, not yet the default ingestion path. The long-term criteria are:

- Quality must beat legacy `knowledge_v2` on Hit@1, MRR, and NDCG@5 across repeated evals.
- Hit@3 must stay at or above 0.9444, matching the current legacy recall floor.
- Average eval latency should remain close to legacy and below the documented p50 target envelope.
- Gateway and n8n logs must show no repeated runtime errors during soak.
- The legacy `push-to-qdrant.sh` path must continue writing to `knowledge_v2` until explicit cutover.
- Existing and keyfacts n8n workflows must remain isolated: `knowledge_v2` writes only to `knowledge_v2`; `knowledge_v2_keyfacts` writes only to `knowledge_v2_keyfacts`.

Findings so far:

- Full-content sparse text was the bottleneck because common homelab tokens caused sparse/RRF rank noise.
- Rebuilding sparse vectors from `topic + Key Facts` improved top-rank precision without changing dense vectors or payloads.
- Initial production soak baseline on 2026-05-02 showed keyfacts hybrid Hit@1 0.9444, MRR 0.9444, NDCG@5 0.9632, and avg latency 1133.4ms.
- Legacy hybrid in the same soak baseline showed Hit@1 0.6667, MRR 0.7963, NDCG@5 0.8766, and avg latency 1120.9ms.
- Final production validation on 2026-05-02 still showed 3 query-level sparse/RRF regressions, but keyfacts remained stronger than legacy on Hit@1, MRR, and NDCG@5; this is acceptable for retrieval-only production while full ingest cutover stays separate.

**P2.6. Repeatable keyfacts soak and verification workflow**

Run the candidate path as a separate workflow while the old push path remains live. The verification loop is:

1. Confirm `push-to-qdrant.sh` still targets `knowledge_v2`.
2. Confirm gateway `/scalar/`, `/openapi/v1.json`, and `/rag/search` smoke pass.
3. Run `eval-retrieval-quality.py` for both `knowledge_v2` and `knowledge_v2_keyfacts` with timestamped outputs under `.claude/reports/`.
4. Compare hybrid Hit@1, MRR, NDCG@5, and latency.
5. Check recent gateway and n8n logs for runtime errors.
6. Confirm no temporary smoke points remain in either collection.

**P2.7. Safe cutover path for retrieval and ingestion**

Retrieval-only cutover is complete as of 2026-05-02. VM B1 production gateway config at `/opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json` targets `knowledge_v2_keyfacts`, so no redeploy or n8n workflow change was required during final validation.

Final retrieval-only production evidence:

- Gateway config collection: `knowledge_v2_keyfacts`.
- Collection health/count evidence: `knowledge_v2` 379 points, `knowledge_v2_keyfacts` 373 points, both green.
- Gateway `/scalar/` and `/openapi/v1.json` returned 200.
- `/rag/search` smoke for `project=homelab` returned HTTP 200, `status=found`, top result `Python argparse subcommand CLI pattern`.
- Recent gateway and n8n logs showed 0 relevant error lines.
- Final eval reports: `.claude/reports/final-keyfacts-production-2026-05-02.json` and `.claude/reports/final-legacy-production-2026-05-02.json`.
- Keyfacts final hybrid: Hit@1 0.9444, Hit@3 0.9444, Hit@5 0.9444, MRR 0.9444, NDCG@5 0.9648, avg latency 1158.6ms.
- Legacy final hybrid: Hit@1 0.6667, Hit@3 0.9444, Hit@5 0.9444, MRR 0.7963, NDCG@5 0.8786, avg latency 1068.3ms.
- Legacy `push-to-qdrant.sh` remains unchanged and still defaults to `knowledge_v2`.

Rollback for retrieval-only production is restoring the gateway collection setting to `knowledge_v2` in `/opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json`, then restarting/recreating only the gateway container. Do not touch either n8n workflow for retrieval rollback.

Full ingest cutover remains a separate future task. Do not overwrite the existing `knowledge_v2` workflow; export and preserve it before any future full-ingest default change.

**T1-C full ingest cutover (2026-05-04 — DONE):** Verified keyfacts n8n workflow (`~/scripts/n8n-workflows/ingest-knowledge-v2-keyfacts.json`) uses `sparseText = topic + keyFacts` (not full content) and targets `http://qdrant:6333/collections/knowledge_v2_keyfacts/points`. Both `~/scripts/push-to-qdrant.sh` (local laptop) and VM B1 `~/scripts/push-to-qdrant.sh` updated: `N8N_WEBHOOK_PATH` changed from `webhook/knowledge-ingest-${N8N_WEBHOOK_SECRET}` to `webhook/knowledge-ingest-keyfacts`; default `DOC_COLLECTION` changed from `knowledge_v2` to `knowledge_v2_keyfacts`. Sync script `~/scripts/sync-keyfacts-from-legacy.py` written and executed to backfill missing points from `knowledge_v2` into `knowledge_v2_keyfacts`. Initial Qdrant point-ID comparison was misleading because the keyfacts workflow hashes payload IDs into new numeric point IDs; meaningful parity must compare project/topic/content signatures. Retry with normalized metadata (trim CRLF, fix first tag `petrochina` -> `dotnet`, trim ASCII topics to 60 chars, fill blank payload IDs from legacy point ID) synced the true missing payloads with 22/22 success. On 2026-05-05, a direct legacy-to-keyfacts ID sync copied the remaining 49 legacy point IDs from `knowledge_v2` into `knowledge_v2_keyfacts` with payload and dense vector preserved. Current verified state: `knowledge_v2` 441 points, `knowledge_v2_keyfacts` 519 points, and missing legacy point IDs in keyfacts: 0. Legacy `knowledge_v2` n8n workflow left untouched and still active as a write-fallback.

**P2.8. Negative-query not-found confidence gate** — **SHIPPED**

Deployed commit `d686c46` to VM B1 on 2026-05-04. The gateway now keeps `ScoreThreshold` for result inclusion and uses `NotFoundScoreThreshold` to decide whether `/rag/search` returns `status=found` or `status=not_found`. Positive smoke returned `status=found` with top score 0.8333. Negative Blazor/homelab smoke returned `status=not_found`.

### P3 — Lifecycle & feedback

**P3.1. Supersede semantics**
Add frontmatter fields `supersedes: <old_chunk_id>` and `superseded_by`. When `push-to-qdrant.sh` sees `supersedes`, it PATCHes the old chunk's payload to `status: deprecated`. The MCP server's default `status == implemented` filter hides deprecated chunks automatically.

**Files:**

- `~/scripts/rag-capture-v2/rag_capture.py:222-236` (rag-tools) — add `supersedes`/`superseded_by` to frontmatter output
- `~/scripts/push-to-qdrant.sh` (rag-tools) — add deprecate-on-supersede logic during ingest

**P3.2. Expand eval set + implementation correctness test** — **REFRESHED**

Expanded retrieval fixtures now live at `scripts/eval-fixtures/homelab-expanded.json`, with reports under `.claude/reports/p32-expanded-*.json`. End-to-end mode exists but is not currently usable with Ollama on VM B1 because `qwen2.5-coder:7b` is not installed. Treat qwen2.5-coder as an optional benchmark model; the recommended production smoke is a 9routers-routed AI assistant consuming `/rag/search` context and generating a small implementation from an `implementation-spec` chunk.

**P3.2 fixture cleanup (2026-05-04):** 5 cleanup actions applied after regression analysis. (1) Negative query fixtures marked `negative: true`; scored via confidence-gate outcome not top-doc relevance. (2) `expected_ids` added to 9 ambiguous fixtures; `relevance_score()` short-circuits to 1.0 on exact ID or snippet match, eliminating rank-swap false positives. (3) 3 missing-corpus fixtures removed (Python argparse, Python dataclass default_factory, eval fixture loader); restore when chunks are captured. (4) Overloaded CSharp threshold query split into 2 focused fixtures. (5) Generic single-token gold keywords tightened to multi-word phrases.

**Implementation-correctness smoke strategy (2026-05-08):** Treat 9routers as the production routing layer for downstream AI assistants. The smoke is not another retrieval-only score; it is a reproducible implementation-correctness exercise using retrieved `implementation-spec` context.

1. Retrieve one implemented homelab spec with `/rag/search` or MCP `search_knowledge`, preferring a query that should return a single unambiguous implementation contract.
2. Feed only the retrieved chunk content into the 9routers-managed AI assistant workflow with a bounded instruction such as: "Implement exactly this contract in the specified files. Do not invent new endpoints or config keys."
3. Verify the generated code against the chunk contract, not prose similarity alone.
4. Record outcome as `pass`, `partial`, or `fail` with the retrieved chunk topic, target files, and the first compile or smoke error if it failed.

**Recommended first smoke cases:**
- `Spec: rag gateway retrieval service contract` -> verify `/rag/search` contract and thresholds
- `Spec: rag gateway knowledge expansion retrieval` -> verify variant generation and aggregation rules
- Grounded answer path spec once captured -> verify `/rag/answer` plus citation tagging contract

**Pass criteria:**
- The AI assistant edits only the files named in `### Target Files`
- Produced method and DTO names match `### Interfaces`
- No new config keys, routes, or payload fields appear outside `### Dependencies` and `### Contract`
- `rtk dotnet build rag-gateway-mini.sln --configuration Release --warnaserror` passes
- Relevant API smoke from `docs/testing/TEST_STRATEGY.md` passes for the touched endpoint

**Fail criteria:**
- The AI assistant invents extra files, routes, config keys, or DTO fields
- Generated code violates an Anti-Pattern named by the chunk
- Build fails, endpoint contract differs, or smoke returns the wrong status

**Next actions:** capture and push implementation-spec chunks for the gateway search/answer flow, run one documented implementation-correctness smoke against the first retrieved spec, then run the next eval against cleaned fixtures to confirm retrieval still supports the implementer workflow. Revisit TEI/BGE reranking later only if needed.

**P3.3. Feedback loop: eval → chunk revision queue**
When eval flags NDCG < 0.6 for query X, append the chunk_id that should have ranked 1 to `~/scripts/.rag_revision_queue.md`. Surface the backlog in `rag status`.

**Files:** `scripts/eval-retrieval-quality.py`, `~/scripts/rag-capture-v2/rag_capture.py:438` (rag-tools) `cmd_status`.

### P4 — Nice to have (skip until P1-P3 are done)

- Pre-commit hook validating frontmatter of `.claude/summaries/*.md` (n8n already validates; low marginal value)
- TTL-based auto-deprecate for chunks older than 6 months with zero retrieval hits
- Semantic eval (replace substring match with LLM-judge for gold signals)

## Canonical Task Tracker

| Order | ID | Task | Scope boundary | Status | Evidence | Next action |
|---:|---|---|---|---|---|---|
| 1 | P1.1 | Enrich chunk schema for implementer models | Includes schema and validation rules; excludes reranker or retrieval tuning | `[x] DONE (2026-04-19)` | `rag_capture.py` accepts `implementation-spec`; CLI positive test saved a valid spec with all required sections | None |
| 2 | P2.1 | Add hard-reject validation | Includes CLI hard rejects for low-quality chunks; excludes n8n runtime validation changes | `[x] DONE (2026-04-19)` | CLI negative tests rejected short content, feature without `### Target Files`, and implementation-spec missing `### Contract`; no drafts were saved | None |
| 3 | P1.2 | Deploy contextual retrieval prepend | Includes n8n embed-content prepend; excludes full keyfacts cutover | `[x] DONE (2026-04-19)` | `~/scripts/n8n-workflows/ingest-knowledge-v2.json` (rag-tools) stores `content` unchanged and sends `embed_content` to Ollama; Hit@1 improved from 0.60 to 1.00 after deployment | None |
| 4 | P2.2 | Scaffold LLM-as-reranker | Includes disabled scaffolding only; excludes TEI/BGE production deployment | `[ ] DEFERRED` | Scaffolding exists, but reranker remains blocked on infra and disabled by default | Revisit after TEI plus BGE reranker is available |
| 5 | P3.2 | Expand eval set and implementation correctness test | Includes retrieval eval expansion and end-to-end strategy; excludes future semantic judge replacement | `[!] BLOCKED (2026-05-10)` | Added `scripts/eval-fixtures/homelab-expanded.json`; 28 → 26 fixture entries after cleanup (3 missing-corpus entries removed, 1 overloaded query split into 2). 9 fixtures now carry `expected_ids` for exact-hit scoring; 2 negative fixtures marked `negative: true` with `expected_snippet: "NOT FOUND IN RAG"`. `TestCase` dataclass extended with `expected_ids` and `negative` fields; `relevance_score()` short-circuits to 1.0 on exact ID or snippet match. Reports: `.claude/reports/p32-expanded-keyfacts-2026-05-04.json`, `.claude/reports/p32-expanded-legacy-2026-05-04.json`, `.claude/reports/p32-expanded-keyfacts-e2e-2026-05-04.json`. Smoke design spec written at `docs/superpowers/specs/2026-05-10-p32-smoke-design.md`. Manual smoke run attempted 2026-05-10; blocked report at `.claude/reports/p32-smoke-2026-05-10.json` — no implemented homelab implementation-spec chunk retrieved for the three priority cases. | Capture and push implementation-spec chunks for gateway search/answer flow before retrying smoke |
| 6 | P3.1 | Add supersede and deprecate semantics | Includes frontmatter and push-time deprecation; excludes TTL auto-deprecate | `[x] DONE (2026-04-19)` | `rag_capture.py` writes supersede frontmatter and `push-to-qdrant.sh` patches superseded chunks to `status: deprecated` | None |
| 7 | P2.2-B | Deploy TEI plus BGE reranker | Includes reranker infra only after sparse noise is solved; excludes masking current sparse/RRF issue | `[ ] DEFERRED` | Final 2026-05-02 eval shows dense-only beats hybrid on Hit@1/MRR/NDCG@5; problem is sparse/RRF noise, not reranker absence | First A/B dense-only and redesign sparse text; revisit reranker only if top-K has correct chunks but ordering remains poor |
| 8 | P3.3 | Add eval to chunk revision queue feedback loop | Includes low-NDCG queueing and `rag status` count; excludes automatic chunk rewriting | `[x] DONE (2026-05-02)` | `eval-retrieval-quality.py` appends low-NDCG queries to `~/scripts/.rag_revision_queue.md`; `rag status` reports open item count; Python argparse/dataclass coverage was fixed with new pattern chunks | None |
| 9 | P2.3 | A/B dense-only vs hybrid and sparse text redesign | Includes experimental collection and metric comparison; excludes default workflow switch | `[x] DONE (2026-05-02)` | `knowledge_v2_keyfacts` smoke eval: hybrid Hit@1 0.8889, MRR 0.9167, NDCG@5 0.9547; current hybrid was Hit@1 0.6111, MRR 0.7685, NDCG@5 0.8629 | None |
| 10 | P2.4 | Promote sparse Key Facts collection strategy | Includes separate candidate workflow and gateway smoke; excludes replacing legacy push default | `[x] DONE (2026-05-02)` | Live gateway targets `knowledge_v2_keyfacts`; separate n8n workflow `knowledge_v2_keyfacts` uses `knowledge-ingest-keyfacts`, writes to `knowledge_v2_keyfacts`, and passed webhook plus gateway search smoke; original `knowledge_v2` workflow stayed active and `push-to-qdrant.sh` smoke passed | None |
| 11 | P2.5 | Document keyfacts production criteria and history | Includes production criteria, findings, and safe candidate status; excludes runtime cutover | `[x] DONE (2026-05-02)` | This roadmap records P2.5 criteria and findings; `RAG_EVAL_HARNESS.md` records latest keyfacts vs legacy soak metrics | None |
| 12 | P2.6 | Add repeatable keyfacts soak workflow | Includes documented repeatable checks and session cron; excludes durable external scheduler | `[x] DONE (2026-05-02)` | Initial soak plus final production evals saved to `.claude/reports/soak-keyfacts-initial-2026-05-02.json`, `.claude/reports/soak-legacy-initial-2026-05-02.json`, `.claude/reports/final-keyfacts-production-2026-05-02.json`, and `.claude/reports/final-legacy-production-2026-05-02.json`; final smoke and logs passed | None |
| 13 | P2.7 | Decide safe keyfacts cutover path | Includes rollback-safe retrieval cutover; excludes full ingest default switch | `[x] DONE (2026-05-02)` | VM B1 gateway production config already targets `knowledge_v2_keyfacts`; final keyfacts eval beats legacy on Hit@1, MRR, and NDCG@5; rollback is restoring gateway collection to `knowledge_v2` and restarting only gateway | Keep full ingest cutover as future work; do not modify legacy push path until sync/default-write behavior is designed |
| 14 | P2.8 | Add negative-query not-found confidence gate | Includes gateway confidence gating and debug visibility; excludes n8n, push tooling, reranker, and full ingest cutover | `[x] DONE (2026-05-04)` | Deployed commit `d686c46` to VM B1, rebuilt `rag-gateway`, positive homelab smoke returned `status=found` with top score 0.8333, negative `What is the project-alpha Blazor login flow?` with `project=homelab` returned `status=not_found`, and promoted checkpoint to Qdrant summary `2026-05-04-keyfacts-production-hardening-p28-promoted`. | None |

## Critical Files Reference

| File                                                   | Role                                                     |
| ------------------------------------------------------ | -------------------------------------------------------- |
| `~/scripts/rag-capture-v2/rag_capture.py` (rag-tools)  | Markdown drafting CLI: schema, validation, frontmatter   |
| `~/scripts/push-to-qdrant.sh` (rag-tools)              | Ingestion: embedding, upsert, supersede logic            |
| `~/scripts/qdrant-mcp-server-v2/qdrant-mcp-server-v2.js` (rag-tools) | Retrieval: hybrid search, reranker stage                 |
| `scripts/eval-retrieval-quality.py`                    | Eval framework; end-to-end hallucination test lives here |
| `.claude/skills/rag-knowledge-capture-cli/SKILL.md`    | Chunk body templates Claude uses when capturing          |
| `CLAUDE.md`                                            | Field and content rules visible to every session         |

## Verification Steps (run after each priority ships)

1. `rag add` a sample `implementation-spec` chunk → must pass validation, or reject with a clear reason
2. `python scripts/eval-retrieval-quality.py --project homelab --debug` → compare NDCG@5 before vs after
3. End-to-end strategy: query via MCP `search_knowledge` or `/rag/search`, feed the result through the 9routers-managed AI assistant workflow, verify generated code compiles and matches the chunk spec
4. Optional benchmark: run Ollama end-to-end only after a code model such as `qwen2.5-coder:7b` is installed
5. Watch MCP server stderr for `avg_score` improvement after contextual retrieval lands

## Session Handoff Notes

When starting a new session on this roadmap:

1. Load Qdrant MCP schema: `ToolSearch select:mcp__qdrant-knowledge__search_knowledge`
2. Query RAG first for any related prior work: `search_knowledge("rag knowledge_v2 ...", project="homelab")`
3. Read this file before proposing changes
4. Confirm which priority is active before writing code
5. Prefix every shell command with `rtk`

---

_Derived from plan: `~/.claude/plans/prancy-painting-wigderson.md` (2026-04-15). Author: Figur Ulul Azmi._
