# RAG `knowledge_v2` Roadmap

> **Status:** Active roadmap. Future Claude sessions: **read this file before proposing changes to the RAG pipeline** (`rag_capture.py`, `push-to-qdrant.sh`, `qdrant-mcp-server-v2.js`, `eval-retrieval-quality.py`). Do not deviate from the priorities below without explicit user approval.

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

**P1.2. Contextual retrieval prepend before embedding**
In `push-to-qdrant.sh`, before posting to the embedding endpoint, prepend 50-100 tokens of document-level context:

```
This chunk is from project {project}, type {chunk_type}, topic "{topic}",
tagged {tags}. Session date {date}. Content: {original_chunk}
```

Embed the prepended version. **Store the original content in the payload** — never surface the prepend to the consumer LLM.

**Files to modify:**
- `scripts/push-to-qdrant.sh` around lines 181-190 (after frontmatter extraction, before the Ollama embed POST)
- No changes needed in `qdrant-mcp-server-v2.js` — retrieval still returns the original `content` payload

**Impact:** 35-49% retrieval failure reduction (Anthropic benchmark). The right chunk reaches the implementer more often.

### P2 — Quality gates & precision

**P2.1. Upgrade `validate_content()` from warn to hard reject**
- Reject when word count < 100 or > 400
- Reject when `### Key Facts` is absent
- Reject when em dash is present (no longer a warn)
- Reject when type is `implementation-spec`/`feature`/`pattern` and `### Target Files` is absent
- Exit code 1 so `rag add` fails loudly and Claude corrects it

**Files:** `scripts/rag-capture-v2/rag_capture.py:181-194` and `rag_capture.py:283-285` (convert `print(w)` to `sys.exit(1)` for hard errors; keep soft ones as warnings).

**P2.2. Reranker after RRF**
Rerank RRF top-20 to top-5 with BGE-reranker-v2-m3 (lightweight cross-encoder). If Ollama does not support cross-encoders, use LLM-as-reranker with a small model (e.g., Qwen2.5-3B) and a relevance-scoring prompt.

**Files:** `scripts/qdrant-mcp-server-v2/qdrant-mcp-server-v2.js` — add a rerank stage after the fusion call at line 99.

**Impact:** positions 1-3 become much more precise; implementer context window stays clean.

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

## Recommended Execution Order

1. P1.1 chunk schema enrichment (~1-2 h) — improves quality of all new chunks; existing chunks remain valid
2. P2.1 hard-reject validation (~30 min) — cheap; blocks bad chunks at the gate
3. P1.2 contextual retrieval (~1-2 h) — requires re-embedding existing chunks, but the push script is already upsert-safe
4. P2.2 reranker (~2-3 h) — depends on reranker choice
5. P3.1 supersede (~1 h)
6. P3.2 and P3.3 eval expansion + feedback (~3-4 h)

**Total: ~10 hours for full P1-P3. P1 alone (~3 hours) delivers about 70% of the impact against the strategic goal.**

## Critical Files Reference

| File | Role |
|------|------|
| `scripts/rag-capture-v2/rag_capture.py` | Markdown drafting CLI: schema, validation, frontmatter |
| `scripts/push-to-qdrant.sh` | Ingestion: embedding, upsert, supersede logic |
| `scripts/qdrant-mcp-server-v2/qdrant-mcp-server-v2.js` | Retrieval: hybrid search, reranker stage |
| `scripts/eval-retrieval-quality.py` | Eval framework; end-to-end hallucination test lives here |
| `.claude/skills/rag-knowledge-capture-cli/SKILL.md` | Chunk body templates Claude uses when capturing |
| `CLAUDE.md` | Field and content rules visible to every session |

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

*Derived from plan: `~/.claude/plans/prancy-painting-wigderson.md` (2026-04-15). Author: Figur Ulul Azmi.*
