# RAG Qdrant Intelligence Audit

> **Navigation:** [docs/README.md](README.md) — full index of all RAG docs.
> Coverage knowledge detail & improvement history → [COVERAGE_KNOWLEDGE_TRACKER.md](COVERAGE_KNOWLEDGE_TRACKER.md)

**Date:** 2026-04-25  
**Overall Score: 6.8/10**

---

## Snapshot

| Dimension | Score | Notes |
|---|---|---|
| Infrastruktur | 9/10 | Qdrant 1.17.1, hybrid RRF, status green |
| Coverage knowledge | 5/10 | 67% debug-biased, pattern/reference nyaris 0 |
| Query quality | 7/10 | Retry bias ke homelab, threshold alignment needed |
| Freshness | 6/10 | 22% unindexed, 2 checkpoint belum promote |
| Pipeline reliability | 7/10 | qdrant_url `.169` salah, push-queue perlu audit |

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

```js
// Current (wrong for petrochina-eproc):
const rewrittenQuery = effectiveQuery + " deployment configuration setup steps homelab VM B1";
```

Fix di `/opt/mcp-servers/qdrant-knowledge/qdrant-mcp-server.js`:
```js
const expansions = {
  homelab: "deployment configuration setup steps homelab VM B1 Docker",
  "petrochina-eproc": "Blazor .NET EF Core CQRS MediatR implementation pattern",
};
const expansion = expansions[project] || "implementation architecture system behavior";
const rewrittenQuery = effectiveQuery + " " + expansion;
```

**Status:** [ ] TODO

---

#### B. SCORE_THRESHOLD vs NOT_FOUND_THRESHOLD Redundant

```js
const SCORE_THRESHOLD = 0.5;       // filter individual results
const NOT_FOUND_THRESHOLD = 0.50;  // output gate — same value, redundant
```

Pertimbangkan turunkan `SCORE_THRESHOLD` ke `0.35` (consistent dengan rag-gateway config) agar borderline results (0.35-0.49) tidak dibuang sebelum NOT_FOUND gate.

**Status:** [ ] TODO — evaluate impact first

---

### P3 — Freshness (Score: 6/10)

#### A. 56 Points Unindexed

```bash
ssh figulazmi@192.168.18.199 'curl -s -X POST \
  "http://localhost:6333/collections/knowledge_v2/index" \
  -H "api-key: QDRANT_API_KEY_REDACTED" \
  -H "Content-Type: application/json" \
  -d "{\"wait\": true}"'
```

**Status:** [ ] TODO

---

### P4 — Implementation-Spec (Score: N/A)

`implementation-spec` chunk type dirancang untuk feed implementer models (qwen2.5-coder). Belum pernah dipakai. Aktifkan ketika ada feature baru yang membutuhkan code generation.

**Status:** [ ] DEFERRED — aktifkan saat P2.2-B reranker selesai

---

## Fix Tracker

| # | Issue | Priority | Status |
|---|---|---|---|
| A | Promote 2 checkpoints April 18 | P0 | [x] Done 2026-04-25 |
| B | Fix rag_config.json URL `.169` | P0 | [x] Done 2026-04-25 → localhost:6333 |
| 1 | Aktif capture pattern chunks | P1 | [x] Done 2026-04-25 → 1→4 pattern chunks |
| 2 | Capture reference chunks (VM B1 topology) | P1 | [x] Done 2026-04-25 → 3→5 reference chunks |
| 3 | Migrate old `knowledge` collection | P1 | [x] Already done prior session (145/147 exist) |
| X | Fix push-to-qdrant.sh per-chunk metadata bug | P1 | [x] Done 2026-04-25 — pipeline bug fixed |
| 4 | Auto-retry expansion project-aware | P2 | [ ] TODO |
| 5 | Tune SCORE_THRESHOLD ke 0.35 | P2 | [ ] TODO — evaluate impact first |
| 6 | Force-index 56 unindexed points | P3 | [ ] TODO |
| 7 | Aktifkan implementation-spec capture | P4 | [ ] DEFERRED |

**Coverage knowledge after 2026-04-25 session:** pattern 1→4, reference 3→5, total 255→262.
Full before/after detail with score projections → [COVERAGE_KNOWLEDGE_TRACKER.md](COVERAGE_KNOWLEDGE_TRACKER.md)
