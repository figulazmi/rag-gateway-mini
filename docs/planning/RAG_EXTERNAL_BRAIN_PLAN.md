# RAG External Brain — Improvement Plan

# For: .NET & Python Software Engineer daily work

> **How to track progress:** Follow [`../reference/TRACKING_STATUS_STANDARD.md`](../reference/TRACKING_STATUS_STANDARD.md).
> Update the canonical task table row only. Each row must include Status, Evidence, and Next action.
> Avoid duplicate status checklists outside the canonical table; summaries should reference task IDs only.
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

| #    | Task                                                                                                                                                                                                   | File(s)                                                              | Status                  |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------- | ----------------------- |
| P1-A | Change heredoc terminator `CONTENT` → `RAGBODY_EOF` in all `rag add` examples in CLAUDE.md. Prevents body truncation when chunk content contains the literal word `CONTENT` on its own line.           | `CLAUDE.md` (auto-capture section)                                   | `[x] DONE (2026-04-19)` |
| P1-B | Auto-push inside `cmd_merge()`: after writing `.claude/summaries/*.md`, immediately attempt `push-to-qdrant.sh`. On network fail, append file path to `~/.rag_push_queue` instead of silently exiting. | `~/scripts/rag-capture-v2/rag_capture.py` (rag-tools)                              | `[x] DONE (2026-04-19)` |
| P1-C | New command `rag push-pending`: reads `~/.rag_push_queue`, retries each file with exponential backoff (2s, 4s, 8s), removes entry on 2xx.                                                              | `~/scripts/rag-capture-v2/rag_capture.py`, `~/scripts/push-to-qdrant.sh` (rag-tools) | `[x] DONE (2026-04-19)` |
| P1-D | Verify step after push: query Qdrant `GET /collections/knowledge_v2` point count before and after ingest; log delta to stderr. Non-zero delta = verified indexed. Zero delta on new chunk = warning.   | `~/scripts/push-to-qdrant.sh` (rag-tools)                                          | `[x] DONE (2026-04-19)` |

**Acceptance:** Run `rag merge` on a test chunk → summary auto-pushed → Qdrant point count increments → `~/.rag_push_queue` only populated on actual network failure.

---

## Phase 2 — Eval Expansion (make quality measurable)

**Why next:** Current 7-query eval suite saturates at Hit@1=1.00, MRR=1.00 — no improvement
(reranker, contextual retrieval tuning) can be measured. Must grow the suite first.

| #    | Task                                                                                                                                                                                            | File(s)                                                                                      | Status                  |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ----------------------- |
| P2-A | Grow eval set from 7 to 30 queries. At least 15 must be `implementation-spec` type. Cover .NET 9 and Python domains. Add harder negatives — queries where the wrong chunk is tempting.          | `~/scripts/rag-infra/eval-retrieval-quality.py`, `scripts/eval-fixtures/implementation-tests.json` (new) | `[x] DONE (2026-04-19)` |
| P2-B | Add `--end-to-end` mode to eval: retrieve top-5 chunks → feed to `qwen2.5-coder` via Ollama → generate code → diff against expected snippet in fixture → report hallucination rate as a metric. | `~/scripts/rag-infra/eval-retrieval-quality.py`                                                          | `[x] DONE (2026-04-19)` |

**Acceptance:** `python ~/scripts/rag-infra/eval-retrieval-quality.py --project homelab --debug` runs 30 queries; `--end-to-end` flag generates code and reports hallucination % per query.

---

## Phase 3 — Supersede Semantics (keep knowledge fresh)

**Why:** Without deprecation, old `.NET 8` decisions sit alongside `.NET 9` ones. Conflicting
chunks confuse retrievers and implementers. MCP server already filters `status != implemented`
by default — just need the pipeline to set `status: deprecated` on old chunks.

| #    | Task                                                                                                                                                     | File(s)                                     | Status                  |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- | ----------------------- |
| P3-A | Add `supersedes` and `superseded_by` frontmatter fields to `rag_capture.py`. Validation: `supersedes` value must be a valid existing chunk ID format.    | `~/scripts/rag-capture-v2/rag_capture.py:222` (rag-tools) | `[x] DONE (2026-04-19)` |
| P3-B | In `push-to-qdrant.sh`: when `supersedes` field is present, PATCH the old chunk's Qdrant payload to `status: deprecated` before upserting the new chunk. | `~/scripts/push-to-qdrant.sh` (rag-tools)                 | `[x] DONE (2026-04-19)` |

**Acceptance:** Capture a chunk with `supersedes: <old-id>` → push → verify old chunk in Qdrant has `status: deprecated` → MCP search no longer returns it.

---

## Phase 4 — .NET & Python Coverage Strategy (ongoing)

**Why:** Infrastructure is solid. The gap is _what knowledge exists_ in Qdrant.
Systematic capture for daily .NET and Python work turns this into a real external brain.

### Capture habits to establish

| Work pattern                | Chunk type            | Minimum fields                                                  | Project tag          |
| --------------------------- | --------------------- | --------------------------------------------------------------- | -------------------- |
| .NET feature implemented    | `implementation-spec` | Target Files, Interfaces, Contract, Anti-Patterns, Verification | `dotnet`             |
| .NET architecture decision  | `decision`            | Problem, Options considered, Chosen, Rationale                  | `dotnet`             |
| Python script/tool built    | `feature`             | Target Files, what it does, how to invoke                       | `python`             |
| Bug fixed (either language) | `debug`               | Error message, root cause, fix applied                          | `dotnet` or `python` |
| Deployment runbook          | `runbook`             | Numbered steps, expected output per step                        | `homelab`            |
| Reusable pattern found      | `pattern`             | Target Files, code snippet, when to use / not use               | `dotnet` or `python` |

### Setup tasks

| #    | Task                                                                                                                                                                                                     | File(s)                                                   | Status                                                                                                                                                                                              |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P4-A | Add `.NET` and `Python` tag conventions to CLAUDE.md field rules. Require one of `dotnet`, `python`, `homelab` as the first tag on every chunk.                                                          | `CLAUDE.md` (field rules section)                         | `[x] DONE (2026-04-19)`                                                                                                                                                                             |
| P4-B | Deploy contextual retrieval prepend to n8n (P1.2 is shipped in code but not deployed). Import updated `ingest-knowledge-v2.json` into n8n UI at `http://192.168.18.199:5678`. Smoke test with one chunk. | `~/scripts/n8n-workflows/ingest-knowledge-v2.json` (rag-tools, imported via n8n UI) | `[x] DONE (2026-04-19)` — embed_content verified in workflow vm7AIcsMvjzstjkb; snap Ollama disabled, Docker Ollama recreated via docker-compose.stage2.yml; pipeline verified 200→201 Qdrant points |
| P4-C | Re-embed existing corpus after n8n deploy: loop over `.claude/summaries/*.md` and re-push all files (upsert is idempotent by deterministic ID). Run eval before/after to confirm NDCG@5 improvement.     | `bash ~/scripts/push-to-qdrant.sh`                        | `[x] DONE (2026-05-02) — re-pushed 36 homelab summaries and added Python argparse/dataclass pattern chunks; final eval shows dense-only improved to Hit@1 0.8333, MRR 0.9028, NDCG@5 0.9108; hybrid recall recovered but top-rank remains limited by sparse/RRF noise` |

**Acceptance (P4-B/C):** `python ~/scripts/rag-infra/eval-retrieval-quality.py` must improve quality without hiding top-rank regressions. Final 2026-05-02 result: dense-only improved beyond baseline, while hybrid still has sparse/RRF rank noise. Next acceptance should compare live dense-only vs hybrid before more reranker work.

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

**Deferred until:** dense-only and sparse-text redesign have been measured. Final 2026-05-02 eval shows dense-only beats hybrid on top-rank quality, so reranker is not the next bottleneck.

| #    | Task                                                                                                                            | File(s)                                                | Status                              |
| ---- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ | ----------------------------------- |
| P5-A | Deploy BGE-reranker-v2-m3 via TEI container on VM B1. Add to `docker-compose.yml` on VM B1 (not in this repo).                  | VM B1 infra                                            | `[ ] DEFERRED — first fix sparse/RRF noise and test dense-only` |
| P5-B | Replace `rerankWithLLM` in MCP server with `rerankWithTEI` hitting TEI's `/rerank` endpoint. Set `RERANK_ENABLED=true` env var. | `~/scripts/qdrant-mcp-server-v2/qdrant-mcp-server-v2.js` (rag-tools) | `[ ] DEFERRED — needs P5-A plus evidence of reranker gap` |
| P5-C | Benchmark: rerun eval with `--rerank` flag; confirm NDCG@5 improves and latency stays under 2s budget.                          | `~/scripts/rag-infra/eval-retrieval-quality.py`                    | `[ ] DEFERRED — after dense-only and sparse redesign baselines` |

---

## Quick Status Overview

```text
Done: P1-A, P1-B, P1-C, P1-D, P2-A, P2-B, P3-A, P3-B, P4-A, P4-B, P4-C, P6-A, P6-B
Open: none
Deferred: P5
Next: none
```

---

## Canonical Task Tracker

This table is the canonical execution tracker and recommended execution order. Do not maintain a separate checklist with different status values.

| Order | ID | Task | Status | Evidence | Next action |
|---:|---|---|---|---|---|
| 1 | P4-B | Deploy contextual retrieval to n8n | `[x] DONE (2026-04-19)` | `embed_content` verified in n8n workflow; pipeline verified 200 to 201 Qdrant points | None |
| 2 | P1-A | Fix heredoc terminator | `[x] DONE (2026-04-19)` | `rag add` examples use `RAGBODY_EOF` terminator | None |
| 3 | P1-B | Auto-push in `cmd_merge()` | `[x] DONE (2026-04-19)` | `rag merge` writes summary and immediately calls `push-to-qdrant.sh` | None |
| 4 | P1-C | Push queue and retry | `[x] DONE (2026-04-19)` | `rag push-pending` exists and retries queued failed pushes | None |
| 5 | P1-D | Verify point count after push | `[x] DONE (2026-04-19)` | `push-to-qdrant.sh` logs Qdrant point count before and after push | None |
| 6 | P2-A | Expand eval set to 30 queries | `[x] DONE (2026-04-19)` | `eval-retrieval-quality.py` supports expanded fixtures and debug run | None |
| 7 | P2-B | Add end-to-end hallucination test | `[x] DONE (2026-04-19)` | `--end-to-end` mode retrieves chunks, calls qwen2.5-coder, and reports hallucination metric | None |
| 8 | P3-A | Add supersede frontmatter | `[x] DONE (2026-04-19)` | `rag_capture.py` supports `--supersedes` / `--superseded-by`; CLI test verified `supersedes: old-chunk-001` frontmatter is written | None |
| 9 | P3-B | Deprecate old chunk on push | `[x] DONE (2026-04-19)` | `push-to-qdrant.sh` patches superseded chunk status to `deprecated` | None |
| 10 | P4-A | Add tag conventions to CLAUDE.md | `[x] DONE (2026-04-19)` | First tag convention requires `dotnet`, `python`, or `homelab` | None |
| 11 | P4-C | Re-embed corpus after n8n deploy | `[x] DONE (2026-05-02)` | Final eval after Python pattern chunks and selective chunk_type filtering: dense-only Hit@1 0.8333, MRR 0.9028, NDCG@5 0.9108; hybrid Hit@1 0.6111, Hit@3 0.9444, Hit@5 0.9444, MRR 0.7685, NDCG@5 0.8629 | Use results to drive dense-only A/B and sparse-text redesign |
| 12 | P5 | TEI plus BGE reranker | `[ ] DEFERRED` | Reranker scaffold exists, but final eval points to sparse/RRF noise rather than reranker absence | Revisit only after dense-only and sparse-text redesign still leave a top-K ordering gap |
| 13 | P6-A | Dense-only and sparse-text A/B | `[x] DONE (2026-05-02)` | `knowledge_v2_keyfacts` built from `knowledge_v2` with 373/373 point parity and smoke eval improved hybrid to Hit@1 0.8889, MRR 0.9167, NDCG@5 0.9547 | Promote topic + Key Facts sparse strategy to live collection and ingestion paths |
| 14 | P6-B | Promote Key Facts sparse strategy live | `[x] DONE (2026-05-02)` | Live gateway targets `knowledge_v2_keyfacts`; separate n8n workflow `knowledge_v2_keyfacts` uses webhook `knowledge-ingest-keyfacts`, writes to `knowledge_v2_keyfacts`, and passed webhook plus gateway search smoke; original `knowledge_v2` workflow stayed active and `push-to-qdrant.sh` smoke passed | None |

---

## Status Tracking Standard

Use this standard for future planning docs to prevent drift between phase tables, quick summaries, and execution order lists.

### Canonical table format

Every plan should have exactly one canonical task table:

| Order | ID | Task | Status | Evidence | Next action |
|---:|---|---|---|---|---|
| 1 | P1-A | Short imperative task name | `[ ] OPEN` | Observable proof required to mark done | Immediate next command or decision |

### Allowed status values

| Status | Meaning | Required evidence |
|---|---|---|
| `[ ] OPEN` | Not started | None |
| `[~] IN PROGRESS` | Started but not verified | Link to branch, file, command, or blocker |
| `[x] DONE (YYYY-MM-DD)` | Implemented and verified | Command output, test result, deployed service, or doc link |
| `[!] BLOCKED` | Cannot proceed until dependency changes | Name the dependency and owner/system |
| `[ ] DEFERRED` | Valid task but intentionally postponed | State the revisit condition |
| `[x] OBSOLETE (YYYY-MM-DD)` | No longer needed | State what replaced it |

### Rules

1. Keep status in one place only: the canonical table.
2. Quick Status sections must summarize IDs only, not duplicate per-task status text.
3. A task cannot be marked DONE without evidence.
4. If evidence is external, write the verification command or the exact observed result.
5. When implementation and verification are separate, keep the task IN PROGRESS until verification passes.
6. If a blocker becomes stale, update the Evidence and Next action immediately.
7. After every completed implementation session, update docs in the same commit or same working set as the code/script change.
8. Prefer task IDs that never change, even if the title changes.

### Recommended quick summary format

```text
Done: P1-A, P1-B, P1-C
Open: <current open item>
Deferred: <blocked or intentionally postponed item>
Next: <single next action>
```

Do not repeat detailed status in the quick summary. The canonical table remains the source of truth.

---

_Created: 2026-04-19 | Author: Figur Ulul Azmi | Based on: RAG_V2_ROADMAP.md + RAG_CAPTURE_PIPELINE_GAPS.md_
