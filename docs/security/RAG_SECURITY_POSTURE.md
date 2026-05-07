# RAG Security Posture — Implementation Tracker

Based on threat model analysis dated 2026-04-29 (PoisonedRAG arXiv:2402.07867).
Tracks hardening tasks across three phases. Update status as each item is implemented and verified.

> **How to use this document:** Each item has Problem → Fix → Verification steps.
> Follow [`../reference/TRACKING_STATUS_STANDARD.md`](../reference/TRACKING_STATUS_STANDARD.md): update the canonical task section with status, completed date, verified by, and evidence.
> Cross-reference `RAG_EVAL_HARNESS.md` for retrieval quality metrics.

---

## Status Legend

- `[x] DONE` — implemented, deployed, verified
- `[~] IN PROGRESS` — work started, not yet verified
- `[ ] OPEN` — not yet started
- `[!] BLOCKED` — waiting on dependency (see note)

---

## Threat Model Summary

| Entry Point | Severity | Current State |
|---|---|---|
| Qdrant API key in public git history | CRITICAL | Key `0aa9f…` — rotation status unconfirmed |
| n8n HTTP webhook — auth unknown | HIGH | Fixed 2026-04-30 on VM105: old public path returns 404; secret-bearing path accepts authenticated `push-to-qdrant.sh` payloads |
| push-to-qdrant.sh — cosine gate is warning-only | HIGH | Fixed 2026-04-30: cosine gate now hard-aborts unless `COSINE_GATE_BYPASS=1` |
| No audit log for upserts | MEDIUM | Fixed 2026-04-30: `~/.rag_audit.log` records host/user/doc/chunk/hash/file after successful upsert |
| No content/schema validation at ingestion | MEDIUM | Any payload accepted |
| No chunk provenance fields | MEDIUM | `ingested_by`, `payload_sha256` absent |

---

## Phase 1 — Immediate (Target: this week)

### P0-1 — Rotate Qdrant API Key

**Status:** `[x] DONE`  
**Effort:** ~30 min  
**Completed on:** 2026-04-30  
**Verified by:** Claude Code + runtime HTTP verification (`new key => 200`, `old key => 401`)

**Problem:** API key `0aa9f…` is present in public GitHub history (`figulazmi/rag-gateway-mini`).
Any past clone has the key. Key bypasses ALL ingestion controls — attacker can directly upsert to `knowledge_v2`.

**Fix steps:**
1. SSH to VM B1, update Qdrant container config with new key
2. Update `~/.config/qdrant-knowledge.env` on laptop
3. Update `/opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json` on VM B1
4. Update n8n Qdrant credential in vault
5. Restart Qdrant container + verify `curl -H "api-key: NEW_KEY" http://192.168.18.199:6333/collections` returns 200

**Verification:**
```bash
# Old key should now return 401
curl -H "api-key: 0aa9f..." http://192.168.18.199:6333/collections
# Expected: {"status":{"error":"Unauthorized"}}
```

---

### P0-2 — Scrub Git History

**Status:** `[x] DONE`  
**Effort:** ~45 min  
**Completed on:** 2026-04-30  
**Verified by:** Claude Code (`git_filter_repo --replace-text --force`, `git push --force-with-lease origin main`)  
**Depends on:** P0-1 (rotate first, then scrub)  
**Execution note:** push retried once after lease refresh (`git fetch origin main`), then succeeded.

**Problem:** Even after replacing literals with env-var reads (commit `[scrub commit]`),
the literal key remains in git history of the public repo. Anyone can `git log -p` to find it.

**Fix steps:**
```bash
# Install git-filter-repo if not present
pip install git-filter-repo

# Create replacements file
echo "0aa9f...==>QDRANT_API_KEY_REDACTED" > replacements.txt  # use full key

# Rewrite history
git filter-repo --replace-text replacements.txt

# Force push (requires branch protection bypass — coordinate if needed)
git push origin main --force

# Verify GitHub no longer shows the key
# Check: https://github.com/figulazmi/rag-gateway-mini/search?q=0aa9f
```

**Verification:**
```bash
git log -p | grep "0aa9f" | wc -l
# Expected: 0
```

---

### P0-3 — Harden Cosine Gate (Hard Abort)

**Status:** `[x] DONE`  
**Effort:** ~20 min  
**Completed on:** 2026-04-30  
**Verified by:** Claude Code static verification (`bash -n`, removed `|| true`, hard-abort path present)

**Problem:** `push-to-qdrant.sh` runs `verify_embed_cosine.py` with `|| true`, meaning a failed
cosine check (cos < 0.95) only prints a warning but push proceeds. An adversarial chunk that
passes embedding but has wrong vector can still enter the collection.

**File:** `~/scripts/push-to-qdrant.sh` (on VM B1) or local copy

**Fix:**
```bash
# BEFORE (warning-only):
python ~/scripts/verify_embed_cosine.py "$chunk_file" || true

# AFTER (hard abort):
if ! python ~/scripts/verify_embed_cosine.py "$chunk_file"; then
  echo "ERROR: Cosine gate FAILED for $chunk_file (threshold: 0.95) — push aborted." >&2
  echo "Re-run with COSINE_GATE_BYPASS=1 to skip (requires justification in audit log)." >&2
  exit 1
fi
```

**Verification:**
```bash
# Test with a chunk that should fail the cosine gate
# Manually corrupt the body of a test chunk and attempt push
# Expected: exit code 1, "Cosine gate FAILED" message, no upsert to Qdrant
```

---

### P0-4 — n8n Webhook Authentication

**Status:** `[x] DONE`  
**Effort:** ~30 min  
**Completed on:** 2026-04-30  
**Verified by:** Claude Code live VM105 verification: old public path returned 404, authenticated `push-to-qdrant.sh` smoke push returned HTTP 200 with `status: ok`, Qdrant `points_count` increased 368 → 369, `~/.rag_audit.log` increased 2 → 3, and cosine gate passed.

**Problem:** n8n v2.15.0 HTTP trigger has no auth by default. Webhook URL discovery = open write path to Qdrant.

**Implemented fix:**
1. Generated `N8N_WEBHOOK_SECRET` in `/opt/homelab/ai-stack/qdrant/.env` and copied it to `~/.config/qdrant-knowledge.env` on VM105.
2. Changed `push-to-qdrant.sh` to require `N8N_WEBHOOK_SECRET`, send `X-Webhook-Secret`, and call `/webhook/knowledge-ingest-${N8N_WEBHOOK_SECRET}`.
3. Imported the n8n `knowledge_v2` workflow with a secret-bearing webhook path generated from rag-tools source.
4. Recreated the VM105 n8n container with `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` so workflow HTTP nodes can read `QDRANT_API_KEY` from container env.
5. Switched the workflow webhook response mode to return the `Build Response` node output, so callers receive JSON `status: ok` instead of an empty HTTP 200.

**Verification:**
```bash
# Old public path is closed
curl -s -o /tmp/old_path_final.json -w "%{http_code}" \
  -X POST http://localhost:5678/webhook/knowledge-ingest \
  -H "Content-Type: application/json" -d "{}"
# Observed on VM105: 404

# Authenticated smoke push through secret path
bash ~/scripts/push-to-qdrant.sh /tmp/vm105-auth-test.md
# Observed on VM105: ✅ OK (200), points 368 → 369, audit_lines 2 → 3, cosine gate PASS
```

---

### P0-5 — Audit Log for Qdrant Upserts

**Status:** `[x] DONE`  
**Effort:** ~1 hour  
**Completed on:** 2026-04-30  
**Verified by:** Claude Code static verification (`log_upsert`, payload SHA-256, host/user/doc/chunk metadata present in `push-to-qdrant.sh`)

**Problem:** No record of who pushed what to `knowledge_v2`. Cannot detect unauthorized upserts
or trace the origin of a poisoned chunk after the fact.

**Fix — add to `push-to-qdrant.sh`:**
```bash
AUDIT_LOG="$HOME/.rag_audit.log"

log_upsert() {
  local doc_id="$1"
  local chunk_file="$2"
  local chunk_type="$3"
  local project="$4"
  local payload_hash
  payload_hash=$(sha256sum "$chunk_file" | cut -d' ' -f1)
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) UPSERT host=$(hostname) user=$USER doc_id=$doc_id type=$chunk_type project=$project hash=$payload_hash" \
    >> "$AUDIT_LOG"
}
```

**Audit log format:**
```
2026-04-29T10:30:00Z UPSERT host=laptop user=figulazmi doc_id=rag-gateway-embed-fix-001 type=debug project=homelab hash=abc123...
```

**Verification:**
```bash
# Push one test chunk, then check log
tail -5 ~/.rag_audit.log
# Should show entry for the test chunk
```

---

## Phase 2 — Short-term (Target: 2–4 weeks)

### P1-1 — Source Allowlisting in rag_capture.py

**Status:** `[x] DONE (2026-05-05)`  
**Effort:** ~1 hour  
**Completed on:** 2026-05-05  
**Verified by:** Claude Code + local `rtk python` accepted/rejected source-path verification + `py_compile` syntax check

**Evidence:** Active tool file `C:\Users\Clandesitine\scripts\rag-capture-v2\rag_capture.py` now defines `ALLOWED_SOURCES`, validates source values through `validate_source()`, exposes `--source` on `rag add`, and writes frontmatter `source` from validated input instead of a hardcoded value. Accepted-path smoke succeeded with `--source claude-code-cli`; invalid source was rejected before draft save via CLI choice enforcement. `rtk python -m py_compile` passed after the change.

**Problem:** The `source` field in chunk metadata is a free-form string. An attacker or
misconfigured script can set any value, making audit logs unreliable.

**Fix — add to `rag_capture.py` in the `cmd_add` path:**
```python
ALLOWED_SOURCES = {"claude-code-cli", "n8n-webhook", "manual-push", "rag-capture-v2"}

def validate_source(metadata: dict) -> None:
    source = metadata.get("source", "")
    if source not in ALLOWED_SOURCES:
        raise SystemExit(
            f"Rejected: source '{source}' not in allowlist {ALLOWED_SOURCES}\n"
            "Set a valid --source flag or update ALLOWED_SOURCES."
        )
```

---

### P1-2 — Payload Schema Validation at Ingestion

**Status:** `[x] DONE (2026-05-05)`
**Started on:** 2026-05-02
**Evidence:** Local n8n workflows `~/scripts/n8n-workflows/ingest-knowledge-v2.json` and `~/scripts/n8n-workflows/ingest-knowledge-v2-keyfacts.json` validate required id/content/collection/project/topic/chunk_type/tags, allowed project/type/tag values, ASCII topic length, first-tag allowlist, and content length (`100..20000`). JSON syntax validation passed for both files. Local node-level smoke via `node` + `vm.runInNewContext` confirmed: one valid payload passed, while malformed payloads for missing project, non-ASCII topic, invalid first tag, and too-short content were all rejected in `Validate & Clean`. Live webhook smoke against `http://192.168.18.199:5678/webhook/knowledge-ingest-keyfacts` then confirmed the active n8n workflow rejected a malformed payload missing `project`, accepted a valid payload, upserted the temporary point into `knowledge_v2_keyfacts`, and allowed cleanup of the test point (`qdrant_id=2510859428`) via Qdrant delete API.
**Effort:** ~2 hours  
**Completed on:** 2026-05-05  
**Verified by:** Claude Code local JSON validation + local `Validate & Clean` smoke harness + live n8n malformed rejection/valid success + Qdrant cleanup verification.

**Problem:** Chunks missing required fields (project, chunk_type, topic, tags, body) are accepted
and pushed to Qdrant, creating incomplete records that degrade retrieval and are harder to audit.

**Required fields for hard reject:**

| Field | Type | Validation rule |
|---|---|---|
| `project` | string | Must be in `{homelab, project-alpha}` |
| `chunk_type` | string | Must be in `{debug, feature, runbook, pattern, decision, reference, implementation-spec}` |
| `topic` | string | Non-empty, max 60 chars, ASCII only |
| `tags` | list[str] | Min 1, max 8, first tag must be in `{dotnet, python, homelab}` |
| `body` | string | Min 100 chars, max 20000 chars |

---

### P1-3 — Chunk Provenance Fields

**Status:** `[x] DONE (2026-05-06)`
**Started on:** 2026-05-02
**Evidence:** Published patched live n8n workflow `knowledge_v2_keyfacts` (`id=keyfacts63ce76d761`) from local export `C:\Users\Clandesitine\scripts\n8n-workflows\ingest-knowledge-v2-keyfacts.json` using n8n API `PUT /api/v1/workflows/{id}` plus activate. Post-publish controlled smoke write `p1-3-provenance-smoke-live-after-publish-2026-05-06` returned webhook `status=ok` with `qdrant_id=227909133`; Qdrant read-back for that point confirmed `chunk_source`, `session_type`, `environment`, `git_branch`, `git_commit`, `captured_at`, and `related` persisted end-to-end in `knowledge_v2_keyfacts`.
**Effort:** ~2–3 hours  
**Completed on:** 2026-05-06  
**Verified by:** Claude Code live n8n API publish + single webhook smoke write + Qdrant payload read-back with `api-key` header.

**Problem:** Existing chunks have no `ingested_by`, `ingested_at`, `push_host`, or `payload_sha256`
fields. Cannot trace a poisoned chunk back to its origin.

**Add to every new upsert payload:**
```json
{
  "ingested_by": "figulazmi@hostname",
  "ingested_at": "2026-04-29T10:30:00Z",
  "push_host": "192.168.1.x",
  "push_method": "push-to-qdrant.sh",
  "payload_sha256": "abc123...",
  "embed_model": "nomic-embed-text",
  "embed_prefix_version": "v2"
}
```

**Note:** Backfilling existing ~252 chunks in `knowledge_v2` is P2 effort (see P2-3).

---

### P1-4 — Knowledge Expansion Defense

**Status:** `[x] DONE (2026-05-06)`  
**Effort:** ~3–4 hours  
**Completed on:** 2026-05-06  
**Verified by:** Claude Code local build + VM B1 live smoke
**File:** `src/Application/Services/RagSearchService.cs`

**Problem:** Single-query retrieval is vulnerable to a poisoned chunk that wins top-1 for a specific phrasing. Knowledge Expansion (3 phrasings → union → vote) reduces this risk.

**Approach:**
```
Query Q → Paraphrase(Q) → [Q, Q', Q''] 
→ embed each separately
→ retrieve top-5 per phrasing (15 candidates total)
→ deduplicate by doc_id
→ re-rank by hit count (chunks appearing in 2+ results promoted)
→ return top-5 final
```

**ASR reduction per paper:** ~50–60% when combined with other defenses.

**Tradeoff:** 3x embed calls → +2–3x latency. Implement as opt-in flag: `POST /rag/search { "knowledge_expansion": true }`.

**Implementation (2026-05-06 local):**
- Added `knowledge_expansion: bool` to `RagSearchRequest` and `RagDebugResponse`
- `RagSearchService.SearchAsync` branches on the flag; default path unchanged
- Expansion path: 3 rule-based variants (`original`, `Explain: {q}`, `Describe the approach for: {q}`) embedded in parallel, top results per variant union-deduplicated by `doc_id`, ranked by `(hit_count DESC, best_score DESC)`, `AggregateExpansionResults` returns top `ResultLimit` items
- `DebugAsync` exposes `expanded_queries` in response when flag is true
- Build: `dotnet build` → 0 errors, 0 warnings

**Live verification (VM B1, 2026-05-06):**
- `GET /scalar/` returned `200`
- Default search (`knowledge_expansion` omitted) for `how to push knowledge chunk to Qdrant` returned `status=not_found`
- Expansion search (`knowledge_expansion=true`) for the same query returned `status=found`
- Debug call with expansion returned `knowledge_expansion=true` and populated `expanded_queries`
- Negative query `What is the project-alpha Blazor login flow?` with `project=homelab` and `knowledge_expansion=true` returned `status=not_found`

**Evidence command (executed over SSH):**
```bash
curl -s -o /tmp/p14_scalar.out -w "%{http_code}" http://192.168.18.199:5200/scalar/
curl -s -X POST http://192.168.18.199:5200/rag/search -H "Content-Type: application/json" -d '{"query":"how to push knowledge chunk to Qdrant","project":"homelab"}'
curl -s -X POST http://192.168.18.199:5200/rag/search -H "Content-Type: application/json" -d '{"query":"how to push knowledge chunk to Qdrant","project":"homelab","knowledge_expansion":true}'
curl -s -X POST http://192.168.18.199:5200/rag/debug -H "Content-Type: application/json" -d '{"query":"how to push knowledge chunk to Qdrant","project":"homelab","knowledge_expansion":true}'
curl -s -X POST http://192.168.18.199:5200/rag/search -H "Content-Type: application/json" -d '{"query":"What is the project-alpha Blazor login flow?","project":"homelab","knowledge_expansion":true}'
```

**Outcome:** Knowledge expansion improved recall for phrasing-sensitive query while preserving negative-query not-found gating.

---

### P1-5 — Embedding Anomaly Detector

**Status:** `[x] DONE (2026-05-06)`  
**Effort:** ~4–6 hours  
**Completed on:** 2026-05-06  
**Verified by:** Claude Code local syntax check + VM B1 live push-hook smoke

**Problem:** A carefully crafted injection chunk can have `cosine(poison, legitimate) > 0.97`
but belong to a different project or chunk_type — hijacking the retrieval neighborhood.

**Implemented fix:**
- Added repo script `scripts/anomaly_check.py` and deployed it to VM B1 at `~/scripts/anomaly_check.py`
- Detector loads `QDRANT_API_KEY` from environment or `~/.config/qdrant-knowledge.env`
- Default collection is `knowledge_v2_keyfacts`; collection, threshold, limit, Qdrant URL, and audit log path are CLI-configurable
- Detector loads the new point's dense vector and payload, queries nearest dense neighbors, skips self-hit, and emits `ANOMALY` lines when score is above threshold and `project` or type family (`chunk_type`/`session_type`) mismatches
- Patched VM B1 `~/scripts/push-to-qdrant.sh` post-upsert flow to run `anomaly_check.py` using returned `qdrant_id`; anomaly status is non-blocking for v1 and alerts are appended to `~/.rag_audit.log`
- VM script backup before patch: `~/scripts/push-to-qdrant.sh.bak-p15-20260506140218`

**Verification:**
```bash
# Local syntax check
python -m py_compile scripts/anomaly_check.py

# VM syntax check
python3 -m py_compile ~/scripts/anomaly_check.py
bash -n ~/scripts/push-to-qdrant.sh

# Direct detector smoke on existing point
python3 ~/scripts/anomaly_check.py --point-id 3843143 --collection knowledge_v2_keyfacts
# Observed: OK: no anomalies for point_id=3843143 threshold=0.97

# Live push-hook smoke
bash ~/scripts/push-to-qdrant.sh /tmp/p15-anomaly-smoke.md
# Observed: webhook OK (200), detector ran and printed OK: no anomalies for point_id=552949229 threshold=0.97
# Temporary smoke point 552949229 was deleted after verification; knowledge_v2_keyfacts count returned to 545.
```

**Alert delivery:** Append `ANOMALY point_id=... neighbor_id=... score=... project/type ...` lines to `~/.rag_audit.log`; non-anomalous pushes continue normally.

---

## Phase 3 — Long-term (Target: 1–3 months)

### P2-1 — Forensics Snapshot Vector

**Status:** `[x] DONE (2026-05-06)`  
**Effort:** ~4–6 hours  
**Completed on:** 2026-05-06  
**Verified by:** Claude Code staged Qdrant migration + VM B1 live ingest smoke + tamper-check sample

**Problem:** If a stored vector is tampered with post-upsert (direct Qdrant API write),
there is currently no way to detect it.

**Implemented fix:**
- Added `scripts/add-snapshot-vector-migration.py` for guarded Qdrant migration to named vectors `dense` and `snapshot` plus sparse vector `sparse`
- Added `scripts/snapshot_tamper_check.py` to compare `dense` vs `snapshot` cosine and append `TAMPER` lines to `~/.rag_audit.log` when cosine falls below `0.99`
- Migrated live `knowledge_v2_keyfacts` via staging collection `knowledge_v2_keyfacts_snapshot_stage`
- Created retained backup collection `knowledge_v2_keyfacts_backup_20260506145220`
- Live `knowledge_v2_keyfacts` now has named vectors `dense` and `snapshot` and sparse vector `sparse`
- Patched local n8n workflow export `C:\Users\Clandesitine\scripts\n8n-workflows\ingest-knowledge-v2-keyfacts.json` so new upserts write `snapshot: embedding` alongside `dense: embedding`
- Published the patched workflow to live n8n via `n8n import:workflow`, `n8n publish:workflow`, then restarted the `n8n` container

**Verification:**
```bash
# Local/VM syntax checks
python -m py_compile scripts/add-snapshot-vector-migration.py scripts/snapshot_tamper_check.py
python3 -m py_compile ~/scripts/add-snapshot-vector-migration.py ~/scripts/snapshot_tamper_check.py

# Preflight before migration
python3 ~/scripts/add-snapshot-vector-migration.py --collection knowledge_v2_keyfacts
# Observed before: points_count=545, has_snapshot=False

# Staging migration
python3 ~/scripts/add-snapshot-vector-migration.py --collection knowledge_v2_keyfacts --prepare-stage --force
# Observed: copied 545 points, stage_ready=knowledge_v2_keyfacts_snapshot_stage points=545

# Staging tamper sample
python3 ~/scripts/snapshot_tamper_check.py --collection knowledge_v2_keyfacts_snapshot_stage --sample 5
# Observed: 5/5 points OK with cos=1.000000

# Production promotion
python3 ~/scripts/add-snapshot-vector-migration.py --collection knowledge_v2_keyfacts --promote
# Observed: promoted=knowledge_v2_keyfacts points=545 backup=knowledge_v2_keyfacts_backup_20260506145220

# Live ingest smoke after n8n workflow publish
bash ~/scripts/push-to-qdrant.sh /tmp/p21-snapshot-smoke.md
# Observed: webhook OK (200), qdrant_id=109591335, vectors ['dense', 'snapshot'], cos=1.000000

# Gateway smoke
curl http://192.168.18.199:5200/scalar/
# Observed: 200
# Positive /rag/search with knowledge_expansion=true returned status=found
# Negative homelab cross-project query returned status=not_found

# Final tamper sample
python3 ~/scripts/snapshot_tamper_check.py --collection knowledge_v2_keyfacts --sample 10
# Observed: 10/10 points OK with cos=1.000000, exit 0
```

**Cleanup note:** Temporary smoke point `109591335` was deleted with `wait=true` and verified absent by `has_id` lookup. Qdrant exact count reported `546` after cleanup; treat this as the live post-migration corpus count unless a later compaction/count audit says otherwise.

---

### P2-2 — LLM Citation Verification

**Status:** `[~] IN PROGRESS (2026-05-07)`  
**Effort:** ~6–10 hours  
**Started on:** 2026-05-07  
**Completed on:** —  
**Verified by:** —

**Problem:** llama3.2:3b (3B params) has low adversarial resistance and will follow retrieved context
even if poisoned. No way to know post-generation which claims are grounded vs hallucinated.

**Fix:** New `/rag/answer` endpoint: retrieve chunks → generate grounded answer via Ollama `/api/generate`
with inline citation prompt (`[1]`, `[2]`...) → programmatic `CitationVerifier` tags uncited sentences
`[UNVERIFIED]`. Opt-in: `"citation_verify": true`. No second LLM pass — deterministic regex check.

**Implementation approach (2026-05-07 local):**
- Added `ILlmGenerationClient` + `OllamaGenerationClient` (`POST /api/generate`, stream=false, 60 s timeout)
- Added `CitationVerifier` static class: splits answer into sentences, checks `[N]` refs against chunk count, tags uncited sentences
- Added `RagAnswerRequest` / `RagAnswerResponse` DTOs; `RagAnswerSource` includes `doc_id` + `score`
- Extended `IRagSearchService` with `AnswerAsync`; `RagSearchService.AnswerAsync` delegates to search then generation
- Added `POST /rag/answer` action in `RagController`
- Added `GenerationModel` to `RagGatewayOptions` (default `llama3.2:3b`) and both appsettings files
- Registered `OllamaGenerationClient` as `ILlmGenerationClient` typed HttpClient in `Program.cs`

**Tradeoff:** +1–5 s latency per `/rag/answer` call (Ollama generation warmth dependent).
`citation_verify: false` (default) returns answer without citation markup. Existing `/rag/search` and
`/rag/debug` endpoints are completely unchanged.

**Pending:** Local build verification + VM B1 smoke.

---

### P2-3 — Existing Chunk Provenance Backfill

**Status:** `[x] DONE (2026-05-07)`  
**Effort:** ~6–12 hours  
**Started on:** 2026-05-07  
**Completed on:** 2026-05-07  
**Verified by:** Claude Code local syntax check + live VM B1 Qdrant dry-run/apply/post-verify + spot-check read-back with `api-key` header.

**Problem:** Legacy points in the active Qdrant collection lacked provenance fields, so historical chunks could not be traced to a backfill source or method during incident response.

**Implemented fix:**
- Added `scripts/backfill-provenance.py` using the existing stdlib Qdrant script pattern (`urllib`, `api-key` header, `~/.config/qdrant-knowledge.env` fallback)
- Script supports `--dry-run` preflight and `--apply` write mode
- Uses `POST /collections/{collection}/points/payload?wait=true` with `filter.must[].is_empty.key` for idempotent field-level backfill
- Backfilled only missing fields: `ingested_by`, `push_method`, `backfilled_at`, `backfill_id`
- Preserved vectors and existing payload keys; did not invent unrecoverable historical values such as original `payload_sha256` or `push_host`
- Supports `--collection` override; live target was `knowledge_v2_keyfacts`

**Live verification (VM B1 Qdrant, 2026-05-07):**
```bash
rtk python -m py_compile scripts/backfill-provenance.py
rtk python scripts/backfill-provenance.py --qdrant-url http://192.168.18.199:6333 --collection knowledge_v2_keyfacts --dry-run
# Observed: total_points=560; ingested_by missing=419; push_method missing=419; backfill_id missing=560; backfilled_at missing=560

rtk python scripts/backfill-provenance.py --qdrant-url http://192.168.18.199:6333 --collection knowledge_v2_keyfacts --apply
# Observed: all four fields applied; post-apply result=all_provenance_fields_present

rtk python scripts/backfill-provenance.py --qdrant-url http://192.168.18.199:6333 --collection knowledge_v2_keyfacts --dry-run
# Observed: total_points=560; missing=0 for ingested_by, push_method, backfill_id, backfilled_at
```

**Spot-check evidence:** point `3843143` now has `ingested_by=backfill-p2-3`, `push_method=provenance-backfill-script`, `backfill_id=p2-3-existing-chunk-provenance-2026-05-07`, and `backfilled_at=2026-05-07T08:55:16Z`.

---

### P2-4 — Automated Red Team Cron

**Status:** `[x] DONE (2026-05-07)`  
**Effort:** ~3–5 hours  
**Started on:** 2026-05-07  
**Completed on:** 2026-05-07  
**Verified by:** Claude Code local syntax check + VM B1 one-shot probe + forced msmtp/mail alert test + Qdrant cleanup verification.

**Problem:** No continuous validation that the poisoning defenses are working.

**Implemented fix:**
- Added `scripts/redteam-probe.py` for weekly RAG poisoning-defense validation
- Script inserts one temporary synthetic probe into `knowledge_v2_keyfacts`, queries live `/rag/search` with `knowledge_expansion=true`, alerts if the probe appears in top-5, and deletes the probe before exit
- Uses existing script conventions: stdlib `urllib`, `QDRANT_API_KEY` from environment or `~/.config/qdrant-knowledge.env`, direct Qdrant `api-key` header
- Alert path is VM B1 `mail` command backed by existing homelab msmtp/mailutils pattern, sent to `azmi.codes@gmail.com`
- Default target: `knowledge_v2_keyfacts`; default gateway URL for cron: `http://localhost:5200`

**Installed cron:**
```cron
17 9 * * 1 cd /opt/homelab/ai-stack/rag-gateway-mini && /usr/bin/python3 scripts/redteam-probe.py --collection knowledge_v2_keyfacts --gateway-url http://localhost:5200 >> /var/log/redteam-probe.log 2>&1
```

**Verification evidence (2026-05-07):**
```bash
rtk python -m py_compile scripts/redteam-probe.py
rtk python scripts/redteam-probe.py --qdrant-url http://192.168.18.199:6333 --ollama-url http://192.168.18.199:11434 --gateway-url http://192.168.18.199:5200 --collection knowledge_v2_keyfacts --no-email
# Observed: probe_upsert=ok; gateway_status=not_found; OK probe_not_surfaced_in_top_k; probe_cleanup=ok

ssh figulazmi@192.168.18.199 '~/bin/rtk python3 /tmp/redteam-probe.py --collection knowledge_v2_keyfacts --gateway-url http://localhost:5200 --force-alert'
# Observed: OK probe_not_surfaced_in_top_k; test_email_sent=azmi.codes@gmail.com; probe_cleanup=ok
```

**Cleanup evidence:** Qdrant scroll filter for `topic=redteam-probe-202619` returned `[]` after both one-shot and forced-alert runs.

**Alert threshold:** If probe ranks ≤ 5 → send alert email to `azmi.codes@gmail.com`.

---

## Defense Evaluation Summary

| Defense | Paper ASR | Feasibility | Status |
|---|---|---|---|
| Paraphrasing | 79–93% remain | NOT RECOMMENDED | Skipped |
| Perplexity Detection | Too many false positives | NOT RECOMMENDED | Skipped |
| Duplicate Filtering | No effect | PARTIAL (sparse threshold) | Already in place |
| Knowledge Expansion | 41–43% remain | YES — implement | `[ ] OPEN` (P1-4) |
| Embedding Consistency Gate | N/A | YES — high value | `[x] DONE (2026-04-30)` (P0-3) |
| Payload Schema Validation | N/A | YES — low effort | `[~] IN PROGRESS` (P1-2 local workflow patched, live import pending) |
| LLM Citation Verification | N/A | YES — medium effort | `[ ] OPEN` (P2-2) |

---

*Last updated: 2026-05-02 · Author: Figur Ulul Azmi*  
*Cross-reference: [`RAG_EVAL_HARNESS.md`](../quality/RAG_EVAL_HARNESS.md) (retrieval quality) · [`RAG_BOTTLENECK_FIXES.md`](../pipeline/RAG_BOTTLENECK_FIXES.md) (pipeline fixes)*
