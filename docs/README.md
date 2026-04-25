# docs/ — Navigation Index

All documents in this folder cover the RAG knowledge pipeline for `rag-gateway-mini`
(homelab + petrochina-eproc projects). Organized by purpose below.

---

## Active Work (read these first)

| Document | Purpose | Status |
|---|---|---|
| [RAG_V2_ROADMAP.md](RAG_V2_ROADMAP.md) | Active feature roadmap for `knowledge_v2` — P1/P2/P3 items, strategic goal, success criteria | **Active** |
| [RAG_QDRANT_AUDIT.md](RAG_QDRANT_AUDIT.md) | Intelligence audit: 5-dimension health score + fix tracker | **Active** |
| [COVERAGE_KNOWLEDGE_TRACKER.md](COVERAGE_KNOWLEDGE_TRACKER.md) | Dedicated tracker: before/after history for every Coverage knowledge improvement | **Active** |

---

## Fix Trackers

| Document | Covers | Use When |
|---|---|---|
| [RAG_BOTTLENECK_FIXES.md](RAG_BOTTLENECK_FIXES.md) | Pipeline A (write/ingest) and Pipeline B (read/retrieve) bottleneck fixes with test evidence | Diagnosing slow/wrong retrieval, checking fix history |
| [RAG_CAPTURE_PIPELINE_GAPS.md](RAG_CAPTURE_PIPELINE_GAPS.md) | Gaps in the chunk capture pipeline (`rag add` → `rag merge` → `push-to-qdrant.sh` → n8n → Qdrant) | Debugging why chunks land incorrectly or get lost |

---

## System Design & Reference

| Document | Covers | Use When |
|---|---|---|
| [RAG_CHECKPOINT_SYSTEM.md](RAG_CHECKPOINT_SYSTEM.md) | Session continuity: `rag checkpoint`, `rag resume`, `rag promote` commands and 3-collection architecture | Understanding checkpoint workflow, adding new checkpoint fields |
| [RAG_EXTERNAL_BRAIN_PLAN.md](RAG_EXTERNAL_BRAIN_PLAN.md) | Strategic improvement plan: Phase 1 reliability → Phase 2 quality → Phase 3 implementer-grade chunks | Planning multi-session improvement sprints |

---

## Reading Order for New Contributors

1. `RAG_V2_ROADMAP.md` — understand the strategic goal and current state
2. `RAG_QDRANT_AUDIT.md` — understand current health and open issues
3. `RAG_BOTTLENECK_FIXES.md` — understand what's already been fixed in retrieval
4. `RAG_CAPTURE_PIPELINE_GAPS.md` — understand what's been fixed in capture
5. `RAG_CHECKPOINT_SYSTEM.md` — understand session continuity mechanics

---

## Document Ownership

All docs are written and maintained by Claude Code sessions.
Update a document's status when a fix is deployed — stale status is worse than no status.

Last index update: 2026-04-25
