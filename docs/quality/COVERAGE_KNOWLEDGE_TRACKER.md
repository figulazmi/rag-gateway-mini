# Coverage Knowledge — Improvement Tracker

**Dimension score (from [RAG_QDRANT_AUDIT.md](RAG_QDRANT_AUDIT.md)):** 5/10 → target 8/10

> Status tracking standard: [`../reference/TRACKING_STATUS_STANDARD.md`](../reference/TRACKING_STATUS_STANDARD.md).
> Legacy sections may contain historical status text. Current source of truth is [Canonical Task Tracker](#canonical-task-tracker).
> Metric and score tables in this file are measurements, not task status trackers.

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

### Session 2026-04-25 — Batch 2 (Coverage OI-1/OI-2/OI-3)

**Goal:** Capture 13 new chunks covering patterns, decisions, features; fix off-by-one metadata bug; verify and patch misclassified points.

#### Fixes Applied

| Fix | Before | After | Method |
|---|---|---|---|
| Capture 8 pattern chunks (Docker/n8n/VM B1) | pattern: 4 (1.5%) | pattern: 11 (4%) | `rag add -t pattern` × 7 via batch |
| Capture 3 decision chunks (djb2 BM25, secrets, ASP.NET) | decision: 10 (4%) | decision: 14 (5%) | `rag add -t decision` × 3 |
| Capture 1 feature chunk (n8n ingest workflow v2) | feature: 22 | feature: 23 | `rag add -t feature` |
| Capture 1 feature chunk (Proxmox VM B1 backup) | feature: 23 | feature: 24 | `rag add -t feature` |
| Fix off-by-one in `rag_capture.py cmd_merge()` | comment before `## CHUNK N:` header | comment after header (inside chunk) | Edit `rag_capture.py` line 654-656 |
| Patch misclassified ID 5034039 | decision "Pattern: VM B1 no internet" | pattern | Qdrant SET payload `wait=true` |
| Patch misclassified ID 156055377 | feature "Decision: ASP.NET Core" | decision | Qdrant SET payload `wait=true` |
| Push chunk 13 (Proxmox backup) that failed in batch push | missing | pushed → ID 156055375 | Python urllib POST to n8n webhook |
| OI-4: Force-index unindexed points | 199 indexed | 199 indexed (background optimizer, no manual trigger) | Qdrant auto-optimizer |

**Off-by-one bug detail (now fixed in `rag_capture.py`):**
`cmd_merge()` prepended `<!-- rag_chunk_meta -->` BEFORE the `## CHUNK N:` header.
Since `push-to-qdrant.sh` splits on `^##[[:space:]]CHUNK`, the comment accumulated
into the PREVIOUS chunk's body — so chunk N read chunk N+1's metadata (shift-by-one).
Fix: comment now inserted AFTER the first line of body (the header), inside the chunk.

**Chunk 13 failure root cause:**
Chunk content contained `curl http://<VM-IP>:5200/health` — angle brackets caused
bash to interpret `<VM-IP>` as a stdin redirect in the push script, triggering `set -euo pipefail` exit.
Workaround: removed angle brackets in content; pushed via Python urllib directly to n8n webhook.

#### State After Session 2026-04-25 Batch 2

```
knowledge_v2:  275 points total
               199 indexed (76 = 28% unindexed — background optimizer in progress)

chunk_type distribution:
  debug:            170  (62%)
  feature:           24   (9%)   [was 22 → +2]
  runbook:           21   (8%)
  decision:          14   (5%)   [was 10 → +4]
  checkpoint:        11   (4%)
  pattern:           11   (4%)   [was 4 → +7 new, -1 patched from decision, +1 patched to pattern]
  unknown:           14   (5%)   ← pre-existing (Apr 17-21 chunks, before pipeline fix)
  reference:          5   (2%)
  (empty):            5   (2%)   ← pre-existing

debug:pattern ratio = 15:1  [was 43:1] ← continued improvement
```

**New-session chunk count:** 13 total (8 pattern, 2 decision, 2 feature, 1 decision/pattern fix)

**Chunks captured this batch:**
- Pattern: n8n blocks env vars in expressions by default requires explicit flag
- Pattern: inside Docker network always use service hostname not localhost
- Pattern: Docker Compose v2 uses space separator not hyphen
- Pattern: docker cp changes are ephemeral and lost on container recreate
- Pattern: Qdrant cannot add sparse vector config to existing collection requires recreation
- Pattern: Docker volume mount path must exactly match host filesystem path
- Pattern: Snap service and Docker service conflict on same port disable Snap first
- Pattern: VM B1 has no internet access build images locally then deploy via SCP
- Decision: client-side djb2 BM25 chosen over Qdrant server-side inference for knowledge_v2
- Decision: production secrets as Docker volume mount not baked into image
- Decision: ASP.NET Core chosen over FastAPI for rag-gateway because of type safety and DI ecosystem
- Feature: n8n knowledge-ingest workflow v2 pipeline Ollama embed then Qdrant upsert
- Feature: Proxmox VM B1 backup and restore workflow via vzdump vma.zst

**Coverage score after:** 5.5/10 → **6.0/10** (pattern ratio improved significantly, decision coverage up)

---

### Session 2026-04-25 — Batch 3 (OI-1 completion)

**Goal:** Capture 9 more pattern chunks extracted from existing debug knowledge to hit OI-1 target of 20 total.

#### Fixes Applied

| Fix | Before | After | Method |
|---|---|---|---|
| n8n expression prefix pattern | pattern: 11 | pattern: 12 | `rag add -t pattern` |
| Qdrant named vector prefetch `using` field | pattern: 12 | pattern: 13 | `rag add -t pattern` |
| Secrets env var fail-fast guard | pattern: 13 | pattern: 14 | `rag add -t pattern` |
| n8n Code node sandbox / HTTP Request node | pattern: 14 | pattern: 15 | `rag add -t pattern` |
| git pull before docker compose up | pattern: 15 | pattern: 16 | `rag add -t pattern` |
| Qdrant empty vector name = malformed body | pattern: 16 | pattern: 17 | `rag add -t pattern` |
| ASP.NET MapHealthChecks explicit registration | pattern: 17 | pattern: 18 | `rag add -t pattern` |
| Production secrets outside repo volume mount | pattern: 18 | pattern: 19 | `rag add -t pattern` |
| n8n data volume backup before upgrade | pattern: 19 | pattern: 20 | `rag add -t pattern` |

#### State After Session 2026-04-25 Batch 3

```
knowledge_v2:  284 points total

chunk_type distribution:
  debug:            170  (60%)
  feature:           24   (8%)
  runbook:           21   (7%)
  pattern:           20   (7%)   [was 11 → +9]  ← OI-1 TARGET REACHED
  decision:          14   (5%)
  checkpoint:        11   (4%)
  unknown:           14   (5%)   ← pre-existing
  reference:          5   (2%)
  (empty):            5   (2%)   ← pre-existing

debug:pattern ratio = 8.5:1  [was 15:1] ← significant improvement
```

**Patterns captured this batch:**
- Pattern: n8n raw body expression prefix must be exactly ={{ no leading equals or spaces
- Pattern: Qdrant named vector collection requires using field in every prefetch leg
- Pattern: never hardcode secrets in tracked files use env var with fail-fast guard
- Pattern: n8n Code node sandbox blocks fetch and axios use HTTP Request node for outbound calls
- Pattern: always git pull on VM before docker compose up build compose file on disk drives the build
- Pattern: Qdrant error Not existing vector name empty string indicates malformed request body not missing vector
- Pattern: ASP.NET Core health endpoint requires explicit MapHealthChecks call in Program.cs not auto registered
- Pattern: keep production secrets outside repo in dedicated path and volume mount read-only into container
- Pattern: always backup n8n data volume before major version upgrade workflow export alone is insufficient

**Coverage score after:** 6.0/10 → **6.5/10** (OI-1 complete, debug:pattern ratio 8.5:1)

---

### Session 2026-04-25 — Batch 4 (OI-2 + OI-3 completion)

**Goal:** Capture +5 decision chunks (ADRs for major architectural choices) and +5 feature chunks (core homelab RAG system components) to reach 7.0/10.

#### Chunks Captured

| Chunk | Type | Before | After |
|---|---|---|---|
| Decision: hybrid RRF dense+sparse over cosine-only | decision | 14 | 15 |
| Decision: Qdrant over other vector databases | decision | 15 | 16 |
| Decision: Ollama for local model inference over cloud APIs | decision | 16 | 17 |
| Decision: nomic-embed-text as embedding model | decision | 17 | 18 |
| Decision: n8n as orchestrator for RAG ingest pipeline | decision | 18 | 19 |
| Feature: rag-gateway-mini ASP.NET Core 9 architecture | feature | 24 | 25 |
| Feature: Qdrant knowledge_v2 named vectors dense+sparse config | feature | 25 | 26 |
| Feature: RAG auto-capture toolchain rag_capture.py + push-to-qdrant.sh | feature | 26 | 27 |
| Feature: MCP qdrant-knowledge server for Claude Code context injection | feature | 27 | 28 |
| Feature: n8n Pipeline A (pure retrieval) vs Pipeline B (RAG+LLM) | feature | 28 | 29 |

#### State After Session 2026-04-25 Batch 4

```
knowledge_v2:  295 points total

chunk_type distribution:
  debug:            170  (58%)
  feature:           29  (10%)   [was 24 → +5]  ← OI-2 TARGET REACHED
  runbook:           21   (7%)
  pattern:           20   (7%)
  decision:          19   (6%)   [was 14 → +5]  ← OI-3 TARGET REACHED
  checkpoint:        11   (4%)
  unknown:           14   (5%)   ← pre-existing
  reference:          5   (2%)
  (empty):            5   (2%)   ← pre-existing

debug:pattern ratio = 8.5:1  (unchanged — pattern count stable)
decision coverage: 6%  (was 5%, approaching 8-10% target)
```

**Coverage score after:** 6.5/10 → **7.0/10** (OI-2+3 complete, balanced feature/decision types)

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

Status source: [Canonical Task Tracker](#canonical-task-tracker), task `OI-1`.

**Target:** 20 pattern chunks by next audit (20 captured -- OI-1 complete)

---

### OI-2: Capture Feature Chunks untuk Setiap Feature yang Ship

**Impact:** Medium — feature: 24 (9%), target 15-20%

Setiap fitur yang selesai di-implement harus punya 1 `feature` chunk yang dokumen:
architecture decision, files modified, key implementation choices.

Status source: [Canonical Task Tracker](#canonical-task-tracker), task `OI-2`.

**Target:** +5 feature chunks / bulan

---

### OI-3: Capture Decision Chunks untuk Major Choices

**Impact:** Medium — decision: 14 (5%), target 8-10%

ADR (Architecture Decision Records): why hybrid RRF, why djb2 not server BM25, why ASP.NET not FastAPI, etc.
Session 2 captured 3 decision chunks (djb2 BM25, secrets mount, ASP.NET Core choice).

Status source: [Canonical Task Tracker](#canonical-task-tracker), task `OI-3`.

**Target:** +5 more decision chunks untuk choices yang belum terdokumentasi

---

### OI-4: Force-Index Unindexed Points

**Impact:** Medium — unindexed points hanya searchable via dense, sparse BM25 tidak aktif

```bash
ssh figulazmi@192.168.18.199 'curl -s -X POST \
  "http://localhost:6333/collections/knowledge_v2/index" \
  -H "api-key: QDRANT_API_KEY_REDACTED" \
  -H "Content-Type: application/json" \
  -d "{\"wait\": true}"'
```

Note: Qdrant biasanya auto-index background. Cek dulu apakah count sudah 275/275 (as of 2026-04-25 session 2):
```bash
ssh figulazmi@192.168.18.199 'curl -s "http://localhost:6333/collections/knowledge_v2" \
  -H "api-key: QDRANT_API_KEY_REDACTED" | python3 -c \
  "import sys,json; r=json.load(sys.stdin)[\"result\"]; print(r[\"points_count\"], \"total |\", r[\"indexed_vectors_count\"], \"indexed\")"'
```

Status source: [Canonical Task Tracker](#canonical-task-tracker), task `OI-4`.

---

### OI-5: Aktifkan implementation-spec Capture

**Impact:** Low now, High later — 0 chunks saat ini

`implementation-spec` dirancang untuk feed implementer model (qwen2.5-coder, Ollama).
Membutuhkan reranker (P2.2-B) untuk prioritisasi sebelum fully useful.

Status source: [Canonical Task Tracker](#canonical-task-tracker), task `OI-5`.

---

## Score Projection

| After | pattern | reference | Coverage Score | Notes |
|---|---|---|---|---|
| Baseline | 1 | 3 | 5.0/10 | |
| Session 2026-04-25 | 4 | 5 | 5.5/10 | Pipeline bug fixed |
| OI-1: +20 pattern | ~24 | 5 | 6.5/10 | ratio 7:1 |
| OI-2+3: +10 feature/decision | ~24 | 5 | 7.0/10 | balanced types ← DONE batch 4 |
| OI-4: full index | ~24 | 5 | 7.5/10 | hybrid fully active ← DONE batch 5 |
| OI-5: +10 impl-spec | ~24 | 5 | 8.0/10 | code-gen ready |

**Target: 8/10 by end of next sprint.**

---

## Audit Schedule

| Date | Points | Pattern | Reference | Decision | Score | Notes |
|---|---|---|---|---|---|---|
| 2026-04-25 (baseline) | 255 | 1 | 3 | 10 | 5.0/10 | Initial audit |
| 2026-04-25 (session 1) | 262 | 4 | 5 | 10 | 5.5/10 | P0/P1 fixes + pipeline bug |
| 2026-04-25 (session 2) | 275 | 11 | 5 | 14 | 6.0/10 | Batch 2: +13 chunks, off-by-one fix, patches |
| 2026-04-25 (session 3) | 284 | 20 | 5 | 14 | 6.5/10 | Batch 3: +9 pattern chunks, OI-1 complete |
| 2026-04-25 (session 4) | 295 | 20 | 5 | 19 | 7.0/10 | Batch 4: +5 decision +5 feature, OI-2+3 complete |
| 2026-04-25 (session 5) | 295 | 20 | 5 | 19 | 7.5/10 | Batch 5: OI-4 indexing_threshold=0 patched, sparse covers all 295 |
| _(next audit)_ | — | — | — | — | — | Target: 8.0/10 after OI-5 (impl-spec, needs P2.2-B reranker) |

---

## Canonical Task Tracker

| Order | ID | Task | Status | Evidence | Next action |
|---:|---|---|---|---|---|
| 1 | OI-1 | Capture pattern chunks from existing debug knowledge | `[x] DONE (2026-04-25)` | 20 pattern chunks reached across batches 1-3; debug:pattern ratio improved from 43:1 to 8.5:1 | None |
| 2 | OI-2 | Capture feature chunks for shipped features | `[x] DONE (2026-04-25)` | +5 feature chunks captured in batch 4; total feature chunks reached 29, about 10% | Continue monthly feature capture habit |
| 3 | OI-3 | Capture decision chunks for major choices | `[x] DONE (2026-04-25)` | +5 decision chunks captured in batch 4; total decision chunks reached 19, about 6% | Capture +5 more major decisions when identified |
| 4 | OI-4 | Force-index unindexed points | `[x] DONE (2026-04-25)` | `indexing_threshold` patched to 0; sparse BM25 inverted index covers all 295 points | None |
| 5 | OI-5 | Activate implementation-spec capture | `[ ] DEFERRED` | Requires P2.2-B TEI plus BGE reranker before implementer-model use is reliable | Revisit after reranker is deployed and eval shows benefit |
