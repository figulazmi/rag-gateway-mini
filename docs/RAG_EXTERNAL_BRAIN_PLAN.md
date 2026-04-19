# RAG External Brain — Improvement Plan
# For: .NET & Python Software Engineer daily work

> **How to track progress:** When a task is done, change `[ ] OPEN` to `[x] DONE (YYYY-MM-DD)`.
> Work top-to-bottom — each phase unblocks the next.

---

## Strategic Goal

Build a RAG knowledge base precise enough that implementer models (qwen2.5-coder, etc.)
can write correct .NET and Python code from retrieved chunks — without hallucination.
Every captured chunk must reach Qdrant reliably, remain fresh, and be measurably retrievable.

---

## Phase 1 — Reliability (fix silent knowledge loss)

**Why first:** Even if capture and retrieval are perfect, knowledge that never reaches Qdrant
is useless. Fix the pipeline gaps before adding more knowledge.

| # | Task | File(s) | Status |
|---|------|---------|--------|
| P1-A | Change heredoc terminator `CONTENT` → `RAGBODY_EOF` in all `rag add` examples in CLAUDE.md. Prevents body truncation when chunk content contains the literal word `CONTENT` on its own line. | `CLAUDE.md` (auto-capture section) | `[x] DONE (2026-04-19)` |
| P1-B | Auto-push inside `cmd_merge()`: after writing `.claude/summaries/*.md`, immediately attempt `push-to-qdrant.sh`. On network fail, append file path to `~/.rag_push_queue` instead of silently exiting. | `scripts/rag-capture-v2/rag_capture.py` | `[x] DONE (2026-04-19)` |
| P1-C | New command `rag push-pending`: reads `~/.rag_push_queue`, retries each file with exponential backoff (2s, 4s, 8s), removes entry on 2xx. | `scripts/rag-capture-v2/rag_capture.py`, `scripts/push-to-qdrant.sh` | `[x] DONE (2026-04-19)` |
| P1-D | Verify step after push: query Qdrant `GET /collections/knowledge_v2` point count before and after ingest; log delta to stderr. Non-zero delta = verified indexed. Zero delta on new chunk = warning. | `scripts/push-to-qdrant.sh` | `[x] DONE (2026-04-19)` |

**Acceptance:** Run `rag merge` on a test chunk → summary auto-pushed → Qdrant point count increments → `~/.rag_push_queue` only populated on actual network failure.

---

## Phase 2 — Eval Expansion (make quality measurable)

**Why next:** Current 7-query eval suite saturates at Hit@1=1.00, MRR=1.00 — no improvement
(reranker, contextual retrieval tuning) can be measured. Must grow the suite first.

| # | Task | File(s) | Status |
|---|------|---------|--------|
| P2-A | Grow eval set from 7 to 30 queries. At least 15 must be `implementation-spec` type. Cover .NET 9 and Python domains. Add harder negatives — queries where the wrong chunk is tempting. | `scripts/eval-retrieval-quality.py`, `scripts/eval-fixtures/implementation-tests.json` (new) | `[x] DONE (2026-04-19)` |
| P2-B | Add `--end-to-end` mode to eval: retrieve top-5 chunks → feed to `qwen2.5-coder` via Ollama → generate code → diff against expected snippet in fixture → report hallucination rate as a metric. | `scripts/eval-retrieval-quality.py` | `[x] DONE (2026-04-19)` |

**Acceptance:** `python scripts/eval-retrieval-quality.py --project homelab --debug` runs 30 queries; `--end-to-end` flag generates code and reports hallucination % per query.

---

## Phase 3 — Supersede Semantics (keep knowledge fresh)

**Why:** Without deprecation, old `.NET 8` decisions sit alongside `.NET 9` ones. Conflicting
chunks confuse retrievers and implementers. MCP server already filters `status != implemented`
by default — just need the pipeline to set `status: deprecated` on old chunks.

| # | Task | File(s) | Status |
|---|------|---------|--------|
| P3-A | Add `supersedes` and `superseded_by` frontmatter fields to `rag_capture.py`. Validation: `supersedes` value must be a valid existing chunk ID format. | `scripts/rag-capture-v2/rag_capture.py:222` | `[x] DONE (2026-04-19)` |
| P3-B | In `push-to-qdrant.sh`: when `supersedes` field is present, PATCH the old chunk's Qdrant payload to `status: deprecated` before upserting the new chunk. | `scripts/push-to-qdrant.sh` | `[x] DONE (2026-04-19)` |

**Acceptance:** Capture a chunk with `supersedes: <old-id>` → push → verify old chunk in Qdrant has `status: deprecated` → MCP search no longer returns it.

---

## Phase 4 — .NET & Python Coverage Strategy (ongoing)

**Why:** Infrastructure is solid. The gap is *what knowledge exists* in Qdrant.
Systematic capture for daily .NET and Python work turns this into a real external brain.

### Capture habits to establish

| Work pattern | Chunk type | Minimum fields | Project tag |
|-------------|-----------|----------------|-------------|
| .NET feature implemented | `implementation-spec` | Target Files, Interfaces, Contract, Anti-Patterns, Verification | `dotnet` |
| .NET architecture decision | `decision` | Problem, Options considered, Chosen, Rationale | `dotnet` |
| Python script/tool built | `feature` | Target Files, what it does, how to invoke | `python` |
| Bug fixed (either language) | `debug` | Error message, root cause, fix applied | `dotnet` or `python` |
| Deployment runbook | `runbook` | Numbered steps, expected output per step | `homelab` |
| Reusable pattern found | `pattern` | Target Files, code snippet, when to use / not use | `dotnet` or `python` |

### Setup tasks

| # | Task | File(s) | Status |
|---|------|---------|--------|
| P4-A | Add `.NET` and `Python` tag conventions to CLAUDE.md field rules. Require one of `dotnet`, `python`, `homelab` as the first tag on every chunk. | `CLAUDE.md` (field rules section) | `[x] DONE (2026-04-19)` |
| P4-B | Deploy contextual retrieval prepend to n8n (P1.2 is shipped in code but not deployed). Import updated `ingest-knowledge-v2.json` into n8n UI at `http://192.168.18.169:5678`. Smoke test with one chunk. | `scripts/n8n-workflows/ingest-knowledge-v2.json` (n8n UI) | `[x] DONE (2026-04-19)` — embed_content verified in workflow vm7AIcsMvjzstjkb; snap Ollama disabled, Docker Ollama recreated via docker-compose.stage2.yml; pipeline verified 200→201 Qdrant points |
| P4-C | Re-embed existing corpus after n8n deploy: loop over `.claude/summaries/*.md` and re-push all files (upsert is idempotent by deterministic ID). Run eval before/after to confirm NDCG@5 improvement. | `bash ~/scripts/push-to-qdrant.sh` | `[ ] OPEN — no local summaries yet; run command below when summaries accumulate` |

**Acceptance (P4-B/C):** `python scripts/eval-retrieval-quality.py` NDCG@5 improves vs pre-deploy baseline. MCP server stderr shows higher `avg_score` on typical queries.

**P4-C re-embed command (run when summaries exist):**
```bash
for f in ~/.claude/summaries/*.md; do
  echo "Pushing $f..."
  bash ~/scripts/push-to-qdrant.sh "$f"
  sleep 2
done
```

---

## Phase 5 — TEI + BGE-Reranker (P2.2-B)

**Blocked until:** Phase 2 eval expansion shows measurable gap (current suite already saturates).

| # | Task | File(s) | Status |
|---|------|---------|--------|
| P5-A | Deploy BGE-reranker-v2-m3 via TEI container on VM B1. Add to `docker-compose.yml` on VM B1 (not in this repo). | VM B1 infra | `[ ] BLOCKED — needs Phase 2 first` |
| P5-B | Replace `rerankWithLLM` in MCP server with `rerankWithTEI` hitting TEI's `/rerank` endpoint. Set `RERANK_ENABLED=true` env var. | `scripts/qdrant-mcp-server-v2/qdrant-mcp-server-v2.js` | `[ ] BLOCKED — needs P5-A` |
| P5-C | Benchmark: rerun eval with `--rerank` flag; confirm NDCG@5 improves and latency stays under 2s budget. | `scripts/eval-retrieval-quality.py` | `[ ] BLOCKED — needs P5-A, P5-B` |

---

## Quick Status Overview

```
Phase 1 — Reliability        [x] P1-A  [x] P1-B  [x] P1-C  [x] P1-D
Phase 2 — Eval Expansion     [x] P2-A  [x] P2-B
Phase 3 — Supersede          [x] P3-A  [x] P3-B
Phase 4 — Coverage/Deploy    [x] P4-A  [x] P4-B  [ ] P4-C
Phase 5 — TEI Reranker       [BLOCKED] [BLOCKED] [BLOCKED]
```

---

## Recommended Execution Order

```
1. [x] P4-B  Deploy contextual retrieval to n8n  — DONE 2026-04-19
2. [x] P1-A  Fix heredoc terminator         — DONE 2026-04-19
3. P1-B  Auto-push in cmd_merge             (~1h, eliminates biggest SPOF)
4. P1-C  Push queue + retry                 (~1h, robustness)
5. P1-D  Verify step                        (~30 min, observability)
6. P2-A  Expand eval set to 30 queries      (~1.5h, unblocks everything downstream)
7. P2-B  End-to-end hallucination test      (~1h)
8. P3-A  Supersede frontmatter              (~30 min)
9. P3-B  Deprecate on push                  (~30 min)
10. P4-A Tag conventions in CLAUDE.md       (~10 min)
11. P4-C Re-embed corpus after n8n deploy   (~20 min, batch job)
12. P5   TEI reranker                       (after P2 confirms gap exists)
```

---

*Created: 2026-04-19 | Author: Figur Ulul Azmi | Based on: RAG_V2_ROADMAP.md + RAG_CAPTURE_PIPELINE_GAPS.md*
