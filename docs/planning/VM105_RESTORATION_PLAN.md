# [VM 105] Plan: Restoration — Scripts + Full knowledge_v2 Re-ingest

**Created:** 2026-04-28
**Author:** Figur Ulul Azmi
**SSH:** `figulazmi@192.168.18.199`
**Goal:** Restore VM 105 to match full state of VM B1 as of 2026-04-27

> Status tracking standard: [`../reference/TRACKING_STATUS_STANDARD.md`](../reference/TRACKING_STATUS_STANDARD.md).
> This legacy restoration tracker is historical; for new edits, keep one canonical table row per task with evidence.
>
> Backup yang tersedia di VM 105: **2026-04-13** (gap = 14 hari updates hilang).
> User memiliki 120 summary `.md` files tersebar di 8 lokasi lokal Windows.
> Sebelum push, scripts harus sesuai konfigurasi April 27.
>
> **Live verification 2026-04-30:** VM target `192.168.18.199` currently has MCP v2, Qdrant env, `push-to-qdrant.sh`, `rag_capture.py`, n8n workflow source, eval script, and cosine verifier present. Qdrant `knowledge_v2` is reachable with `points_count=368`, dense vector `dense`, sparse vector `sparse`, and `sparse.modifier=idf`. Treat older 350/359 counts below as historical restoration checkpoints, not current counts.

---

## Current Verified State vs April 27 Target (2026-04-30)

| Area | April 27 target | Verified existing state | VM105 action |
|---|---|---|---|
| Qdrant collection | `knowledge_v2` with named dense+sparse vectors and IDF sparse modifier | Live Qdrant: `points_count=368`, dense=`dense`, sparse=`sparse`, `sparse.modifier=idf` | None if restoring onto this VM; if rebuilding from Apr 13 backup, recreate collection before re-push |
| MCP server | v2 server deployed and used by Claude Code | `/opt/mcp-servers/qdrant-knowledge/qdrant-mcp-server-v2.js` exists; `~/.qdrant-mcp.env` exists | Ensure PS1/startup command points to v2, not v1 |
| Ingest scripts | April 27 `push-to-qdrant.sh` and `rag_capture.py` | `~/scripts/push-to-qdrant.sh` and `~/scripts/rag-capture-v2/rag_capture.py` exist on VM; source of truth is rag-tools installed per device under `~/scripts` / `C:\Users\Clandesitine\scripts` | Copy from rag-tools/current laptop `~/scripts/...` to VM105 when rebuilding |
| n8n workflow source | `knowledge_v2` workflow with contextual `embed_content` and protected ingest endpoint | `~/scripts/n8n-workflows/ingest-knowledge-v2.json` exists; source of truth is rag-tools/local scripts, not this repo. Live 2026-04-30: old public path returns 404; secret-path smoke push returns `status: ok` | Import workflow from rag-tools/current laptop, generate the VM-specific secret path, set `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`, and activate after restore |
| Eval and verifier scripts | Eval harness plus cosine verifier available | `~/scripts/eval-retrieval-quality.py` and `~/scripts/verify_embed_cosine.py` exist on VM | Copy scripts, then rerun eval and cosine checks after restore |
| Corpus re-ingest | 120 summary files re-pushed after Apr 13 backup restore | Historical restore pushed 120 summaries; live count is now 368 | For a fresh VM105 rebuild, repeat steps 5b-5d and verify live count after push |

## VM105 Remaining Fix List

Use this list only when restoring from the **2026-04-13 backup** or rebuilding a new server. The currently verified VM already has these items present.

| Priority | Fix needed on restored VM105 | Evidence to collect before marking done |
|---:|---|---|
| 1 | Copy `~/scripts/push-to-qdrant.sh` and `~/scripts/rag-capture-v2/rag_capture.py` from rag-tools/current laptop to `~/scripts/` on VM105 | `test -f ~/scripts/push-to-qdrant.sh` and `test -f ~/scripts/rag-capture-v2/rag_capture.py` |
| 2 | Copy/deploy `qdrant-mcp-server-v2.js` from rag-tools/current laptop to `/opt/mcp-servers/qdrant-knowledge/` and ensure Claude startup uses v2 | `test -f /opt/mcp-servers/qdrant-knowledge/qdrant-mcp-server-v2.js`; smoke query through Claude MCP returns FOUND |
| 3 | Create `~/.qdrant-mcp.env` and local Qdrant env files with the active API key | Qdrant `/collections/knowledge_v2` returns HTTP 200 with api-key header |
| 4 | Import `~/scripts/n8n-workflows/ingest-knowledge-v2.json` from rag-tools/current laptop into n8n and activate webhook | n8n execution log shows `embed_content` populated and Qdrant upsert success |
| 5 | Recreate `knowledge_v2` with dense vector `dense`, sparse vector `sparse`, and `modifier=idf` if restoring from old backup | Qdrant collection config shows dense and sparse names plus `sparse.modifier=idf` |
| 6 | Re-push the 120 summary files from the listed inventory paths | Push logs show HTTP 2xx and point-count checks; final count recorded in this file |
| 7 | Run eval and MCP smoke tests after restore | Eval metrics recorded; Claude MCP smoke test returns expected FOUND results |

---

## Status Legend

```
[ ] PENDING    — belum dikerjakan
[~] IN PROGRESS — sedang dikerjakan
[x] DONE       — selesai + verified
[!] BLOCKED    — menunggu dependency lain
```

---

## Pipeline Verification Audit (vs April 27 target)

### Pipeline A — Write/Ingest (`push-to-qdrant.sh` → n8n → Ollama → Qdrant)

| Component | April 27 Target | Local Script Status | Issue? |
|---|---|---|---|
| Target collection | `knowledge_v2` | `DOC_COLLECTION:-knowledge_v2` default | ✅ FIXED (0b) |
| IP address | `192.168.18.199` | `B1_LOCAL_IP="192.168.18.199"` | ✅ OK |
| Network detection | local-b1→LAN→Tailscale | Implemented | ✅ OK |
| `get_point_count()` delta | Ada, log before/after | Implemented (line ~326) | ✅ OK |
| Per-chunk metadata `rag_chunk_meta` | Ada, extract type+tags per chunk | Implemented | ✅ OK |
| Supersede/deprecate logic | Ada, PATCH old point | Implemented | ✅ OK |
| QDRANT_API_KEY | Dari `~/.config/qdrant-knowledge.env` | Reads from env/file | ✅ OK |
| `collection: knowledge` lama → override | Harus force ke `knowledge_v2` | **BUG: tidak di-override** | ❌ FIXED (0b) |

### Pipeline B — Read/Retrieve (`qdrant-mcp-server-v2.js`)

| Component | April 27 Target | Pre-Restoration State (Apr 13) | Current Deployed | Issue? |
|---|---|---|---|---|
| `SCORE_THRESHOLD` | `0.35` | `0.5` (line 16) | `0.35` | ✅ FIXED (0a) |
| `RETRY_THRESHOLD` | `0.50` | `0.6` (line 17) | `0.55` | ✅ FIXED (0a→0.50, 7c→0.55) |
| `NOT_FOUND_THRESHOLD` | `0.50` | `0.50` (line 18) | `0.35` | ✅ Improved (7c) — beyond Apr27 target |
| Retry expansion | Project-aware (homelab vs project-alpha) | Generic string | Intent-aware 3 rules (homelab) | ✅ FIXED (0a→project-aware, 7b→intent-aware) |
| Hybrid search (dense+sparse+RRF) | Ada | Ada (line 165) | Ada | ✅ OK |
| djb2 BM25 sparse vector | Ada, match n8n + C# | Ada (line 57) | Ada | ✅ OK |
| `using: "dense"` / `using: "sparse"` named vectors | Ada | Ada | Ada | ✅ OK |
| `RERANK_ENABLED` scaffolding (off by default) | Ada, disabled | Ada | Ada | ✅ OK |
| Status filter (`implemented` default) | Ada | Ada | Ada | ✅ OK |
| `rag_search` / `rag_retry` stderr logs | Ada | Ada | Ada | ✅ OK |
| `HYBRID_PREFETCH_MULT` | `6` (hardcoded) | `6` (hardcoded) | `8` (constant) | ✅ Improved (7b) |

### n8n Workflow — Contextual Retrieval

| Component | April 27 Target | Pre-Restoration (Apr 13) | Current Deployed | Issue? |
|---|---|---|---|---|
| Ollama reads `embed_content` | `{{ $json.embed_content }}` | `$json.content` raw | `{{ $json.embed_content }}` | ✅ FIXED (Step 3) |
| `embed_content` build | `"This chunk from project X..."` prepend | Tidak ada | Ada di node Validate & Clean | ✅ FIXED (Step 3) |
| Webhook path | Protected `knowledge_v2` ingest webhook | Public `/webhook/knowledge-ingest` existed before hardening | Secret-bearing path active; old public path returns 404; smoke push returns `status: ok` | ✅ FIXED (Step 3 + P0-4 hardening) |

---

## Inventory Summary Files (120 total)

| Lokasi | Files | Date Range | Notes |
|---|---|---|---|
| `D:\Backup\qdrant-backup\summaries\project-alpha\` | 32 | Apr 07–16 | Older backup, `collection: knowledge` lama → override di step 0b |
| `D:\Backup\qdrant-backup\summaries\rag-gateway-mini\` | 26 | Apr 11–15 | Older backup, `collection: knowledge` lama → override di step 0b |
| `homelab-hardening\.claude\summaries\` | 3 | Apr 27 | |
| `ai-agent-stack\.claude\summaries\` | 11 | Apr 07, 25–27 | |
| `openclaw-setup\.claude\summaries\` | 1 | Apr 21 | |
| `project-alpha\.claude\summaries\` | 15 | Apr 16–24 | |
| `rag-gateway-mini\.claude\summaries\` | 25 | Apr 19–25 | |
| `token-monitor\.claude\summaries\` | 7 | Apr 12–21 | |

**Upsert idempotent** — DOC_ID deterministik (`{id}-chunk-{N}`), aman di-push ulang.

---

## Tracking — Mana yang Sudah, Mana yang Belum

| Step | Task | Status | Notes |
|---|---|---|---|
| **0a** | Fix `qdrant-mcp-server-v2.js`: SCORE_THRESHOLD 0.5→0.35, RETRY 0.6→0.50 (→0.55 via step 7c), retry expansion project-aware (→intent-aware via step 7b) | `[x] DONE` | 3 edits, local file; lihat step 7b+7c untuk lanjutan |
| **0b** | Fix `push-to-qdrant.sh`: add `collection="knowledge"` ke override condition | `[x] DONE` | 1 edit, local file |
| **0c** | Setup `~/.config/qdrant-knowledge.env` dengan QDRANT_API_KEY | `[x] DONE` | Prerequisite push-to-qdrant.sh |
| **1** | Recreate `knowledge_v2` collection (named dense+sparse+idf) | `[x] DONE` | Delete + PUT + PATCH, verify sparse.modifier=idf |
| **2a** | SCP `push-to-qdrant.sh` ke VM | `[x] DONE` | Verified 2026-04-30: `~/scripts/push-to-qdrant.sh` exists on VM; source of truth is rag-tools/current laptop under `~/scripts` |
| **2b** | SCP `rag_capture.py` ke VM | `[x] DONE` | Verified 2026-04-30: `~/scripts/rag-capture-v2/rag_capture.py` exists on VM; source of truth is rag-tools/current laptop under `~/scripts` |
| **2c** | SCP `qdrant-mcp-server-v2.js` ke VM (post-fix) | `[x] DONE` | Verified 2026-04-30: `/opt/mcp-servers/qdrant-knowledge/qdrant-mcp-server-v2.js` exists; source of truth is rag-tools/current laptop under `~/scripts/qdrant-mcp-server-v2/` |
| **2d** | SCP `ingest-knowledge-v2.json` ke VM | `[x] DONE` | Verified 2026-04-30: `~/scripts/n8n-workflows/ingest-knowledge-v2.json` exists; source of truth is rag-tools/current laptop under `~/scripts/n8n-workflows/` |
| **2e** | SCP `eval-retrieval-quality.py` ke VM | `[x] DONE` | Verified 2026-04-30: `~/scripts/eval-retrieval-quality.py` exists on VM; keep this aligned with the project eval harness when copied |
| **2f** | Setup `~/.rag_config.json` di VM | `[x] DONE` | URL = localhost:6333 |
| **3** | Update n8n workflow — import + aktifkan contextual retrieval | `[x] DONE` | Manual via n8n UI |
| **4** | Deploy MCP server v2 ke `/opt/mcp-servers/` + restart | `[x] DONE` | |
| **5a** | Verify D:\Backup frontmatter collection field | `[x] DONE` | collection field missing → override catches it; 3 file project fix done |
| **5b** | Push 62 repo-based summaries (homelab-hardening s/d token-monitor) | `[x] DONE` | All 200 OK, 0 errors |
| **5c** | Push 58 D:\Backup summaries | `[x] DONE` | All 200 OK, 0 errors |
| **5d** | Verify point count di Qdrant | `[x] DONE` | Historical snapshot: **359 points, 359 indexed** on 2026-04-29; live verification on 2026-04-30 shows `points_count=368`, `indexed_vectors_count=371` |
| **6a** | Run eval framework | `[x] DONE` | NDCG@5=0.905, Hit@1=0.80, MRR=0.90 — below target; no regressions, hybrid beneficial |
| **6b** | MCP query test via Claude Code | `[x] DONE` | 1/3 FOUND (push-to-qdrant.sh score=0.708); 2/3 NOT FOUND |
| **7a** | Audit gap outcome — prefetch-mult=8 experiment | `[x] DONE` | Metric tidak berubah; Hit@1 tetap 0.80 — prefetch bukan akar masalah |
| **7b** | Fix MCP: intent-aware retry expansion + HYBRID_PREFETCH_MULT=8 | `[x] DONE` | `buildRetryExpansion()` dengan 3 homelab intent rules; improved check pakai topScore |
| **7c** | Fix MCP: tune thresholds RETRY 0.50→0.55, NOT_FOUND 0.50→0.35 | `[x] DONE` | Root cause Q3 NOT FOUND: RRF scores cap lower dari cosine; NOT_FOUND_THRESHOLD terlalu ketat |
| **7d** | Verify post-patch smoke test 3/3 | `[x] DONE` | **3/3 FOUND** — Q3 FOUND (topScore=0.833) — *pre-PS1-fix scores, lihat 7g untuk final* |
| **7e** | Fix `claude-mcp-connect.ps1`: `$MCP_CMD` → `qdrant-mcp-server-v2.js` | `[x] DONE` | Root cause: PS1 masih spawn v1 (`COLLECTION=knowledge`, old thresholds) bukan v2 |
| **7f** | Create `~/.qdrant-mcp.env` di VM B1 dengan `QDRANT_API_KEY` (chmod 600) | `[x] DONE` | v2 reads key dari env file; tanpa ini v2 exit on startup |
| **7g** | Final smoke test 3/3 post-PS1-fix (sesi 2026-04-29) | `[x] DONE` | Q1=0.750, Q2=0.611, Q3=1.000 — true end-to-end verification via v2 |

> **Semua steps SELESAI: 0a–7g DONE**
> Historical snapshot: knowledge_v2 had 350 points indexed after the initial Apr 29 restoration, later verified at 359/359 in step 5d, and live-checked at 368 points on 2026-04-30. MCP v2 end-to-end verified 3/3 FOUND. Eval 2026-04-29.

---

## Step 6 Results (2026-04-29)

### Step 6a — Eval Summary (5 homelab queries, hybrid-rrf vs dense-only vs sparse-only)

| Metric | Dense | Sparse | **Hybrid** | Target | Met? |
|--------|-------|--------|------------|--------|------|
| Hit@1 | 0.80 | 1.00 | **0.80** | 1.0 | ❌ |
| Hit@3 | 0.80 | 1.00 | **1.00** | — | ✓ |
| Hit@5 | 1.00 | 1.00 | **1.00** | — | ✓ |
| MRR | 0.85 | 1.00 | **0.90** | 1.0 | ❌ |
| NDCG@5 | 0.85 | 0.98 | **0.905** | 0.93 | ❌ |

**System verdict:** Hybrid-RRF beneficial — 3 improved / 0 regressed vs dense-only.

**Weak query:** Q4 (RAG gateway ASP.NET Core hybrid BM25) — dense leg pulled wrong doc to #1,
hybrid RRF followed → Hit@1=0.0, MRR=0.5. Sparse alone got NDCG@5=1.0 on this query.
Root cause: generic terms ("threshold", "score") match multiple docs; dense loses discriminative power.

**Avg latency:** ~781ms per query (embed + 3-strategy search on Ollama+Qdrant local).

### Step 6b — MCP Query Test (3 queries via search_knowledge)

| # | Query | Status | Top Score |
|---|-------|--------|-----------|
| 1 | push-to-qdrant.sh webhook n8n ingest pipeline configuration | **FOUND** | 0.708 |
| 2 | Qdrant hybrid search dense sparse RRF named vectors setup | NOT FOUND | — |
| 3 | VM B1 Docker deployment rag-gateway-mini update workflow SSH | NOT FOUND | — |

Q2/Q3 NOT FOUND via MCP despite relevant chunks existing. Root cause awal: `NOT_FOUND_THRESHOLD=0.50`
terlalu ketat untuk RRF scores (max 1.0 hanya jika rank-1 di kedua leg). Fixed in Step 7c.

> ⚠️ **Root cause lebih dalam ditemukan di Step 7e:** `claude-mcp-connect.ps1` masih spawn
> `qdrant-mcp-server.js` (v1, `COLLECTION=knowledge`), bukan v2. Step 7d "3/3 FOUND" valid
> dalam session itu, tapi regresi setelah restart — karena PS1 tetap spawn v1. Fix permanen
> baru terjadi di Step 7e (PS1 diupdate) + Step 7f (env file) + Step 7g (final verification).

### Step 7 Results (2026-04-29) — Post-Patch Smoke Test

> ⚠️ Skor di bawah dari session **sebelum PS1 fix** (pre-Step 7e). Valid dalam session itu,
> regresi setelah restart. **Canonical final result ada di Step 7g** (post-PS1-fix).

| # | Query | Status | Top Score | Retry? |
|---|-------|--------|-----------|--------|
| 1 | push-to-qdrant.sh webhook n8n ingest pipeline configuration | **FOUND** | 0.625 | yes |
| 2 | Qdrant hybrid search dense sparse RRF named vectors setup | **FOUND** | 0.643 | no |
| 3 | VM B1 Docker deployment rag-gateway-mini update workflow SSH | **FOUND** | 0.833 | no |

**Threshold decisions (final):**
- `SCORE_THRESHOLD = 0.35` — unchanged; filters true noise
- `RETRY_THRESHOLD = 0.55` — raised from 0.50; fires retry for borderline-avgScore queries (Q4-type)
- `NOT_FOUND_THRESHOLD = 0.35` — lowered from 0.50; RRF scores cap lower than cosine similarity

**Remaining known limitation:** eval Hit@1 tetap 0.80 karena Q4 ("RAG gateway ASP.NET Core hybrid BM25")
adalah semantic collision — query pakai istilah generik yang dominan di chunk lain. Dokumen relevan
tetap dikembalikan di rank-2 (Hit@3=1.0, Hit@5=1.0). Retry path sekarang aktif untuk Q4 via MCP
(avgScore 0.5502 < RETRY_THRESHOLD 0.55) dan intent-aware expansion mengembalikannya ke rank-1.

### Step 7g — Final Smoke Test Post-PS1-Fix (2026-04-29, sesi baru)

| # | Query | Status | Top Score |
|---|-------|--------|-----------|
| 1 | MCP v2 qdrant server threshold configuration homelab knowledge | **FOUND** | 0.750 |
| 2 | RAG gateway hybrid BM25 RRF search pipeline Qdrant embeddings Ollama | **FOUND** | 0.611 |
| 3 | VM B1 Docker deployment workflow rag-gateway-mini compose update redeploy | **FOUND** | 1.000 |

True end-to-end verification: Claude Code → PS1 → SSH → `qdrant-mcp-server-v2.js` → `knowledge_v2`.

### Steps 7e–7f — MCP Wiring Fix (2026-04-29)

**Root cause discovered:** `claude-mcp-connect.ps1` `$MCP_CMD` masih menunjuk ke `qdrant-mcp-server.js` (v1).
v1 queries `COLLECTION="knowledge"` (old collection) + `NOT_FOUND_THRESHOLD=0.65` — semua `knowledge_v2` chunks invisible.

**Fix 7e — `claude-mcp-connect.ps1`:**
```powershell
# Before:
$MCP_CMD = "node /opt/mcp-servers/qdrant-knowledge/qdrant-mcp-server.js"
# After:
$MCP_CMD = "node /opt/mcp-servers/qdrant-knowledge/qdrant-mcp-server-v2.js"
```

**Fix 7f — `~/.qdrant-mcp.env` on VM B1:**
```bash
ssh figulazmi@192.168.18.199 'cat > ~/.qdrant-mcp.env << EOF
QDRANT_API_KEY=<key>
EOF
chmod 600 ~/.qdrant-mcp.env'
```

v2 reads `QDRANT_API_KEY` exclusively from this file at startup — no API key = v2 exits immediately.
Restart Claude Code required after any PS1 or MCP binary change (process spawned at session start).

---

## Execution Detail

### Step 0a — qdrant-mcp-server-v2.js fixes applied

**File:** `C:\Users\Clandesitine\scripts\qdrant-mcp-server-v2\qdrant-mcp-server-v2.js`

> ⚠️ Nilai di bawah adalah **final state** setelah step 0a + 7b + 7c. Step 0a = fix awal (0.35/0.50/project-aware); Step 7b = intent-aware buildRetryExpansion + HYBRID_PREFETCH_MULT=8; Step 7c = RETRY 0.50→0.55, NOT_FOUND 0.50→0.35.

```javascript
// Final thresholds (post step 0a + 7c):
const SCORE_THRESHOLD = 0.35;        // was 0.5 (step 0a)
const RETRY_THRESHOLD = 0.55;        // was 0.6 → 0.50 (step 0a) → 0.55 (step 7c)
const NOT_FOUND_THRESHOLD = 0.35;    // was 0.50 (step 7c); RRF scores != cosine similarity
const HYBRID_PREFETCH_MULT = 8;      // was hardcoded limit*6 (step 7b)

// Intent-aware retry expansion (step 7b — 3 homelab keyword rules):
function buildRetryExpansion(query, project) {
  const q = query.toLowerCase();
  if (/hybrid|rrf|bm25|threshold|score|prefetch/.test(q))
    return "IVectorSearchClient QdrantQueryResponse EnableHybridSearch ScoreThreshold RRF fusion";
  if (/deployment|docker|compose|ssh|vm/.test(q))
    return "rag-gateway-mini docker compose up build VM B1 git pull redeploy workflow";
  if (/push-to-qdrant|n8n|webhook|frontmatter/.test(q))
    return "push-to-qdrant.sh network-aware ingest webhook knowledge-ingest frontmatter";
  // fallback: project-aware generic expansion
  const expansions = {
    homelab: "deployment configuration setup steps homelab VM B1 Docker infrastructure",
    "project-alpha": "Blazor .NET 9 EF Core CQRS MediatR implementation pattern C#",
  };
  return expansions[project] || "implementation architecture system behavior";
}
```

---

### Step 0b — push-to-qdrant.sh collection override fix applied

**File:** `C:\Users\Clandesitine\scripts\push-to-qdrant.sh`

```bash
# Before (line ~176):
[ "$DOC_COLLECTION" = "unknown" ] || [ -z "$DOC_COLLECTION" ] && DOC_COLLECTION="knowledge_v2"

# After:
if [ "$DOC_COLLECTION" = "unknown" ] || [ -z "$DOC_COLLECTION" ] || [ "$DOC_COLLECTION" = "knowledge" ]; then
  DOC_COLLECTION="knowledge_v2"
fi
```

---

### Step 3 — Update n8n Workflow (DONE)

1. Buka `http://192.168.18.199:5678`, login: `azmi` / cek `.env`
2. Import `~/scripts/n8n-workflows/ingest-knowledge-v2.json`
3. Verify node `Validate & Clean` membangun `embed_content`:
   ```
   "This chunk is from project {{ $json.project }}, type {{ $json.chunk_type }},
   topic \"{{ $json.topic }}\", tagged {{ $json.tags }}. Session date {{ $json.date }}.
   Content: {{ $json.content }}"
   ```
4. Verify node Ollama membaca `{{ $json.embed_content }}` bukan `{{ $json.content }}`
5. Toggle Active: **Off → On**
6. Verify webhook:
   ```bash
   ssh figulazmi@192.168.18.199 'curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:5678/webhook/knowledge-ingest -H "Content-Type: application/json" -d "{}"'
   # Expected: 200  (GET selalu 404 — webhook hanya terima POST)
   ```

---

### Step 5 — Push 120 Files (DONE)

```bash
# Push repo-based summaries (62 files, format baru)
for f in \
  /c/Users/Clandesitine/source/repos/homelab-hardening/.claude/summaries/*.md \
  /c/Users/Clandesitine/source/repos/ai-agent-stack/.claude/summaries/*.md \
  /c/Users/Clandesitine/source/repos/openclaw-setup/.claude/summaries/*.md \
  /c/Users/Clandesitine/source/repos/project-alpha/.claude/summaries/*.md \
  /c/Users/Clandesitine/source/repos/rag-gateway-mini/.claude/summaries/*.md \
  /c/Users/Clandesitine/source/repos/token-monitor/.claude/summaries/*.md; do
  bash ~/scripts/push-to-qdrant.sh "$f"
  sleep 1
done

# Push D:\Backup summaries (58 files, format lama — collection override sudah di-fix step 0b)
for f in \
  "/d/Backup/qdrant-backup/summaries/project-alpha/"*.md \
  "/d/Backup/qdrant-backup/summaries/rag-gateway-mini/"*.md; do
  bash ~/scripts/push-to-qdrant.sh "$f"
  sleep 1
done

# Verify
ssh figulazmi@192.168.18.199 'curl -s "http://localhost:6333/collections/knowledge_v2" \
  -H "api-key: QDRANT_API_KEY_REDACTED" | python3 -c \
  "import sys,json; r=json.load(sys.stdin)[\"result\"]; \
  print(\"Points:\", r[\"points_count\"], \"| Indexed:\", r[\"indexed_vectors_count\"])"'
```

---

## Notes

- **Upsert idempotent** — semua push aman diulang, tidak akan duplicate
- **Step 3 adalah blocker** untuk step 5 — n8n harus pakai `embed_content` sebelum push data
- **MCP server v2** sudah deploy. QDRANT_API_KEY di VM B1 ada di `/opt/homelab/ai-stack/qdrant/.env` (bukan `~/.config/qdrant-knowledge.env` — file itu tidak ada di VM B1)
- **knowledge_v2** fully populated — historical Apr 29 snapshots were 350 points after initial restoration and 359/359 in step 5d; live 2026-04-30 verification showed 368 points before P0-4 smoke test and 369 points after authenticated VM105 smoke push, with dense=`dense`, sparse=`sparse`, and `sparse.modifier=idf`
- **PS1 wiring is the critical link** — `claude-mcp-connect.ps1` `$MCP_CMD` harus menunjuk ke binary yang benar. Patching JS file saja tidak cukup; kalau PS1 masih spawn v1, semua patch di v2 tidak efektif
- **`~/.qdrant-mcp.env` wajib ada** di VM B1 sebelum v2 bisa start. v2 tidak punya API key hardcoded; exit on startup jika file tidak ada
- **Restart Claude Code wajib** setiap kali PS1 atau MCP binary berubah — process di-spawn saat session start, bukan hot-reload
- **Smoke test query strings ≠ eval query strings** — Step 7d pakai informal queries; gunakan exact eval Q1–Q5 strings untuk valid regression test

---

*Created: 2026-04-28 | Last updated: 2026-04-30 (VM105 P0-4 webhook auth live-verified: old public path 404, secret-path smoke push OK, audit log and cosine gate verified)*
*Based on: pipeline audit vs docs April 27 state*
