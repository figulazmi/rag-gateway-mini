# [VM 105] Plan: Restoration — Scripts + Full knowledge_v2 Re-ingest

**Created:** 2026-04-28
**Author:** Figur Ulul Azmi
**SSH:** `figulazmi@192.168.18.199`
**Goal:** Restore VM 105 to match full state of VM B1 as of 2026-04-27

> Backup yang tersedia di VM 105: **2026-04-13** (gap = 14 hari updates hilang).
> User memiliki 120 summary `.md` files tersebar di 8 lokasi lokal Windows.
> Sebelum push, scripts harus sesuai konfigurasi April 27.

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
| Target collection | `knowledge_v2` | `DOC_COLLECTION:-knowledge_v2` default | ⚠️ Partial |
| IP address | `192.168.18.199` | `B1_LOCAL_IP="192.168.18.199"` | ✅ OK |
| Network detection | local-b1→LAN→Tailscale | Implemented | ✅ OK |
| `get_point_count()` delta | Ada, log before/after | Implemented (line ~326) | ✅ OK |
| Per-chunk metadata `rag_chunk_meta` | Ada, extract type+tags per chunk | Implemented | ✅ OK |
| Supersede/deprecate logic | Ada, PATCH old point | Implemented | ✅ OK |
| QDRANT_API_KEY | Dari `~/.config/qdrant-knowledge.env` | Reads from env/file | ✅ OK |
| `collection: knowledge` lama → override | Harus force ke `knowledge_v2` | **BUG: tidak di-override** | ❌ FIXED (0b) |

### Pipeline B — Read/Retrieve (`qdrant-mcp-server-v2.js`)

| Component | April 27 Target | Local File Status | Issue? |
|---|---|---|---|
| `SCORE_THRESHOLD` | `0.35` | `0.5` (line 16) | ❌ FIXED (0a) |
| `RETRY_THRESHOLD` | `0.50` | `0.6` (line 17) | ❌ FIXED (0a) |
| `NOT_FOUND_THRESHOLD` | `0.50` | `0.50` (line 18) | ✅ OK |
| Retry expansion | Project-aware (homelab vs petrochina-eproc) | Generic string | ❌ FIXED (0a) |
| Hybrid search (dense+sparse+RRF) | Ada | Ada (line 165) | ✅ OK |
| djb2 BM25 sparse vector | Ada, match n8n + C# | Ada (line 57) | ✅ OK |
| `using: "dense"` / `using: "sparse"` named vectors | Ada | Ada | ✅ OK |
| `RERANK_ENABLED` scaffolding (off by default) | Ada, disabled | Ada | ✅ OK |
| Status filter (`implemented` default) | Ada | Ada | ✅ OK |
| `rag_search` / `rag_retry` stderr logs | Ada | Ada | ✅ OK |

### n8n Workflow — Contextual Retrieval

| Component | April 27 Target | VM 105 Status | Issue? |
|---|---|---|---|
| Ollama reads `embed_content` | `{{ $json.embed_content }}` | Pre-Apr 19 = `$json.content` raw | ❌ Step 3 |
| `embed_content` build | `"This chunk from project X..."` prepend | Tidak ada di backup Apr 13 | ❌ Step 3 |
| Webhook path | `/webhook/knowledge-ingest` | Ada tapi pre-contextual-retrieval | ❌ Step 3 |

---

## Inventory Summary Files (120 total)

| Lokasi | Files | Date Range | Notes |
|---|---|---|---|
| `D:\Backup\qdrant-backup\summaries\PetroChina.Eproc\` | 32 | Apr 07–16 | Older backup, `collection: knowledge` lama → override di step 0b |
| `D:\Backup\qdrant-backup\summaries\rag-gateway-mini\` | 26 | Apr 11–15 | Older backup, `collection: knowledge` lama → override di step 0b |
| `homelab-hardening\.claude\summaries\` | 3 | Apr 27 | |
| `ai-agent-stack\.claude\summaries\` | 11 | Apr 07, 25–27 | |
| `openclaw-setup\.claude\summaries\` | 1 | Apr 21 | |
| `PetroChina.Eproc\.claude\summaries\` | 15 | Apr 16–24 | |
| `rag-gateway-mini\.claude\summaries\` | 25 | Apr 19–25 | |
| `token-monitor\.claude\summaries\` | 7 | Apr 12–21 | |

**Upsert idempotent** — DOC_ID deterministik (`{id}-chunk-{N}`), aman di-push ulang.

---

## Tracking — Mana yang Sudah, Mana yang Belum

| Step | Task | Status | Notes |
|---|---|---|---|
| **0a** | Fix `qdrant-mcp-server-v2.js`: SCORE_THRESHOLD 0.5→0.35, RETRY 0.6→0.50, retry expansion project-aware | `[x] DONE` | 3 edits, local file |
| **0b** | Fix `push-to-qdrant.sh`: add `collection="knowledge"` ke override condition | `[x] DONE` | 1 edit, local file |
| **0c** | Setup `~/.config/qdrant-knowledge.env` dengan QDRANT_API_KEY | `[x] DONE` | Prerequisite push-to-qdrant.sh |
| **1** | Recreate `knowledge_v2` collection (named dense+sparse+idf) | `[x] DONE` | Delete + PUT + PATCH, verify sparse.modifier=idf |
| **2a** | SCP `push-to-qdrant.sh` ke VM | `[x] DONE` | |
| **2b** | SCP `rag_capture.py` ke VM | `[x] DONE` | |
| **2c** | SCP `qdrant-mcp-server-v2.js` ke VM (post-fix) | `[x] DONE` | |
| **2d** | SCP `ingest-knowledge-v2.json` ke VM | `[x] DONE` | |
| **2e** | SCP `eval-retrieval-quality.py` ke VM | `[x] DONE` | |
| **2f** | Setup `~/.rag_config.json` di VM | `[x] DONE` | URL = localhost:6333 |
| **3** | Update n8n workflow — import + aktifkan contextual retrieval | `[ ] PENDING` | **Manual via n8n UI** |
| **4** | Deploy MCP server v2 ke `/opt/mcp-servers/` + restart | `[x] DONE` | |
| **5a** | Verify D:\Backup frontmatter collection field | `[ ] PENDING` | Sebelum push D: drive files |
| **5b** | Push 62 repo-based summaries (homelab-hardening s/d token-monitor) | `[ ] PENDING` | |
| **5c** | Push 58 D:\Backup summaries | `[ ] PENDING` | Handle collection field sudah di-fix step 0b |
| **5d** | Verify point count di Qdrant | `[ ] PENDING` | Expected: 100+ points |
| **6a** | Run eval framework | `[ ] PENDING` | Target NDCG@5>=0.93 |
| **6b** | MCP query test via Claude Code | `[ ] PENDING` | |

> **Step yang BELUM dijalankan: 3, 5a, 5b, 5c, 5d, 6a, 6b**
> Step 3 (n8n workflow) adalah BLOCKER untuk 5a-5c — tanpa contextual retrieval,
> vectors yang di-ingest akan salah (raw embed, bukan prepended embed).

---

## Execution Detail

### Step 0a — qdrant-mcp-server-v2.js fixes applied

**File:** `C:\Users\Clandesitine\scripts\qdrant-mcp-server-v2\qdrant-mcp-server-v2.js`

```javascript
// Line 16-17: thresholds
const SCORE_THRESHOLD = 0.35;   // was 0.5
const RETRY_THRESHOLD = 0.50;   // was 0.6

// Line ~338: project-aware retry expansion
const expansions = {
  homelab: "deployment configuration setup steps homelab VM B1 Docker infrastructure",
  "petrochina-eproc": "Blazor .NET 9 EF Core CQRS MediatR implementation pattern C#",
};
const expansion = expansions[project] || "implementation architecture system behavior";
const rewrittenQuery = effectiveQuery + " " + expansion;
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

### Step 3 — Update n8n Workflow (PENDING — Manual)

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
   ssh figulazmi@192.168.18.199 'curl -s -o /dev/null -w "%{http_code}" http://localhost:5678/webhook/knowledge-ingest'
   # Expected: 200
   ```

---

### Step 5 — Push 120 Files (PENDING — setelah Step 3 selesai)

```bash
# Push repo-based summaries (62 files, format baru)
for f in \
  /c/Users/Clandesitine/source/repos/homelab-hardening/.claude/summaries/*.md \
  /c/Users/Clandesitine/source/repos/ai-agent-stack/.claude/summaries/*.md \
  /c/Users/Clandesitine/source/repos/openclaw-setup/.claude/summaries/*.md \
  /c/Users/Clandesitine/source/repos/PetroChina.Eproc/.claude/summaries/*.md \
  /c/Users/Clandesitine/source/repos/rag-gateway-mini/.claude/summaries/*.md \
  /c/Users/Clandesitine/source/repos/token-monitor/.claude/summaries/*.md; do
  bash ~/scripts/push-to-qdrant.sh "$f"
  sleep 1
done

# Push D:\Backup summaries (58 files, format lama — collection override sudah di-fix step 0b)
for f in \
  "/d/Backup/qdrant-backup/summaries/PetroChina.Eproc/"*.md \
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
- **MCP server v2** sudah deploy, env var QDRANT_API_KEY harus set via PM2/systemd ecosystem
- **knowledge_v2** sudah punya config hybrid (named dense+sparse+idf) dan kosong — siap ingest

---

*Created: 2026-04-28 | Last updated: 2026-04-28*
*Based on: pipeline audit vs docs April 27 state*
