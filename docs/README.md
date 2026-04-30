# docs/ — Navigation Index

All documents cover the RAG knowledge pipeline for `rag-gateway-mini`
(stack: Qdrant `knowledge_v2` · nomic-embed-text · Ollama · n8n · ASP.NET Core 9 · VM B1).

> All tracking docs should follow [`reference/TRACKING_STATUS_STANDARD.md`](reference/TRACKING_STATUS_STANDARD.md) to avoid stale duplicate status checklists.

---

## Folder Structure

```
docs/
  pipeline/    — ingestion & retrieval pipeline: fixes, gaps, session continuity
  quality/     — retrieval evaluation, Qdrant health audit, coverage tracking
  security/    — security posture hardening & threat model tracker
  planning/    — roadmaps, strategic plans, restoration plans
  reference/   — manual book & runbooks
```

---

## pipeline/ — Ingestion & Retrieval

| Document | Purpose | Status |
|---|---|---|
| [RAG_BOTTLENECK_FIXES.md](pipeline/RAG_BOTTLENECK_FIXES.md) | Pipeline A (write/ingest) and Pipeline B (read/retrieve) bottleneck fixes with test evidence | Active |
| [RAG_CAPTURE_PIPELINE_GAPS.md](pipeline/RAG_CAPTURE_PIPELINE_GAPS.md) | Gap analysis: `rag add` → `rag merge` → `push-to-qdrant.sh` → n8n → Qdrant | Active |
| [RAG_CHECKPOINT_SYSTEM.md](pipeline/RAG_CHECKPOINT_SYSTEM.md) | Session continuity: `rag checkpoint`, `rag resume`, `rag promote` commands | Reference |

---

## quality/ — Retrieval Quality

| Document | Purpose | Status |
|---|---|---|
| [RAG_EVAL_HARNESS.md](quality/RAG_EVAL_HARNESS.md) | Benchmark metrics (MRR@5, faithfulness), labeled query set, score tracking | Active |
| [RAG_QDRANT_AUDIT.md](quality/RAG_QDRANT_AUDIT.md) | 5-dimension health audit: score 6.8/10 → 8.1/10 + fix tracker | Active |
| [COVERAGE_KNOWLEDGE_TRACKER.md](quality/COVERAGE_KNOWLEDGE_TRACKER.md) | Before/after history for every coverage improvement | Active |

---

## security/ — Security Posture

| Document | Purpose | Status |
|---|---|---|
| [RAG_POWER_SECURITY_INDEX.md](security/RAG_POWER_SECURITY_INDEX.md) | **Entry point** — priority board P0/P1/P2 with quick nav to all items | Active |
| [RAG_SECURITY_POSTURE.md](security/RAG_SECURITY_POSTURE.md) | Phase 1–3 hardening tracker: threat model, fix steps, verification commands | Active |

---

## planning/ — Roadmaps & Plans

| Document | Purpose | Status |
|---|---|---|
| [RAG_V2_ROADMAP.md](planning/RAG_V2_ROADMAP.md) | Active feature roadmap for `knowledge_v2` — P1/P2/P3 priorities, strategic goal | **Active — read before any pipeline change** |
| [RAG_EXTERNAL_BRAIN_PLAN.md](planning/RAG_EXTERNAL_BRAIN_PLAN.md) | Strategic improvement plan: reliability → quality → implementer-grade chunks | Reference |
| [VM105_RESTORATION_PLAN.md](planning/VM105_RESTORATION_PLAN.md) | VM105 restore gap checklist against VM B1 April 27 target; live verification shows current VM has 368 `knowledge_v2` points | Active |

---

## reference/ — Manual & Runbooks

| Document | Purpose | Status |
|---|---|---|
| [RAG_MANUAL_BOOK.md](reference/RAG_MANUAL_BOOK.md) | Complete operational manual: commands, config, troubleshooting, architecture | Reference |
| [RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md](reference/RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md) | Bootstrap/disaster-recovery checklist for new local device or server rebuild | Active |
| [TRACKING_STATUS_STANDARD.md](reference/TRACKING_STATUS_STANDARD.md) | Canonical status table standard for all docs trackers | Active |

---

## Reading Order (new contributor / new session)

1. [`planning/RAG_V2_ROADMAP.md`](planning/RAG_V2_ROADMAP.md) — strategic goal and current priorities
2. [`quality/RAG_QDRANT_AUDIT.md`](quality/RAG_QDRANT_AUDIT.md) — current health score and open issues
3. [`pipeline/RAG_BOTTLENECK_FIXES.md`](pipeline/RAG_BOTTLENECK_FIXES.md) — what's already been fixed in retrieval
4. [`pipeline/RAG_CAPTURE_PIPELINE_GAPS.md`](pipeline/RAG_CAPTURE_PIPELINE_GAPS.md) — what's been fixed in capture
5. [`security/RAG_POWER_SECURITY_INDEX.md`](security/RAG_POWER_SECURITY_INDEX.md) — security hardening status

---

## Quick Status: Open Priorities

| Area | Highest open item | Doc |
|---|---|---|
| Security | P0-3: Harden cosine gate (hard abort on verification failure) | [security/RAG_SECURITY_POSTURE.md](security/RAG_SECURITY_POSTURE.md#p0-3--harden-cosine-gate-hard-abort) |
| Quality | Expand measured baseline beyond retrieval-only metrics (faithfulness, latency, relevance) | [quality/RAG_EVAL_HARNESS.md](quality/RAG_EVAL_HARNESS.md#5-baseline-vs-current-comparison) |
| Pipeline | IDF weighting (Opsi C) — deferred (revisit after corpus diversity and post-baseline metrics) | [pipeline/RAG_BOTTLENECK_FIXES.md](pipeline/RAG_BOTTLENECK_FIXES.md#7--idf-weighting-mismatch-between-c-and-qdrant-bm25-) |
| Reference | New device/server bootstrap checklist is available for future migration/rebuilds | [reference/RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md](reference/RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md) |
| Planning | VM105 restore checklist: current VM verified at 368 points; use remaining-fix list only when rebuilding from Apr 13 backup | [planning/VM105_RESTORATION_PLAN.md](planning/VM105_RESTORATION_PLAN.md) |

---

*Last updated: 2026-04-30 · Owner: Figur Ulul Azmi*  
*Update this index when adding new docs or changing subfolder structure.*
