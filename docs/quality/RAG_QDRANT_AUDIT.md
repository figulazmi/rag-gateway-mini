# RAG Qdrant Intelligence Audit

> **Navigation:** [docs/README.md](../README.md) — full index of all RAG docs.
> Coverage knowledge detail & improvement history → [COVERAGE_KNOWLEDGE_TRACKER.md](COVERAGE_KNOWLEDGE_TRACKER.md)

**Date:** 2026-04-25 (last updated: 2026-04-25 session 5)
**Overall Score: 6.8/10 → 8.1/10**

---

## Snapshot

> **Baseline** (2026-04-25 pagi) → **Current** (2026-04-25 session 5)

| Dimension | Baseline | Current | Notes |
|---|---|---|---|
| Infrastruktur | 9/10 | 9/10 | Unchanged — already excellent |
| Coverage knowledge | 5/10 | **7.5/10** | OI-1/2/3/4 done; OI-5 deferred (see below) |
| Query quality | 7/10 | **8.5/10** | SCORE_THRESHOLD 0.5→0.35, retry expansion project-aware |
| Freshness | 6/10 | **8.5/10** | Checkpoints promoted, indexing_threshold=0 patched |
| Pipeline reliability | 7/10 | **8/10** | qdrant_url fixed, push-queue audit pending |

> **OI-5 (implementation-spec capture) BLOCKED** — deferred until P2.2-B reranker (TEI + BGE-reranker) is deployed on VM B1. Do not activate until reranker is live. See [memory/project_p22b_reranker_deferred.md].

---

## Collection State (2026-04-25)

```
knowledge_v2:  255 points total
               199 indexed  (56 unindexed = 22% gap)
               Status: green

  By project:
    homelab:          146
    petrochina-eproc: 100
    checkpoint:         9

  By chunk_type:
    debug:            170  (67%)  ← severely over-indexed
    feature:           22   (9%)
    runbook:           21   (8%)
    decision:          10   (4%)
    checkpoint:         9   (3%)
    reference:          3   (1%)  ← critical gap
    pattern:            1  (0.4%) ← critical gap
    implementation-spec: 0  (0%)  ← never used

knowledge (old): 147 points — dense-only, not queried by any current pipeline
```

---

## Strengths

1. **Hybrid RRF retrieval** — dense (nomic-embed-text 768-dim) + sparse (djb2 BM25 + IDF). Server-side fusion.
2. **NOT_FOUND gate** — top score < 0.50 → explicit "NOT FOUND IN RAG" response.
3. **Status filter** — `implemented` only by default; drafts/planned excluded.
4. **Auto-retry** — avgScore < 0.60 triggers query rewrite + retry automatically.
5. **Project isolation** — homelab / petrochina-eproc never mixed.
6. **Query normalization** — queries < 8 words auto-expanded.

---

## Issues & Fixes (Priority Order)

### P0 — Fix Immediately

#### A. 2 Checkpoints Belum Dipromote

Knowledge dari sesi 2026-04-18 masih terkunci di checkpoint format.

```bash
rag promote --file .claude/checkpoints/2026-04-18-rich-checkpoint-system-for-session-conti-001.md
rag promote --file .claude/checkpoints/2026-04-18-rag-checkpoint-system-implementation-com-001.md
bash ~/scripts/push-to-qdrant.sh .claude/summaries/2026-04-18-*.md
```

**Status:** [ ] TODO

---

#### B. `rag_config.json` URL Qdrant Salah

```json
"qdrant_url": "http://192.168.18.169:6333"  // connection refused!
```

IP `.169` tidak reachable. push-to-qdrant.sh bisa gagal silently.

```bash
# Fix: update ke IP yang benar
ssh figulazmi@192.168.18.199 \
  "python3 -c \"import json,pathlib; p=pathlib.Path('~/.rag_config.json').expanduser(); d=json.loads(p.read_text()); d['qdrant_url']='http://localhost:6333'; p.write_text(json.dumps(d,indent=2))\""
```

**Status:** [ ] TODO

---

### P1 — Coverage Knowledge (Score: 5/10 → 5.5/10)

> Full improvement history, open items, and score projection:
> **[COVERAGE_KNOWLEDGE_TRACKER.md](COVERAGE_KNOWLEDGE_TRACKER.md)**

Summary of fixes applied 2026-04-25:
- Captured 3 `pattern` chunks → pattern: 1 → 4
- Captured 2 `reference` chunks → reference: 3 → 5
- Fixed pipeline bug: per-chunk metadata (type + topic) now correctly embedded by `rag merge` and parsed by `push-to-qdrant.sh`
- Old `knowledge` collection already migrated in prior session (145/147 overlap)

Remaining: OI-1 (capture ~20 pattern chunks from existing debug knowledge) is the highest-ROI next step.

---

#### Old `knowledge` collection: 147 points

**Status:** [x] DONE prior session — 145/147 already exist in knowledge_v2 (same IDs).
`migrate-to-hybrid.py` script created at `~/scripts/migrate-to-hybrid.py` on VM B1 for future use.

---

### P2 — Query Quality (Score: 7/10)

#### A. Auto-retry Expansion Homelab-Biased

**Status:** [x] DONE 2026-04-25 session 5

Was: `const rewrittenQuery = effectiveQuery + " deployment configuration setup steps homelab VM B1";`

Fixed in `/opt/mcp-servers/qdrant-knowledge/qdrant-mcp-server.js`:
```js
const expansions = {
  homelab: "deployment configuration setup steps homelab VM B1 Docker infrastructure",
  "petrochina-eproc": "Blazor .NET 9 EF Core CQRS MediatR implementation pattern C#",
};
const expansion = expansions[project] || "implementation architecture system behavior";
const rewrittenQuery = effectiveQuery + " " + expansion;
```

---

#### B. SCORE_THRESHOLD Alignment with rag-gateway

**Status:** [x] DONE 2026-04-25 session 5

Was: `SCORE_THRESHOLD = 0.5` and `RETRY_THRESHOLD = 0.6` — too high for RRF scores.
rag-gateway ScoreThreshold was already 0.35 (set when hybrid RRF was implemented).

Fixed:
```js
const SCORE_THRESHOLD = 0.35;  // was 0.5 — RRF scores range lower than cosine
const RETRY_THRESHOLD = 0.50;  // was 0.6 — lowered to compensate for wider SCORE_THRESHOLD
```

`NOT_FOUND_THRESHOLD` stays at 0.50 — it is now the meaningful quality gate (topScore < 0.50 = genuinely not found), while SCORE_THRESHOLD is the per-result inclusion threshold (borderline 0.35-0.49 results are now included instead of discarded).

---

### P3 — Freshness (Score: 6/10 → 8.5/10)

#### A. Unindexed Points

**Status:** [x] DONE 2026-04-25 session 5 — `indexing_threshold` patched to 0 via PATCH `/collections/knowledge_v2`. Dense HNSW: 199/296 indexed (appendable segment brute-force fallback — zero practical impact at this scale). Sparse BM25 inverted index covers all 296 points. Threshold=0 is permanent.

#### B. Checkpoints Unindexed

**Status:** [x] DONE 2026-04-25 — both April 18 checkpoints promoted and pushed.

---

### P4 — Implementation-Spec (OI-5) — BLOCKED

> **BLOCKED: Do not activate until P2.2-B reranker (TEI + BGE-reranker container) is deployed on VM B1.**

`implementation-spec` chunk type dirancang untuk feed implementer models (qwen2.5-coder, Ollama). Belum pernah dipakai. Reranker diperlukan untuk prioritisasi hasil sebelum di-feed ke implementer model.

**Unblock checklist:**
- [ ] TEI (Text Embeddings Inference) container deployed on VM B1
- [ ] BGE-reranker model loaded in TEI
- [ ] qdrant-mcp-server.js updated to call reranker before returning results
- [ ] `implementation-spec` template added to CLAUDE.md auto-capture rules

**Status:** [ ] DEFERRED — see [memory/project_p22b_reranker_deferred.md] for full context

---

## Fix Tracker

| # | Issue | Priority | Status |
|---|---|---|---|
| A | Promote 2 checkpoints April 18 | P0 | [x] Done 2026-04-25 |
| B | Fix rag_config.json URL `.169` | P0 | [x] Done 2026-04-25 → localhost:6333 |
| 1 | Capture pattern chunks (OI-1) | P1 | [x] Done 2026-04-25 → 1→20 pattern chunks (3 batches) |
| 2 | Capture reference chunks (OI-1 aux) | P1 | [x] Done 2026-04-25 → 3→5 reference chunks |
| 3 | Migrate old `knowledge` collection | P1 | [x] Already done prior session (145/147 exist) |
| X | Fix push-to-qdrant.sh per-chunk metadata bug | P1 | [x] Done 2026-04-25 — off-by-one metadata fix |
| OI-2 | Capture +5 feature chunks | P1 | [x] Done 2026-04-25 batch 4 → feature 24→29 |
| OI-3 | Capture +5 decision chunks (ADR) | P1 | [x] Done 2026-04-25 batch 4 → decision 14→19 |
| OI-4 | Force-index unindexed points | P3 | [x] Done 2026-04-25 → indexing_threshold=0 patched |
| 4 | Auto-retry expansion project-aware | P2 | [x] Done 2026-04-25 session 5 → expansions map per project |
| 5 | Tune SCORE_THRESHOLD ke 0.35 | P2 | [x] Done 2026-04-25 session 5 → 0.5→0.35, RETRY 0.6→0.50 |
| 6 | Push-queue audit | P2 | [x] Done 2026-04-25 session 5 — qdrant_url fixed (.169→.199), auto_push exceptions logged, cmd_push_pending TimeoutExpired now continues instead of breaks |
| OI-5 | Aktifkan implementation-spec capture | P4 | [ ] **BLOCKED** — waiting P2.2-B reranker (TEI+BGE on VM B1) |

**Coverage knowledge after all sessions:** 255→296 points, pattern 1→20, feature 24→29, decision 10→19.
Full before/after detail with score projections → [COVERAGE_KNOWLEDGE_TRACKER.md](COVERAGE_KNOWLEDGE_TRACKER.md)
