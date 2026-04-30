# RAG Power & Security — Implementation Index

Quick-access index for the RAG hardening + quality initiative (started 2026-04-29).

---

## Documents

| Doc | Purpose | Status |
|---|---|---|
| [`RAG_SECURITY_POSTURE.md`](RAG_SECURITY_POSTURE.md) | Phase 1–3 hardening tasks with fix steps + verification | Active |
| [`RAG_EVAL_HARNESS.md`](../quality/RAG_EVAL_HARNESS.md) | Benchmark metrics, labeled query set, score tracking | Active |
| [`RAG_BOTTLENECK_FIXES.md`](../pipeline/RAG_BOTTLENECK_FIXES.md) | Past pipeline fixes (embed prefix, sparse threshold, etc.) | Reference |

---

## Priority Board

### P0 — Do This Week (CRITICAL)

| # | Task | Doc | Status |
|---|---|---|---|
| P0-1 | Rotate Qdrant API key | [Security](RAG_SECURITY_POSTURE.md#p0-1--rotate-qdrant-api-key) | `[ ] OPEN` |
| P0-2 | Scrub git history (filter-repo + force push) | [Security](RAG_SECURITY_POSTURE.md#p0-2--scrub-git-history) | `[ ] OPEN` |
| P0-3 | Harden cosine gate to hard-abort | [Security](RAG_SECURITY_POSTURE.md#p0-3--harden-cosine-gate-hard-abort) | `[ ] OPEN` |
| P0-4 | n8n webhook — add HMAC/API key auth | [Security](RAG_SECURITY_POSTURE.md#p0-4--n8n-webhook-authentication) | `[ ] OPEN` |
| P0-5 | Audit log for all Qdrant upserts | [Security](RAG_SECURITY_POSTURE.md#p0-5--audit-log-for-qdrant-upserts) | `[ ] OPEN` |

### P1 — 2–4 Weeks

| # | Task | Doc | Status |
|---|---|---|---|
| P1-1 | Source allowlisting in rag_capture.py | [Security](RAG_SECURITY_POSTURE.md#p1-1--source-allowlisting-in-rag_capturepy) | `[ ] OPEN` |
| P1-2 | Payload schema validation at ingestion | [Security](RAG_SECURITY_POSTURE.md#p1-2--payload-schema-validation-at-ingestion) | `[ ] OPEN` |
| P1-3 | Chunk provenance fields | [Security](RAG_SECURITY_POSTURE.md#p1-3--chunk-provenance-fields) | `[ ] OPEN` |
| P1-4 | Knowledge Expansion defense | [Security](RAG_SECURITY_POSTURE.md#p1-4--knowledge-expansion-defense) | `[ ] OPEN` |
| P1-5 | Embedding anomaly detector | [Security](RAG_SECURITY_POSTURE.md#p1-5--embedding-anomaly-detector) | `[ ] OPEN` |
| E-1 | Build labeled eval set (30 queries) | [Eval](../quality/RAG_EVAL_HARNESS.md#6-eval-harness--how-to-run) | `[ ] OPEN` |
| E-2 | Run first MRR@5 / hit-rate baseline measurement | [Eval](../quality/RAG_EVAL_HARNESS.md#5-baseline-vs-current-comparison) | `[ ] OPEN` |
| E-3 | Run verify_embed_cosine.py on 10 random stored chunks | [Eval](../quality/RAG_EVAL_HARNESS.md#4-embed-prefix-alignment-validation) | `[ ] OPEN` |

### P2 — 1–3 Months

| # | Task | Doc | Status |
|---|---|---|---|
| P2-1 | Forensics snapshot vector | [Security](RAG_SECURITY_POSTURE.md#p2-1--forensics-snapshot-vector) | `[ ] OPEN` |
| P2-2 | LLM citation verification | [Security](RAG_SECURITY_POSTURE.md#p2-2--llm-citation-verification) | `[ ] OPEN` |
| P2-3 | Existing chunk provenance backfill | [Security](RAG_SECURITY_POSTURE.md#p2-3--existing-chunk-provenance-backfill) | `[ ] OPEN` |
| P2-4 | Automated red team cron (weekly probe) | [Security](RAG_SECURITY_POSTURE.md#p2-4--automated-red-team-cron) | `[ ] OPEN` |

---

## Quick Status Update — How To

Follow [`../reference/TRACKING_STATUS_STANDARD.md`](../reference/TRACKING_STATUS_STANDARD.md).

Status source of truth:
- Security hardening tasks: update the canonical section in `RAG_SECURITY_POSTURE.md`.
- Eval tasks: update the canonical metric/task row in `../quality/RAG_EVAL_HARNESS.md`.
- This file is an index. When status changes, refresh this board from the canonical source instead of treating it as a second source of truth.

Allowed status values: `[ ] OPEN`, `[~] IN PROGRESS`, `[x] DONE (YYYY-MM-DD)`, `[!] BLOCKED`, `[ ] DEFERRED`, `[x] OBSOLETE (YYYY-MM-DD)`.

---

## Open Questions (NEEDS VALIDATION)

- [x] Has Qdrant API key `0aa9f…` been rotated since the scrub commit? Yes — see `RAG_SECURITY_POSTURE.md` P0-1 evidence.
- [ ] Does the n8n HTTP webhook currently require any authentication header?
- [ ] Has `verify_embed_cosine.py` been run against live `knowledge_v2` corpus?
- [x] What is the current chunk count in `knowledge_v2`? Live VM verification on 2026-04-30: `points_count=368`, `indexed_vectors_count=371`, dense=`dense`, sparse=`sparse`, `sparse.modifier=idf`.

---

*Last updated: 2026-04-30 · Initiative owner: Figur Ulul Azmi*
