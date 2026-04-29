# RAG Security Posture — Implementation Tracker

Based on threat model analysis dated 2026-04-29 (PoisonedRAG arXiv:2402.07867).
Tracks hardening tasks across three phases. Update status as each item is implemented and verified.

> **How to use this document:** Each item has Problem → Fix → Verification steps.
> Update status tag and fill in "Completed on" + "Verified by" when done.
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
| n8n HTTP webhook — auth unknown | HIGH | Auth status unconfirmed |
| push-to-qdrant.sh — cosine gate is warning-only | HIGH | `\|\| true` — does not abort on fail |
| No audit log for upserts | MEDIUM | No logging in place |
| No content/schema validation at ingestion | MEDIUM | Any payload accepted |
| No chunk provenance fields | MEDIUM | `ingested_by`, `payload_sha256` absent |

---

## Phase 1 — Immediate (Target: this week)

### P0-1 — Rotate Qdrant API Key

**Status:** `[ ] OPEN`  
**Effort:** ~30 min  
**Completed on:** —  
**Verified by:** —

**Problem:** API key `0aa9f…` is present in public GitHub history (`figulazmi/rag-gateway-mini`).
Any past clone has the key. Key bypasses ALL ingestion controls — attacker can directly upsert to `knowledge_v2`.

**Fix steps:**
1. SSH to VM B1, update Qdrant container config with new key
2. Update `~/.config/qdrant-knowledge.env` on laptop
3. Update `/opt/rag-gateway/appsettings.Production.json` on VM B1
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

**Status:** `[ ] OPEN`  
**Effort:** ~45 min  
**Completed on:** —  
**Verified by:** —  
**Depends on:** P0-1 (rotate first, then scrub)

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

**Status:** `[ ] OPEN`  
**Effort:** ~20 min  
**Completed on:** —  
**Verified by:** —

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

**Status:** `[ ] OPEN`  
**Effort:** ~30 min  
**Completed on:** —  
**Verified by:** —

**Problem:** n8n v2.15.0 HTTP trigger has no auth by default. Webhook URL discovery = open write path to Qdrant.

**Fix steps:**
1. Open n8n → Edit the RAG ingestion webhook trigger node
2. Set **Authentication**: `Header Auth`
3. Header name: `X-Webhook-Secret`
4. Value: generate with `openssl rand -hex 32`
5. Store value in n8n credential vault (not in workflow JSON)
6. Update any scripts that call the webhook to pass the header

**Verification:**
```bash
# Without header — should reject
curl -X POST "http://192.168.18.199:5678/webhook/YOUR_ID" \
  -H "Content-Type: application/json" -d '{"test": true}'
# Expected: 401 Unauthorized

# With correct header — should accept
curl -X POST "http://192.168.18.199:5678/webhook/YOUR_ID" \
  -H "X-Webhook-Secret: YOUR_SECRET" \
  -H "Content-Type: application/json" -d '{"test": true}'
# Expected: 200 OK
```

---

### P0-5 — Audit Log for Qdrant Upserts

**Status:** `[ ] OPEN`  
**Effort:** ~1 hour  
**Completed on:** —  
**Verified by:** —

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

**Status:** `[ ] OPEN`  
**Effort:** ~1 hour  
**Completed on:** —  
**Verified by:** —

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

**Status:** `[ ] OPEN`  
**Effort:** ~2 hours  
**Completed on:** —  
**Verified by:** —

**Problem:** Chunks missing required fields (project, chunk_type, topic, tags, body) are accepted
and pushed to Qdrant, creating incomplete records that degrade retrieval and are harder to audit.

**Required fields for hard reject:**

| Field | Type | Validation rule |
|---|---|---|
| `project` | string | Must be in `{homelab, petrochina-eproc}` |
| `chunk_type` | string | Must be in `{debug, feature, runbook, pattern, decision, reference, implementation-spec}` |
| `topic` | string | Non-empty, max 60 chars, ASCII only |
| `tags` | list[str] | Min 1, max 8, first tag must be in `{dotnet, python, homelab}` |
| `body` | string | Min 100 chars, max 2000 chars |

---

### P1-3 — Chunk Provenance Fields

**Status:** `[ ] OPEN`  
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
| Embedding Consistency Gate | N/A | YES — high value | `[ ] OPEN` (P0-3) |
| Payload Schema Validation | N/A | YES — low effort | `[ ] OPEN` (P1-2) |
| LLM Citation Verification | N/A | YES — medium effort | `[ ] OPEN` (P2-2) |

---

*Last updated: 2026-04-29 · Author: Figur Ulul Azmi*  
*Cross-reference: [`RAG_EVAL_HARNESS.md`](../quality/RAG_EVAL_HARNESS.md) (retrieval quality) · [`RAG_BOTTLENECK_FIXES.md`](../pipeline/RAG_BOTTLENECK_FIXES.md) (pipeline fixes)*
