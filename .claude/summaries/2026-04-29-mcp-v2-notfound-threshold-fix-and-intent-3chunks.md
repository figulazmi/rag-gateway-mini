---
id: 2026-04-29-mcp-v2-notfound-threshold-fix-and-intent-001
date: 2026-04-29
source: claude-code-cli
collection: knowledge_v2
project: homelab
chunk_type: debug
topic: MCP v2 NOT_FOUND threshold fix and intent-aware retry homelab
tags: [homelab, vm-b1, qdrant, mcp, threshold-tuning, retrieval, rrf]
related: []
session_type: 
environment: homelab
git_branch: 
status: implemented
chunk_source: code
---

## CHUNK 1: MCP v2 NOT_FOUND threshold fix and intent-aware retry homelab
<!-- rag_chunk_meta chunk_type=debug tags=[homelab, vm-b1, qdrant, mcp, threshold-tuning, retrieval, rrf] -->

### Context
qdrant-mcp-server-v2.js on VM B1 (/opt/mcp-servers/qdrant-knowledge/) uses hybrid RRF search
against knowledge_v2 collection. Post-restoration audit revealed MCP smoke test returning 1/3 FOUND
despite relevant chunks existing in DB.

### Problem
Two retrieval failures after VM105 restoration:
1. Q3 (VM B1 Docker deployment workflow) always returned NOT FOUND via MCP even though
   the chunk existed and scored 0.671 in direct eval. Root cause: NOT_FOUND_THRESHOLD=0.50
   was calibrated for cosine similarity scores, not RRF scores. RRF top score = 1.0 only when
   a doc ranks #1 in BOTH dense and sparse legs. Single-leg rank-1 yields ~0.5, meaning borderline
   relevant docs were systematically rejected.
2. Q4 (RAG gateway hybrid BM25 threshold) had Hit@1=0 because dense leg pulled a semantically
   similar but wrong chunk to rank-1. Retry never fired because avgScore=0.5502 >= old RETRY_THRESHOLD=0.50.

### Solution
Three changes deployed to qdrant-mcp-server-v2.js (local + VM B1):
1. NOT_FOUND_THRESHOLD: 0.50 -> 0.35 (matches SCORE_THRESHOLD; RRF-appropriate lower bound)
2. RETRY_THRESHOLD: 0.50 -> 0.55 (catches borderline-avgScore queries like Q4)
3. buildRetryExpansion(): intent-aware per homelab query pattern with 3 keyword-triggered rules:
   - hybrid/rrf/bm25/threshold/score/prefetch -> adds IVectorSearchClient, QdrantQueryResponse, EnableHybridSearch
   - deployment/docker/compose/ssh/vm -> adds rag-gateway-mini deployment workflow terms
   - push-to-qdrant/n8n/webhook/frontmatter -> adds push-to-qdrant network-aware ingest terms
4. HYBRID_PREFETCH_MULT=8 constant replaces hardcoded limit*6 in searchQdrant()

### Key Facts
- RRF scores are NOT equivalent to cosine similarity; max RRF score = 1.0 requires rank-1 in all legs
- NOT_FOUND_THRESHOLD should equal SCORE_THRESHOLD (0.35) for RRF-based hybrid pipelines
- RETRY_THRESHOLD=0.55 ensures retry fires for avgScore in range [0.50, 0.55) covering borderline queries
- Intent-aware expansion must include unique tokens from target chunks (class names, function names) not generic terms
- Smoke test improved from 1/3 to 3/3 FOUND after threshold fix
- Eval Hit@1 stays 0.80 because eval bypasses MCP retry path; direct Qdrant queries unaffected by MCP logic
- HYBRID_PREFETCH_MULT=8 via eval shows no aggregate improvement vs prefetch*4; ranking quality limits performance
- Backup before each MCP patch: sudo cp ...v2.js ...v2.js.bak-YYYYMMDD

## CHUNK 2: MCP connect script wired to v1 instead of v2 causing stale collection queries
<!-- rag_chunk_meta chunk_type=debug tags=[homelab, vm-b1, qdrant, mcp, threshold-tuning, debug] -->

### Context
qdrant-mcp-server-v2.js was patched with corrected thresholds and intent-aware retry on 2026-04-29.
Claude Code MCP connects via ~/.claude/claude-mcp-connect.ps1 -> SSH -> VM B1 node script.

### Problem
After patch session ended and Claude Code was restarted, smoke tests regressed from 3/3 to 1/3 FOUND.
Root cause: claude-mcp-connect.ps1 $MCP_CMD pointed to qdrant-mcp-server.js (v1), not v2.
v1 queries COLLECTION="knowledge" (old collection), NOT_FOUND_THRESHOLD=0.65.
All knowledge_v2 chunks were invisible to MCP because v1 never queries knowledge_v2.
Additionally, ~/.qdrant-mcp.env did not exist on VM B1, so v2 would fail at startup
(v1 has API key hardcoded; v2 reads from env).

### Solution
1. claude-mcp-connect.ps1: changed $MCP_CMD to reference qdrant-mcp-server-v2.js
2. Created ~/.qdrant-mcp.env on VM B1 with QDRANT_API_KEY, chmod 600
3. Verified v2 starts clean: timeout 2 node qdrant-mcp-server-v2.js exits 0, no stderr errors
4. Claude Code restart required to load new MCP process

### Key Facts
- claude-mcp-connect.ps1 is the single wire between Claude Code and the MCP binary on VM B1
- Patching the MCP js file alone is not enough; the PS1 $MCP_CMD must point to the new file
- v1 (qdrant-mcp-server.js) queries "knowledge" collection; v2 queries "knowledge_v2"
- ~/.qdrant-mcp.env is the ONLY source for QDRANT_API_KEY for v2; without it v2 exits on startup
- After any MCP binary change, Claude Code must be restarted (process is spawned at session start)
- Smoke test false alarm: my Q3 query ("VM B1 Docker deployment") != eval Q3 ("docker compose v2 binary not found"); use exact eval query strings for valid smoke tests

## CHUNK 3: VM105 restoration docs full audit and live verification April 27 state
<!-- rag_chunk_meta chunk_type=runbook tags=[homelab, vm-b1, qdrant, mcp, n8n, docs-audit, verification] -->

### Context
rag-gateway-mini homelab RAG stack on VM B1 (192.168.18.199). After completing VM105 restoration,
a full audit of VM105_RESTORATION_PLAN.md was conducted to ensure docs matched live state.
Goal: confirm all infrastructure matches April 27 2026 target configuration.

### Problem
Post-restoration docs had 6 stale table values (S1-S6), 3 misleading sections (M1-M3),
one false alarm (B1 - n8n webhook), and incorrect Step 3 verification command (GET vs POST).
Also needed to confirm live state of all 4 pipelines matches April 27 target.

### Solution
Audit approach: run live checks on VM B1 for every component in the plan, then compare
against April 27 target. Fix all divergences in docs immediately after verification.

Fixes applied to VM105_RESTORATION_PLAN.md:
- Pipeline A/B/n8n tables: added "Pre-Restoration State (Apr 13)" and "Current Deployed" columns
- Pipeline B NOT_FOUND_THRESHOLD: marked as improved beyond Apr27 target (0.50 → 0.35 via step 7c)
- Pipeline B RETRY_THRESHOLD: corrected to show final 0.55 (not 0.50)
- n8n table 3 rows: changed from "FAILED Step 3" to "FIXED Step 3" with deployed state
- Step 5d point count: corrected 350 → 359 (live count)
- Step 0a description: added cumulative chain 0.6→0.50→0.55 and project-aware→intent-aware
- Step 6b root cause: added deeper root cause note (PS1 wiring, step 7e)
- Step 7 Results: added pre-PS1-fix warning label, canonical result is Step 7g
- Step 3 verification command: fixed from GET to POST

Live state confirmed (2026-04-29):
- MCP v2: COLLECTION=knowledge_v2, SCORE=0.35, RETRY=0.55, NOT_FOUND=0.35, PREFETCH_MULT=8
- knowledge_v2: 359 points, 359 indexed, status green, schema dense(768 Cosine)+sparse(idf)
- n8n webhook: POST=200 (active)
- PS1: points to qdrant-mcp-server-v2.js with ~/.qdrant-mcp.env sourcing
- ~/.config/qdrant-knowledge.env: exists locally (Windows), used by push-to-qdrant.sh

### Key Facts
- n8n webhooks always return GET=404; correct verification must use POST (-X POST with -d payload)
- All infrastructure matches or exceeds April 27 target; eval metrics (Hit@1=0.80) are content quality gap, not config
- Q4 semantic collision (RAG gateway hybrid BM25 query) is only fixable via chunk content improvement, not config tuning
- knowledge_v2 has 359 points (not 350 as in initial restoration record)
- Pipeline B table must have 4 columns: April27 Target, Pre-Restoration State, Current Deployed, Issue
- Any live infrastructure audit should use POST for webhook checks and direct Qdrant API for collection schema

---

## SESSION METADATA

- **Total chunks**: 3
- **Qdrant collection**: knowledge_v2
- **Generated by**: rag_capture.py v2 -- Incremental Capture
- **Author**: Figur Ulul Azmi
- **Date**: 2026-04-29
- **Unresolved items**: (fill manually if needed)