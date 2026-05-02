---
id: 2026-04-30-next-rag-power-improvements-after-vm105-001
date: 2026-04-30
source: claude-code-cli
collection: checkpoints
project: homelab
chunk_type: checkpoint
topic: Next RAG power improvements after VM105 auth
tags: [homelab, vm-b1, rag, checkpoint, vm105, reembed]
related: []
session_type: checkpoint
environment: homelab
git_branch: 
status: in_progress
chunk_source: code
hypothesis: Highest ROI is re-embedding corpus through contextual retrieval first, then adding eval-driven revision queue and ingestion provenance/schema gates
next_step: Run rag resume, then execute parallel tracks: A) P4-C re-embed corpus and before/after eval, B) P3.3 eval revision queue design/implementation, C) Security P1-2/P1-3 ingestion schema and provenance review
blocking_question: 
token_trigger: session_end
session_number: 1
files_modified: []
decisions_made: [c619200 Enhance VM105 security and functionality; c20e438 Update documentation and scripts for RAG pipeline enhancements; 46c9d82 feat: implement tracking status standard across documentation for consistency; edccbc7 feat: add documentation for fixing SSH login issues for sysadmin user; fde5120 feat: add bootstrap checklist for new device/server in documentation]
parent_id: 
---

## CHECKPOINT: Next RAG power improvements after VM105 auth

### Problem
VM105 webhook auth and auto-push are now fixed, and docs show the next RAG power improvements are not reranker-first. The remaining work should focus on retrieval quality and feedback loops while preserving the rag-tools source-of-truth separation.

### Progress
VM105 n8n ingest now uses a secret-bearing webhook path, local auto-push works after syncing N8N_WEBHOOK_SECRET, and the latest VM105 hardening summary was pushed to Qdrant. The docs audit identified the next priority as P4-C full corpus re-embed through n8n contextual retrieval, followed by P3.3 eval-to-revision-queue, then Security P1-2 payload schema validation and P1-3 chunk provenance fields.

### Parallel Task Breakdown
- Track A: Run before eval baseline, re-push `.claude/summaries/*.md` through `~/scripts/push-to-qdrant.sh`, then run after eval and compare Hit@1, Hit@3, MRR, NDCG@5, latency, and sparse-noise regressions. Update `docs/planning/RAG_EXTERNAL_BRAIN_PLAN.md`, `docs/planning/RAG_V2_ROADMAP.md`, and `docs/quality/RAG_EVAL_HARNESS.md` with evidence.
- Track B: Inspect `scripts/eval-retrieval-quality.py` and `~/scripts/rag-capture-v2/rag_capture.py` to design P3.3. Implement `~/scripts/.rag_revision_queue.md` append behavior for weak eval queries and surface queue summary in `rag status`.
- Track C: Inspect n8n workflow `~/scripts/n8n-workflows/ingest-knowledge-v2.json` and `~/scripts/push-to-qdrant.sh` for Security P1-2/P1-3. Add or plan strict ingest payload validation plus provenance fields: ingested_by, ingested_at, push_method, payload_sha256, embed_model, embed_prefix_version.
- Track D: Keep TEI/BGE reranker blocked until after P4-C and harder eval prove measurable gap.

### Key Facts
- P4-C is still OPEN in `docs/planning/RAG_EXTERNAL_BRAIN_PLAN.md` and is the recommended first task.
- P3.3 is still OPEN in `docs/planning/RAG_V2_ROADMAP.md` and should create an eval-driven chunk revision queue.
- Security P1-2 and P1-3 are still OPEN in `docs/security/RAG_SECURITY_POSTURE.md`.
- TEI plus BGE reranker remains BLOCKED until re-embed and harder eval show a measurable reranker gap.
