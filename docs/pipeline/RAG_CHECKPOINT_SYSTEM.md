# RAG Checkpoint System — Session Continuity

## Problem

Claude CLI has a 5-hour token rate limit. Complex features often require multiple sessions.
Without checkpoints, each new session must re-explore the codebase from scratch, costing
3,000–8,000 tokens before any real work begins. Prior capture pipeline only handled
*solved* problems (`knowledge_v2`); there was no way to capture *in-progress momentum*.

## Solution: 3-Collection Architecture

| Collection | Purpose | Status field |
|-----------|---------|-------------|
| `knowledge_v2` | Solved problems, lessons learned | `solved` |
| `checkpoints` | In-progress session snapshots | `in_progress` |
| `architecture` | Permanent architectural decisions | `stable` |

---

## Pipeline Flow

```
SESSION 1
─────────────────────────────────────────────────────────────────
  Token 0%  ──► Normal work
  Token 75% ──► EARLY WARNING: rag checkpoint --quick   (~300 tok)
  Token 85% ──► HARD LIMIT:   rag checkpoint (full)   (~1500 tok)
                               └─► saves to .claude/checkpoints/
                               └─► push to Qdrant: checkpoints collection
  /clear or session end
─────────────────────────────────────────────────────────────────

SESSION 2
─────────────────────────────────────────────────────────────────
  Start ──► rag resume
             │
             ├─ FOUND in_progress ──► load fields, NO file exploration
             │                        rtk read <files_modified only>
             │                        execute next_step directly
             │
             └─ NOT FOUND ──► normal RAG-first protocol

  Problem solved ──► rag promote --file .claude/checkpoints/...
                      └─► status: solved, collection: knowledge_v2
                      └─► push to Qdrant: knowledge_v2 collection
─────────────────────────────────────────────────────────────────
```

### Before vs After

| | Without Checkpoint | With Checkpoint |
|--|---|---|
| Session start | Re-explore 5-10 files | `rag resume` → load fields |
| Token cost to resume | 3,000-8,000 tokens | 400-800 tokens |
| Savings | baseline | **~75-90% reduction** |

---

## Token Budget (checkpoint capture)

The checkpoint itself MUST NOT consume more than 15% of remaining tokens.
Achieved by writing entirely from active context — zero new file reads.

| What | How | ~Tokens |
|------|-----|---------|
| Body (Problem / Progress / Key Facts) | Claude writes from memory | 800-1200 |
| `files_modified` | `rtk git diff --name-only HEAD` (auto) | 50 |
| `decisions_made` | `rtk git log --oneline -5` (auto) | 100 |
| CLI heredoc overhead | pipe + Python stdout | 150 |
| **Total** | | **~1,100-1,500** |

At 200K budget, 85% used = 30K remaining. Checkpoint uses ~1,500 = **5% of remaining**.

---

## Commands Reference

### `rag checkpoint` — save in-progress state

```bash
# Standard (trigger: 85%)
cat <<'RAGCHK' | rag checkpoint -p PROJECT --topic "..." \
  --next-step "exact action: src/X.cs:89" \
  --hypothesis "current working theory" \
  --trigger "85%"
### Problem
[what is being solved]
### Progress
[what was done this session]
### Key Facts
- fact 1
- fact 2
- fact 3
RAGCHK

# Emergency quick mode (trigger: 75%, <5% tokens left)
rag checkpoint -p PROJECT --topic "..." \
  --next-step "src/X.cs:89 null ref fix" --trigger "75%" --quick
```

**Flags:**

| Flag | Required | Description |
|------|----------|-------------|
| `-p PROJECT` | Yes | homelab / petrochina-eproc / etc |
| `--topic` | Yes | Max 60 chars ASCII |
| `--next-step` | Yes | **Must be specific**: `file.cs:line` if possible |
| `--hypothesis` | No | Current working theory |
| `--blocking` | No | Unanswered blocker question |
| `--trigger` | No | `85%` / `75%` / `manual` / `session_end` |
| `--quick` | No | Skip body, ~300 tokens emergency mode |

After saving, push immediately:
```bash
bash ~/scripts/push-to-qdrant.sh .claude/checkpoints/YYYY-MM-DD-*.md
```

---

### `rag resume` — session start protocol

```bash
rag resume              # all projects
rag resume -p homelab   # filter by project
```

Output format (compact, RTK-style):
```
==============================================================
   📍 OPEN CHECKPOINTS (1) -- load before file exploration
==============================================================

  File       : 2026-04-18-qdrant-migration-001.md
  Topic      : Qdrant hybrid migration
  Session    : #1 | Trigger: 85%
  Hypothesis : BM25 sparse vector config is wrong
  Next step  : fix src/Infrastructure/AI/QdrantService.cs:145
  Files      : [src/Infrastructure/AI/QdrantService.cs:140-180]
  Blocking   : -
  RTK reads  : rtk read src/Infrastructure/AI/QdrantService.cs
  Promote    : rag promote --file .claude/checkpoints/2026-04-18-...md
```

**On FOUND:** skip all Glob/Grep exploration. Execute `RTK reads` line, then `next_step`.

---

### `rag promote` — solved checkpoint → knowledge_v2

```bash
rag promote --file .claude/checkpoints/2026-04-18-foo-001.md
# optional: --output 2026-04-18-foo-solved.md

# Then push to knowledge_v2
bash ~/scripts/push-to-qdrant.sh .claude/summaries/2026-04-18-foo-promoted.md
```

What `promote` does:
- Sets `status: solved`, `collection: knowledge_v2`
- Sets `parent_id` linking to original checkpoint
- Saves to `.claude/summaries/`
- Updates original checkpoint file to `status: solved` (audit trail)

---

## Checkpoint Frontmatter Schema

Standard fields (all chunk types) + checkpoint-specific additions:

```yaml
---
id: 2026-04-18-qdrant-migration-001
date: 2026-04-18
source: claude-code-cli
collection: checkpoints            # routes push-to-qdrant.sh
project: homelab
chunk_type: checkpoint
topic: Qdrant hybrid migration
tags: [homelab, vm-b1, qdrant, migration]
status: in_progress                # in_progress | solved | abandoned
token_trigger: "85%"
session_number: 1
# --- Momentum fields ---
hypothesis: BM25 sparse vector config is wrong
next_step: fix src/Infrastructure/AI/QdrantService.cs:145
blocking_question: ""
files_modified: [src/Infrastructure/AI/QdrantService.cs, src/appsettings.json]
decisions_made: [87483d3 feat: delete obsolete summaries; db09236 feat: update settings]
parent_id: ""                      # filled by rag promote
---
```

---

## Session Workflow (complete)

```
Step 1: New session
   └─► rag resume
         FOUND  → skip exploration, execute next_step
         EMPTY  → normal RAG-first protocol

Step 2: Mid-session 75% token warning
   └─► rag checkpoint --quick (emergency snapshot)
   └─► push .claude/checkpoints/...

Step 3: Mid-session 85% token limit
   └─► rag checkpoint (full body)
   └─► push .claude/checkpoints/...
   └─► /clear (safe — checkpoint is in Qdrant)

Step 4: Problem solved in any session
   └─► rag promote --file .claude/checkpoints/...
   └─► push .claude/summaries/...-promoted.md  (to knowledge_v2)

Step 5: Session end (knowledge chunks)
   └─► rag merge --output YYYY-MM-DD-slug.md
   └─► push .claude/summaries/...
```

---

## Hard Rules (Anti-Patterns)

| Rule | Why |
|------|-----|
| NEVER read files during checkpoint write | Each file read costs 200-500 tokens — violates 15% budget |
| NEVER leave `next_step` vague ("fix the bug") | Vague next_step forces re-exploration in next session |
| NEVER skip `rag resume` at session start | Miss checkpoint = waste 3K-8K tokens on re-exploration |
| NEVER keep checkpoint as `in_progress` after solved | Promotes clutter; blocks resume logic from finding real open work |
| NEVER push checkpoint to `knowledge_v2` | Wrong collection — checkpoint schema has extra fields n8n may not handle |

---

## Files Modified by This Implementation

| File | Change |
|------|--------|
| `scripts/rag-capture-v2/rag_capture.py` | Added `cmd_checkpoint`, `cmd_resume`, `cmd_promote`, `save_checkpoint`, `auto_detect_files_modified`, `auto_detect_decisions`, `validate_checkpoint_content`; extended `build_frontmatter` with checkpoint fields; extended `VALID_TYPES`, `VALID_STATUSES`; added `checkpoints_subdir` to `DEFAULT_CONFIG` |
| `scripts/push-to-qdrant.sh` | `DOC_COLLECTION=$(extract_field "collection")`; replaced hardcoded `"knowledge_v2"` with `$collection` in jq payload and summary output |
| `CLAUDE.md` | Added Session Start Protocol section and Checkpoint Trigger Rules section |
| `docs/RAG_CAPTURE_PIPELINE_GAPS.md` | Gap tracker (G1, G2, G4, SPOF-1, SPOF-2 addressable) |

---

*Implemented: 2026-04-18 | rag_capture.py v2 | push-to-qdrant.sh v2*
