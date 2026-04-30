# RAG `knowledge_v2` Roadmap

> **Status:** Active roadmap. Future Claude sessions: **read this file before proposing changes to the RAG pipeline** (`rag_capture.py`, `push-to-qdrant.sh`, `qdrant-mcp-server-v2.js`, `eval-retrieval-quality.py`). Do not deviate from the priorities below without explicit user approval.
> Status tracking standard: [`../reference/TRACKING_STATUS_STANDARD.md`](../reference/TRACKING_STATUS_STANDARD.md). Current source of truth is [Canonical Task Tracker](#canonical-task-tracker).

## Strategic Goal

Claude AI is used as a **reasoning + capture specialist only** for `knowledge_v2`. Code implementation is delegated to cheaper models (e.g., qwen2.5-coder via Ollama) that consume chunks from `knowledge_v2` via the MCP server.

**Success criterion:** chunks must be rich and precise enough that the implementer model does not hallucinate when writing code from them.

**Implication:** the bottleneck is **chunk content quality** and **retrieval precision**, not retrieval recall. The right chunk must reach the implementer's context window, and its content must be an executable specification, not prose.

## Current State (do not rebuild)

- Deterministic chunk ID (`{DOC_ID}-chunk-{N}`) → upsert-idempotent — `scripts/push-to-qdrant.sh:285`
- Hybrid search: dense (nomic-embed-text 768d COSINE) + sparse (djb2 BM25) + RRF fusion — `scripts/qdrant-mcp-server-v2/qdrant-mcp-server-v2.js:99`
- Query expansion for short queries (<8 words) — `qdrant-mcp-server-v2.js:20`
- Retry with rewrite when `avgScore < 0.6` — `qdrant-mcp-server-v2.js:227`
- Structured query logs (`rag_search`, `rag_retry`, `rag_not_found`) to stderr
- Eval framework with Hit@1/3/5, MRR, NDCG@5, 3 strategies, 7 test cases, regression detection — `scripts/eval-retrieval-quality.py`
- Warn-only validation (word count, em dash, Indonesian detection, Key Facts presence) — `scripts/rag-capture-v2/rag_capture.py:181`
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

- `scripts/rag-capture-v2/rag_capture.py:80` — add `"implementation-spec"` to `VALID_TYPES`
- `scripts/rag-capture-v2/rag_capture.py:181` `validate_content()` — enforce required sections for type `implementation-spec`/`feature`/`pattern`
- `.claude/skills/rag-knowledge-capture-cli/SKILL.md` — add body template for the new chunk_type
- `CLAUDE.md` field & content rules section — update to reflect new type and required sections

**Impact:** directly reduces hallucination; implementer model receives an explicit spec, not prose.

**P1.2. Contextual retrieval prepend before embedding** — **SHIPPED, needs deployment**

The prepend lives in the n8n workflow's `Validate & Clean` node, not in `push-to-qdrant.sh`. Bash script forwards raw payload; n8n computes `embed_content = "This chunk is from project X, type Y, topic Z, tagged ..., date ... Content: ..."` and feeds that to Ollama. Original `content` is stored untouched in the Qdrant payload and used for sparse vector + LLM consumption — the prepend never leaks to consumers.

**Files changed:**

- `scripts/n8n-workflows/ingest-knowledge-v2.json` — `Validate & Clean` node adds `embed_content` field; `Ollama: nomic-embed-text` node now reads `{{ $json.embed_content }}` instead of `{{ $json.content }}`

**Deployment steps (manual, one-time):**

1. In n8n UI at `http://192.168.18.199:5678`, open workflow `knowledge_v2`
2. Import the updated JSON (Workflow → Import from File → pick `scripts/n8n-workflows/ingest-knowledge-v2.json`) or paste the two changed nodes
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

**Files changed:** `scripts/rag-capture-v2/rag_capture.py` — `validate_content` (line 194), `cmd_add` (line 324), `cmd_pipe` (line 383).

**Verification (smoke tested):**

```bash
# Reject: short + no Key Facts
echo "short content" | rag add -p homelab -t debug --topic "x"   # exit 1

# Reject: feature without Target Files
cat body.md | rag add -p homelab -t feature --topic "x"          # exit 1
```

**P2.2. Reranker after RRF** — **SCAFFOLDED, disabled by default; blocked on infra**

LLM-as-reranker (no new infra path) was implemented and evaluated on VM B1 Ollama with `llama3.2:3b`:

- Aggregate NDCG@5: 0.9361 with rerank vs 0.9361 without — **zero measurable lift** because the current 5-query suite already saturates at Hit@1 = 1.00 / MRR = 1.00 under pure hybrid RRF.
- Hybrid latency: **~61s/query** vs 248ms without — 30× over the 2s plan budget.
- Parse reliability: **40% JSON parse-failure rate** (2 of 5 queries fell back to RRF order).

Decision: code shipped as scaffolding, but the default is **off** (`RERANK_ENABLED === "true"` to opt in). Kill switch verified. This preserves the integration point for the real fix below and keeps production on pure RRF — which today is already strong enough that reranker value is invisible on this eval set.

**Files changed (scaffolding):**

- `scripts/qdrant-mcp-server-v2/qdrant-mcp-server-v2.js` — `rerankWithLLM` helper, wired into both primary and retry search paths; gated on `RERANK_ENABLED` env var; emits `rag_rerank` and `rag_rerank_parse_error` stderr events.
- `scripts/eval-retrieval-quality.py` — `rerank_with_llm` helper, `--rerank / --rerank-model / --rerank-candidates` CLI flags.

**Real fix — promoted from P4 to active (P2.2-B):**
Deploy BGE-reranker-v2-m3 via a TEI (text-embeddings-inference) container on VM B1. Cross-encoder reranking gives proper semantic scoring at ~50ms/query instead of ~60s. The MCP scaffolding above already has the call-site — only `rerankWithLLM` needs to be replaced with a `rerankWithTEI` that hits TEI's `/rerank` endpoint.

**Also needed before P2.2-B delivers visible metric gains:**
P3.2's expanded eval set. Current 5 queries already produce perfect Hit@1 on hybrid RRF, so no reranker improvement is measurable. Grow to 30 queries with harder negatives before re-evaluating.

### P3 — Lifecycle & feedback

**P3.1. Supersede semantics**
Add frontmatter fields `supersedes: <old_chunk_id>` and `superseded_by`. When `push-to-qdrant.sh` sees `supersedes`, it PATCHes the old chunk's payload to `status: deprecated`. The MCP server's default `status == implemented` filter hides deprecated chunks automatically.

**Files:**

- `scripts/rag-capture-v2/rag_capture.py:222-236` — add `supersedes`/`superseded_by` to frontmatter output
- `scripts/push-to-qdrant.sh` — add deprecate-on-supersede logic during ingest

**P3.2. Expand eval set + implementation correctness test**

- Grow from 7 to 30 test queries, at least 15 of them `implementation-spec` type
- Add `--end-to-end` mode: retrieve top-5 → feed to a cheap implementer model (qwen2.5-coder via Ollama) → generate code → diff against expected snippet in the test fixture → report hallucination rate

**Files:** `scripts/eval-retrieval-quality.py` plus a new fixture file at `scripts/eval-fixtures/implementation-tests.json`.

**P3.3. Feedback loop: eval → chunk revision queue**
When eval flags NDCG < 0.6 for query X, append the chunk_id that should have ranked 1 to `~/scripts/.rag_revision_queue.md`. Surface the backlog in `rag status`.

**Files:** `scripts/eval-retrieval-quality.py`, `scripts/rag-capture-v2/rag_capture.py:438` `cmd_status`.

### P4 — Nice to have (skip until P1-P3 are done)

- Pre-commit hook validating frontmatter of `.claude/summaries/*.md` (n8n already validates; low marginal value)
- TTL-based auto-deprecate for chunks older than 6 months with zero retrieval hits
- Semantic eval (replace substring match with LLM-judge for gold signals)

## Canonical Task Tracker

| Order | ID | Task | Status | Evidence | Next action |
|---:|---|---|---|---|---|
| 1 | P1.1 | Enrich chunk schema for implementer models | `[x] DONE (2026-04-19)` | Shipped schema guidance for target files, interfaces, dependencies, contract, anti-patterns, verification, and key facts | None |
| 2 | P2.1 | Add hard-reject validation | `[x] DONE (2026-04-19)` | Validation shipped for required implementation-spec sections and content quality constraints | None |
| 3 | P1.2 | Deploy contextual retrieval prepend | `[x] DONE (2026-04-19)` | Hit@1 improved from 0.60 to 1.00 and MRR from 0.80 to 1.00 after contextual retrieval | None |
| 4 | P2.2 | Scaffold LLM-as-reranker | `[ ] DEFERRED` | Scaffolding exists, but reranker remains blocked on infra and disabled by default | Revisit after TEI plus BGE reranker is available |
| 5 | P3.2 | Expand eval set and implementation correctness test | `[x] DONE (2026-04-19)` | External brain plan marks P2-A and P2-B done for expanded eval plus end-to-end mode | None |
| 6 | P3.1 | Add supersede and deprecate semantics | `[x] DONE (2026-04-19)` | External brain plan marks P3-A and P3-B done for supersede frontmatter and deprecate-on-push | None |
| 7 | P2.2-B | Deploy TEI plus BGE reranker | `[!] BLOCKED` | TEI container not deployed; current eval suite saturates, so reranker benefit is not proven | Revisit after harder eval shows measurable reranker gap |
| 8 | P3.3 | Add eval to chunk revision queue feedback loop | `[ ] OPEN` | No canonical evidence yet that `~/scripts/.rag_revision_queue.md` integration is implemented | Implement after P4-C re-embed and post-baseline eval |

## Critical Files Reference

| File                                                   | Role                                                     |
| ------------------------------------------------------ | -------------------------------------------------------- |
| `scripts/rag-capture-v2/rag_capture.py`                | Markdown drafting CLI: schema, validation, frontmatter   |
| `scripts/push-to-qdrant.sh`                            | Ingestion: embedding, upsert, supersede logic            |
| `scripts/qdrant-mcp-server-v2/qdrant-mcp-server-v2.js` | Retrieval: hybrid search, reranker stage                 |
| `scripts/eval-retrieval-quality.py`                    | Eval framework; end-to-end hallucination test lives here |
| `.claude/skills/rag-knowledge-capture-cli/SKILL.md`    | Chunk body templates Claude uses when capturing          |
| `CLAUDE.md`                                            | Field and content rules visible to every session         |

## Verification Steps (run after each priority ships)

1. `rag add` a sample `implementation-spec` chunk → must pass validation, or reject with a clear reason
2. `python scripts/eval-retrieval-quality.py --project homelab --debug` → compare NDCG@5 before vs after
3. End-to-end: query via MCP `search_knowledge`, feed the result to the implementer model, verify generated code compiles and matches the chunk spec
4. Watch MCP server stderr for `avg_score` improvement after contextual retrieval lands

## Session Handoff Notes

When starting a new session on this roadmap:

1. Load Qdrant MCP schema: `ToolSearch select:mcp__qdrant-knowledge__search_knowledge`
2. Query RAG first for any related prior work: `search_knowledge("rag knowledge_v2 ...", project="homelab")`
3. Read this file before proposing changes
4. Confirm which priority is active before writing code
5. Prefix every shell command with `rtk`

---

_Derived from plan: `~/.claude/plans/prancy-painting-wigderson.md` (2026-04-15). Author: Figur Ulul Azmi._
