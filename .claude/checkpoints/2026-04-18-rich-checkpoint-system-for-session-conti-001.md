---
id: 2026-04-18-rich-checkpoint-system-for-session-conti-001
date: 2026-04-18
source: claude-code-cli
collection: checkpoints
project: homelab
chunk_type: checkpoint
topic: Rich checkpoint system for session continuity
tags: [homelab, vm-b1]
related: []
session_type: checkpoint
environment: homelab
git_branch: 
status: in_progress
chunk_source: code
hypothesis: All 3 new commands work; UTF-8 fix applied; push-to-qdrant.sh now routes dynamically
next_step: Run smoke test: rag checkpoint with full body + push to Qdrant checkpoints collection
blocking_question: 
token_trigger: manual
session_number: 1
files_modified: [.claude/settings.local.json, CLAUDE.md, docs/RAG_CAPTURE_PIPELINE_GAPS.md, scripts/push-to-qdrant.sh, scripts/rag-capture-v2/rag_capture.py, --- Changes ---]
decisions_made: [92ab5c9 refactor: streamline permissions in settings.local.json by removing obsolete entries and consolidating allowe...; 87483d3 Delete obsolete summaries for n8n workflow status field, contextual retrieval prepend deployment, rag-gateway...; db09236 feat: update settings.local.json and add summary for git bash path issue with rag and rtk; 4f860cb feat: implement LLM-as-reranker scaffolding and enhance validation in rag_capture.py; 1139bac feat: add evaluation report and verification summary for n8n contextual retrieval deployment]
parent_id: 
---

## CHECKPOINT: Rich checkpoint system for session continuity

### Problem
Claude CLI 5-hour token limit breaks complex multi-session feature work. Previous pipeline only captured solved problems (knowledge_v2), with no way to resume in-progress sessions without full codebase re-exploration costing 3000-8000 tokens.

### Progress
Implemented 3 new commands in rag_capture.py: checkpoint (save in-progress state), resume (show open checkpoints at session start), promote (move solved checkpoint to knowledge_v2). Updated push-to-qdrant.sh to route dynamically based on frontmatter collection field. Added Session Start Protocol and Checkpoint Trigger Rules to CLAUDE.md. Fixed Windows cp1252 UTF-8 encoding bug.

### Key Facts
- rag checkpoint saves to .claude/checkpoints/ directly, no draft-merge cycle needed
- files_modified and decisions_made auto-populated via rtk git diff + rtk git log, ~150 tokens total
- rag resume prints RTK precision read hints to eliminate codebase re-exploration on resume
- push-to-qdrant.sh now reads collection: field from frontmatter, routes to checkpoints or knowledge_v2
- Checkpoint token budget: ~1100-1500 tokens total (< 5% of 200K budget at 85% usage)
- --quick flag for emergency capture when < 5% tokens remaining, ~300 tokens
- 85% token trigger (not 90%) gives 15% safety buffer for checkpoint write
