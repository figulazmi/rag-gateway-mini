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

**Status:** `[~] IN PROGRESS`
**Started on:** 2026-05-02
**Evidence:** Local `~/scripts/push-to-qdrant.sh` sends ingested_by, push_method, embed_model, and embed_prefix_version; local n8n workflow stores provenance payload fields. `bash -n` and JSON validation passed.
**Remaining:** Add payload_sha256 end-to-end without shell expansion regressions, import live workflow, and verify payload fields exist in Qdrant.  
**Effort:** ~2–3 hours  
**Completed on:** —  
**Verified by:** —

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

**Status:** `[ ] OPEN`  
**Effort:** ~3–4 hours  
**Completed on:** —  
**Verified by:** —
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

---

### P1-5 — Embedding Anomaly Detector

**Status:** `[ ] OPEN`  
**Effort:** ~4–6 hours  
**Completed on:** —  
**Verified by:** —

**Problem:** A carefully crafted injection chunk can have `cosine(poison, legitimate) > 0.97`
but belong to a different project or chunk_type — hijacking the retrieval neighborhood.

**Fix — `scripts/anomaly_check.py` (run post-upsert via cron or push hook):**

```python
ANOMALY_THRESHOLD = 0.97

def check_anomaly(new_point_id: str, qdrant_client) -> list[str]:
    alerts = []
    new_vec = get_stored_dense_vector(new_point_id, qdrant_client)
    new_payload = get_payload(new_point_id, qdrant_client)
    
    neighbors = qdrant_client.search(
        collection_name="knowledge_v2",
        query_vector=("dense", new_vec),
        using="dense",
        limit=6,
        with_payload=True
    )
    
    for n in neighbors[1:]:  # skip self
        if n.score > ANOMALY_THRESHOLD:
            if new_payload.get("project") != n.payload.get("project"):
                alerts.append(
                    f"ANOMALY project_mismatch: {new_point_id} score={n.score:.3f} "
                    f"project={new_payload['project']} vs neighbor={n.payload['project']}"
                )
    return alerts
```

**Alert delivery:** Append to `~/.rag_audit.log` + optional email via `mail`.

---

## Phase 3 — Long-term (Target: 1–3 months)

### P2-1 — Forensics Snapshot Vector

**Status:** `[ ] OPEN`  
**Effort:** ~4–6 hours  
**Completed on:** —  
**Verified by:** —

**Problem:** If a stored vector is tampered with post-upsert (direct Qdrant API write),
there is currently no way to detect it.

**Fix:** At ingest time, store the raw embed as an additional named vector `"snapshot"` in Qdrant.
Never update `"snapshot"` after initial upsert. At any future point:

```python
# Tamper detection check
stored_dense = get_vector(point_id, using="dense")
stored_snapshot = get_vector(point_id, using="snapshot")
cos = cosine_similarity(stored_dense, stored_snapshot)
if cos < 0.99:
    alert(f"TAMPER DETECTED: {point_id} cos(dense, snapshot)={cos:.4f}")
```

**Note:** Requires Qdrant collection schema update to add `"snapshot"` named vector (768-dim cosine).

---

### P2-2 — LLM Citation Verification

**Status:** `[ ] OPEN`  
**Effort:** ~6–10 hours  
**Completed on:** —  
**Verified by:** —

**Problem:** llama3.2:3b (3B params) has low adversarial resistance and will follow retrieved context
even if poisoned. No way to know post-generation which claims are grounded vs hallucinated.

**Fix:** After generation, run a second LLM pass that extracts claims and verifies each
against retrieved chunk IDs. Uncited claims get `[UNVERIFIED]` tag.

**Tradeoff:** +500ms latency per query. Implement as opt-in: `"citation_verify": true`.

---

### P2-3 — Existing Chunk Provenance Backfill

**Status:** `[ ] OPEN`  
**Effort:** ~6–12 hours  
**Completed on:** —  
**Verified by:** —

**Problem:** ~252 existing points in `knowledge_v2` lack provenance fields.

**Fix:** Scroll all points, add `{"ingested_by": "backfill-2026-04", "push_method": "backfill-script"}` to each via Qdrant `set_payload` API. Original vectors unchanged.

---

### P2-4 — Automated Red Team Cron

**Status:** `[ ] OPEN`  
**Effort:** ~3–5 hours  
**Completed on:** —  
**Verified by:** —

**Problem:** No continuous validation that the poisoning defenses are working.

**Fix:** Weekly cron on VM B1 that:
1. Inserts a known-poisoned probe chunk (specific topic: `"redteam-probe-{YYYYWW}"`)
2. Queries for it via rag-gateway-mini search endpoint
3. Checks if probe surfaces in top-5 results
4. Alerts if it does (means defenses are insufficient)
5. Deletes the probe chunk regardless of result

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
