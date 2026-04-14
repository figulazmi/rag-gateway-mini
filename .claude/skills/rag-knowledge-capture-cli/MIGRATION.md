# RAG Knowledge Capture Skill — Migration Guide

## What Changed (2026-04-14)

The skill was updated to use the `rag` CLI (`rag_capture.py`) instead of Claude
writing `.md` files manually via the `Write` tool.

---

## Before vs After

### Before (v1 — Direct Write)

```
Claude generates chunk content
    ↓
Claude calls Write tool
    → creates .claude/summaries/YYYY-MM-DD-topic.md directly
    ↓
Claude prints push command manually
    ↓
User runs: bash ~/scripts/push-to-qdrant.sh ...
```

**Problems:**
- Claude duplicated frontmatter logic already in `rag_capture.py`
- `~/scripts/.rag_drafts/` was never used → `rag list`, `rag status`, `rag remind` always empty
- Draft lifecycle (`rag add` → `rag merge` → `rag clear`) was completely bypassed
- Collection was hardcoded as `knowledge` — did not reflect actual target (`knowledge_v2`)
- SESSION METADATA block written manually by Claude, inconsistent with tool output

### After (v2 — rag CLI pipeline)

```
Claude generates chunk content
    ↓
Claude calls Bash: cat << 'CONTENT' | rag add -p PROJECT -t TYPE --topic "..." --tags "..."
    → draft saved to ~/scripts/.rag_drafts/chunk_NNN.md
    → frontmatter generated automatically by rag_capture.py
    ↓ (repeat per chunk)
Claude calls Bash: rag merge --output YYYY-MM-DD-slug.md
    → drafts consolidated into .claude/summaries/YYYY-MM-DD-slug.md
    → SESSION METADATA appended automatically
    → push reminder printed by tool
    ↓
User runs: bash ~/scripts/push-to-qdrant.sh .claude/summaries/YYYY-MM-DD-slug.md
```

**Benefits:**
- Single source of truth: frontmatter schema lives in `rag_capture.py` only
- `rag list`, `rag status`, `rag remind` reflect real session state
- Collection target (`knowledge_v2`) comes from `~/.rag_config.json`
- SESSION METADATA generated consistently by the tool
- Draft folder can be inspected/managed between sessions

---

## Full Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  SESSION                                                     │
│                                                             │
│  User invokes /rag-knowledge-capture-cli                    │
│         ↓                                                   │
│  Claude analyzes session → identifies N distinct chunks     │
│         ↓                                                   │
│  For each chunk (1..N):                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Claude writes chunk body (Context/Problem/Solution) │   │
│  │  Claude calls via Bash:                              │   │
│  │                                                      │   │
│  │  cat << 'CONTENT' | rag add \                        │   │
│  │    -p PROJECT -t TYPE \                              │   │
│  │    --topic "..." --tags "..."                        │   │
│  │  [chunk body]                                        │   │
│  │  CONTENT                                             │   │
│  │         ↓                                            │   │
│  │  rag_capture.py saves to:                            │   │
│  │    ~/scripts/.rag_drafts/chunk_NNN.md               │   │
│  │  (with auto-generated frontmatter)                   │   │
│  └─────────────────────────────────────────────────────┘   │
│         ↓                                                   │
│  Claude calls via Bash:                                     │
│    rag merge --output YYYY-MM-DD-slug.md                    │
│         ↓                                                   │
│  rag_capture.py:                                            │
│    - merges all drafts from ~/scripts/.rag_drafts/          │
│    - writes .claude/summaries/YYYY-MM-DD-slug.md            │
│    - appends SESSION METADATA block                         │
│    - prints push reminder                                   │
│    - prompts to clear draft folder                          │
└─────────────────────────────────────────────────────────────┘
         ↓
  User runs push command:
    bash ~/scripts/push-to-qdrant.sh \
      .claude/summaries/YYYY-MM-DD-slug.md
         ↓
  push-to-qdrant.sh → n8n webhook → n8n workflow
         ↓
  n8n generates embeddings (dense + sparse BM25)
         ↓
  Qdrant collection: knowledge_v2
```

---

## Key File Locations

| File | Purpose |
|------|---------|
| `~/.claude/commands/rag-knowledge-capture-cli.md` | Skill definition loaded by Claude Code |
| `~/scripts/rag-capture-v2/rag_capture.py` | CLI tool (installed as `rag` via rag-setup.sh) |
| `~/.rag_config.json` | Global config: collection name, push script path, projects |
| `~/scripts/.rag_drafts/chunk_NNN.md` | Intermediate draft storage (per `rag add` call) |
| `.claude/summaries/YYYY-MM-DD-[topic].md` | Final merged output (per `rag merge` call) |
| `~/scripts/push-to-qdrant.sh` | Push merged file to Qdrant via n8n webhook |

---

## rag CLI Quick Reference

```bash
# Add a chunk (Claude does this automatically)
cat << 'CONTENT' | rag add -p homelab -t feature \
  --topic "My Feature Title" \
  --tags "tag1,tag2,tag3" \
  --branch main \
  --environment homelab
## CHUNK 1: Title
### Context
...
CONTENT

# Check pending drafts
rag list

# Merge all drafts into final file
rag merge --output 2026-04-14-my-session.md

# View current state
rag status

# Print push reminder
rag remind

# Discard all drafts (if session was not useful)
rag clear

# Show config
rag config --show
```

---

## Config: ~/.rag_config.json

```json
{
  "qdrant_collection": "knowledge_v2",
  "push_script": "~/scripts/push-to-qdrant.sh",
  "summaries_subdir": ".claude/summaries",
  "author": "Figur Ulul Azmi",
  "projects": {
    "homelab":          { "default_environment": "homelab", "default_branch": "main" },
    "petrochina-eproc": { "default_environment": "dev",     "default_branch": "feature/" },
    "mit-internal":     { "default_environment": "dev",     "default_branch": "main" },
    "homeplate":        { "default_environment": "dev",     "default_branch": "feature/" }
  }
}
```

Change `qdrant_collection` here to switch target collection globally — no code change needed.

---

## Note: SKILL.md in This Directory

`SKILL.md` in this repo directory is the **source/reference copy** of the skill.
The **active copy** loaded by Claude Code is at:

```
~/.claude/commands/rag-knowledge-capture-cli.md
```

Keep both files in sync when making changes.
