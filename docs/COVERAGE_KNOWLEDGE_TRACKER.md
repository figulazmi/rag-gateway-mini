# Coverage Knowledge — Improvement Tracker

**Dimension score (from [RAG_QDRANT_AUDIT.md](RAG_QDRANT_AUDIT.md)):** 5/10 → target 8/10

Coverage knowledge mengukur seberapa *beragam* dan *seimbang* isi knowledge base.
Retrieval yang bagus butuh campuran chunk type yang tepat — terlalu banyak `debug`
dan retriever hanya bisa menemukan bug fixes, bukan patterns atau runbooks.

---

## Target Distribution

| chunk_type | Target % | Rationale |
|---|---|---|
| debug | 35-40% | Masih berguna tapi tidak boleh mendominasi |
| feature | 15-20% | Setiap fitur yang ship harus terdokumentasi |
| runbook | 10-15% | Prosedur operasional; on-call referral |
| pattern | 20-25% | **Tertinggi ROI** — mencegah repeat mistakes |
| decision | 8-10% | ADR — why we chose X |
| reference | 5-8% | Config maps, topology, port tables |
| implementation-spec | 3-5% | Code-gen specs untuk implementer models |

---

## Baseline State (2026-04-25, sebelum sesi hari ini)

Snapshot saat audit pertama kali dijalankan.

```
knowledge_v2:  255 points total
               199 indexed (56 = 22% unindexed)

chunk_type distribution:
  debug:            170  (67%)  ← CRITICAL — over-indexed
  feature:           22   (9%)
  runbook:           21   (8%)
  decision:          10   (4%)
  checkpoint:         9   (3%)
  reference:          3   (1%)  ← CRITICAL — near-zero
  pattern:            1  (0.4%) ← CRITICAL — near-zero
  implementation-spec: 0  (0%)  ← never used

debug:pattern ratio = 170:1   (target: 2:1)
debug:reference ratio = 57:1  (target: 10:1)
```

**Root cause:** Pipeline hanya capture `debug` chunks secara otomatis (triggered saat bug fix).
Pattern, reference, dan decision tidak pernah diinstruksikan secara aktif.

**Retrieval impact baseline:**
- Query "how to implement X" → returns bug-fix context, not implementation guidance
- Query "what is the config for Y" → NOT FOUND (reference chunks missing)
- Query "why did we choose Z" → low score (only 10 decision chunks)

---

## Session Log

### Session 2026-04-25 — Initial Fixes

**Goal:** Resolve P0 blockers dan bootstrap pattern/reference coverage.

#### Fixes Applied

| Fix | Before | After | Method |
|---|---|---|---|
| Promote 2 checkpoints Apr-18 | 255 points, 9 checkpoint | 257 points (+2) | `rag promote` × 2 |
| Capture pattern chunks | pattern: 1 (0.4%) | pattern: 4 (1.5%) | `rag add -t pattern` × 3 |
| Capture reference chunks | reference: 3 (1%) | reference: 5 (2%) | `rag add -t reference` × 2 |
| Fix URL `.169` → `localhost` | push bisa gagal silently | push reliable | edit `~/.rag_config.json` on VM B1 |
| Fix pipeline per-chunk metadata bug | all chunks dapat type dari chunk 1 | tiap chunk dapat type sendiri | fix `rag_capture.py` + `push-to-qdrant.sh` |

**Pipeline bug detail:**
`push-to-qdrant.sh` membaca `chunk_type` dan `topic` SEKALI dari top-level frontmatter,
lalu mengaplikasikan ke semua chunks. Merged file hanya punya satu frontmatter block
(milik chunk pertama), sehingga chunk 2+ mendapat metadata yang salah.

Fix: `rag_capture.py cmd_merge()` sekarang embed per-chunk metadata sebelum setiap chunk body:
```
<!-- rag_chunk_meta chunk_type=reference tags=[homelab, vm-b1, ...] -->
## CHUNK 4: VM B1 infrastructure topology...
```
`push-to-qdrant.sh` extract topic dari `## CHUNK N: [title]` header, dan type/tags dari comment.

#### State After Session 2026-04-25

```
knowledge_v2:  262 points total

chunk_type distribution:
  debug:            170  (65%)   [was 67%]
  feature:           22   (8%)
  runbook:           21   (8%)
  decision:          10   (4%)
  checkpoint:        11   (4%)
  reference:          5   (2%)   [was 1%]  ← +2 chunks
  pattern:            4   (2%)   [was 0.4%] ← +3 chunks
  implementation-spec: 0  (0%)

debug:pattern ratio = 43:1   [was 170:1]  ← significant improvement
debug:reference ratio = 34:1 [was 57:1]   ← improving
```

**Chunks captured this session:**
- `Pattern: RRF fusion scores require lower SCORE_THRESHOLD than cosine`
- `Pattern: sparse vector tokenizer must match exactly at index-time and query-time`
- `Pattern: RAG knowledge base chunk_type ratio target for balanced retrieval`
- `Reference: VM B1 infrastructure topology — services, IPs, ports`
- `Reference: RAG pipeline file locations and config paths on VM B1`

**Retrieval impact (estimated):**
- Query "RRF score threshold" → sekarang hit pattern chunk (was NOT FOUND)
- Query "VM B1 services ports" → sekarang hit reference chunk (was NOT FOUND)
- Query "djb2 sparse vector" → sekarang hit pattern chunk with alignment rule
- General improvement: pipeline bug fix ensures future chunks land with correct type

**Coverage score after:** 5/10 → **5.5/10** (bottleneck masih debug dominance)

---

## Open Items (ordered by impact)

### OI-1: Capture Pattern Chunks dari Existing Debug Knowledge

**Impact:** High — debug:pattern ratio dari 43:1 → target 2:1 butuh ~85 pattern chunks

Setiap bug fix yang sudah ada di knowledge base SEMESTINYA punya companion pattern chunk
yang mengextract prinsip arsitekturalnya. Ini adalah conversion, bukan net-new capture.

**How to query candidates:**
```
search_knowledge("debug fix error resolution lesson learned", project="homelab", limit=10)
```
Untuk setiap hasil: extract prinsip sebagai pattern chunk.

**Template:**
```bash
cat <<'EOF' | rag add -p homelab -t pattern --topic "Pattern: [rule name]" --tags "homelab,[area],pattern"
### Context
[Sistem / domain — 1 kalimat]
### Pattern
[The rule: always X / never Y when Z]
### When to Apply
[Kapan aturan ini relevan]
### Anti-Pattern
[Apa yang jangan dilakukan dan kenapa]
### Key Facts
- [searchable fact 1]
- [searchable fact 2]
- [searchable fact 3]
EOF
```

**Status:** [ ] OPEN — ongoing, not a one-time task

**Target:** 20 pattern chunks by next audit

---

### OI-2: Capture Feature Chunks untuk Setiap Feature yang Ship

**Impact:** Medium — feature: 22 (8%), target 15-20%

Setiap fitur yang selesai di-implement harus punya 1 `feature` chunk yang dokumen:
architecture decision, files modified, key implementation choices.

**Status:** [ ] OPEN — add to post-ship routine

**Target:** +5 feature chunks / bulan

---

### OI-3: Capture Decision Chunks untuk Major Choices

**Impact:** Medium — decision: 10 (4%), target 8-10%

ADR (Architecture Decision Records): why hybrid RRF, why djb2 not server BM25, why ASP.NET not FastAPI, etc.

**Status:** [ ] OPEN

**Target:** +5 decision chunks untuk choices yang belum terdokumentasi

---

### OI-4: Force-Index 56 Unindexed Points

**Impact:** Medium — 56 points hanya searchable via dense, sparse BM25 tidak aktif

```bash
ssh figulazmi@192.168.18.199 'curl -s -X POST \
  "http://localhost:6333/collections/knowledge_v2/index" \
  -H "api-key: QDRANT_API_KEY_REDACTED" \
  -H "Content-Type: application/json" \
  -d "{\"wait\": true}"'
```

Note: Qdrant biasanya auto-index background. Cek dulu apakah count sudah 262/262:
```bash
ssh figulazmi@192.168.18.199 'curl -s "http://localhost:6333/collections/knowledge_v2" \
  -H "api-key: QDRANT_API_KEY_REDACTED" | python3 -c \
  "import sys,json; r=json.load(sys.stdin)[\"result\"]; print(r[\"points_count\"], \"total |\", r[\"indexed_vectors_count\"], \"indexed\")"'
```

**Status:** [ ] OPEN

---

### OI-5: Aktifkan implementation-spec Capture

**Impact:** Low now, High later — 0 chunks saat ini

`implementation-spec` dirancang untuk feed implementer model (qwen2.5-coder, Ollama).
Membutuhkan reranker (P2.2-B) untuk prioritisasi sebelum fully useful.

**Status:** [ ] DEFERRED — aktifkan setelah P2.2-B reranker selesai

---

## Score Projection

| After | pattern | reference | Coverage Score | Notes |
|---|---|---|---|---|
| Baseline | 1 | 3 | 5.0/10 | |
| Session 2026-04-25 | 4 | 5 | 5.5/10 | Pipeline bug fixed |
| OI-1: +20 pattern | ~24 | 5 | 6.5/10 | ratio 7:1 |
| OI-2+3: +10 feature/decision | ~24 | 5 | 7.0/10 | balanced types |
| OI-4: full index | ~24 | 5 | 7.5/10 | hybrid fully active |
| OI-5: +10 impl-spec | ~24 | 5 | 8.0/10 | code-gen ready |

**Target: 8/10 by end of next sprint.**

---

## Audit Schedule

| Date | Points | Pattern | Reference | Score | Notes |
|---|---|---|---|---|---|
| 2026-04-25 (baseline) | 255 | 1 | 3 | 5.0/10 | Initial audit |
| 2026-04-25 (session) | 262 | 4 | 5 | 5.5/10 | P0/P1 fixes + pipeline bug |
| _(next audit)_ | — | — | — | — | Target: 6.5/10 after OI-1 |
