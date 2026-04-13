---
id: 2026-04-13-rag-pipeline-upgrade-6-templates
date: 2026-04-13
source: claude-code-cli
project: homelab
chunk_type: feature
topic: RAG Pipeline Upgrade - 6 Typed Templates and Global RAG-First Protocol
tags: [rag, qdrant, knowledge-capture, n8n, claude-code, homelab, push-to-qdrant, implemented]
related: [rag-gateway-mini, push-to-qdrant, knowledge-ingest]
session_type: feature
environment: homelab
git_branch: main
status: implemented
chunk_source: ops
---

## CHUNK 1: RAG Knowledge Capture Skill - 6 Typed Templates

### Context
The `rag-knowledge-capture-cli` SKILL.md previously had a single universal
problem-solution template (debug-only). This forced all session knowledge into
one format regardless of whether the session was a bug fix, feature build,
deployment procedure, or architecture decision.

### Requirements
- Support 6 distinct knowledge chunk types for better RAG retrieval precision
- Add mandatory `chunk_type` frontmatter field that determines which template to use
- Enforce one chunk_type per file (separate files for mixed-type sessions)
- Maintain backward compatibility with existing `.md` summaries

### Architecture Decision
`chunk_type` is added as a REQUIRED frontmatter field. Its value dictates the
template body structure for the chunk. A CHUNK TYPE SELECTION GUIDE (table +
decision tree) was added to help Claude select the correct type. CHUNK SPLITTING
RULES updated to enforce one chunk_type per file — mixed sessions generate
separate `.md` files.

### Implementation
File modified: `.claude/skills/rag-knowledge-capture-cli/SKILL.md`

6 templates added, each with distinct section structure:
- `debug`: Context → Problem → Solution → Key Facts → Code → Caveats
- `feature`: Context → Requirements → Architecture Decision → Implementation → Key Facts → Code → Lessons Learned
- `runbook`: Context → Prerequisites → Steps → Verification → Key Facts → Troubleshooting
- `pattern`: Context → When to Use → When NOT to Use → Implementation → Key Facts → Code → Variations
- `decision`: Context → Decision Required → Options Considered → Decision → Rationale → Consequences → Key Facts
- `reference`: Context → Content → Key Facts → Related Commands

Additional additions:
- `deprecated` added to `status` field options
- `ops` added to `chunk_source` field options
- `feature-retrospective` and `ops-documentation` added to `session_type`
- `homeplate` added to `project` options

### Key Facts
- `chunk_type` is REQUIRED in frontmatter — no default, must be explicitly set
- One .md file MUST contain only one chunk_type — mixed sessions = separate files
- CHUNK TYPE SELECTION GUIDE: error/bug=debug, build feature=feature, how-to=runbook, reusable approach=pattern, why A not B=decision, factual data=reference
- HARD RULES updated: NEVER mix chunk_types in one file, ALWAYS use correct template body
- Backward-compatible: old summaries without chunk_type are not broken

---

## CHUNK 2: push-to-qdrant.sh - Expanded Qdrant Payload Fields

### Context
`~/scripts/push-to-qdrant.sh` extracted only 5 frontmatter fields (`id`, `date`,
`project`, `topic`, `source`) and sent a minimal JSON payload to Qdrant via n8n
webhook. The 3 new fields from Phase 1 (`chunk_type`, `status`, `chunk_source`)
plus 5 existing frontmatter fields (`tags`, `session_type`, `environment`,
`git_branch`, `related`) were silently dropped — never reaching Qdrant.

### Requirements
- Forward all 13 frontmatter fields as Qdrant vector metadata
- Show `chunk_type` in push summary display for quick verification
- Maintain backward compatibility for old .md files without new fields

### Implementation
Three edit locations in `~/scripts/push-to-qdrant.sh`:

**1. PARSE FRONTMATTER section** — added 8 new `extract_field` calls after `DOC_SOURCE`:
```bash
DOC_TAGS=$(extract_field "tags")
DOC_SESSION_TYPE=$(extract_field "session_type")
DOC_ENVIRONMENT=$(extract_field "environment")
DOC_GIT_BRANCH=$(extract_field "git_branch")
DOC_RELATED=$(extract_field "related")
DOC_CHUNK_TYPE=$(extract_field "chunk_type")
DOC_STATUS=$(extract_field "status")
DOC_CHUNK_SOURCE=$(extract_field "chunk_source")
```

**2. jq --arg block** — 8 new `--arg` entries added before `--arg chunk_num`

**3. JSON body** — expanded from 11 to 19 fields; new fields: tags, session_type, environment, git_branch, related, chunk_type, status, chunk_source

**4. Display summary** — added `echo "  Type     : $DOC_CHUNK_TYPE"` after Topic line

### Key Facts
- `extract_field` has `|| echo "unknown"` fallback — old .md files without new fields return "unknown", not error
- Qdrant payload now carries 19 fields including chunk_type, status, and chunk_source for filtering
- Display summary now shows `Type : [chunk_type]` — use this to verify parsing during push
- n8n webhook path unchanged: `webhook/knowledge-ingest`
- Script is at `~/scripts/push-to-qdrant.sh` (Git Bash path: `/c/Users/Clandesitine/scripts/push-to-qdrant.sh`)

---

## CHUNK 3: RAG-First Protocol - Global CLAUDE.md Configuration

### Context
Claude Code was silently falling back to training data for project-specific
questions (architecture, patterns, past decisions, deployment procedures). The
global `~/.claude/CLAUDE.md` had a MANDATORY Session Start section but no
explicit enforcement for RAG-first behavior during Q&A — only at session start.

### Requirements
- Enforce query-before-reasoning for all project-specific technical questions
- Define clear rules for what requires RAG query vs. what does not
- Provide chunk_type-aware retrieval guidance (match question type to chunk type)
- Handle not-found and unreachable Qdrant cases with explicit user notification

### Implementation
**File modified:** `~/.claude/CLAUDE.md`

Added `## RAG-First Protocol (MANDATORY — ALL PROJECTS)` section at the top
(after main header, before MANDATORY Session Start section) containing:
- Rule: Query Before Reasoning (4 numbered rules covering found/not-found/unreachable)
- What Requires RAG Query (7 trigger categories)
- What Does NOT Require RAG Query (4 exclusion categories)
- Chunk Type Awareness table (maps question type to prioritized chunk_type)

**File created:** `~/.claude/templates/project-claude-md-template.md`

Generic template for per-project CLAUDE.md with:
- Project Identity section (project name, environment, stack — used as Qdrant filter)
- Project-specific RAG notes placeholder
- Standard Critical Rules + Session End Protocol

### Key Facts
- RAG-First Protocol applies to ALL projects on this machine (global CLAUDE.md)
- Not-found response MUST include: "WARNING NOT FOUND IN RAG - answer based on general knowledge"
- Chunk type to question type mapping: runbook/pattern for "how to", decision for "why", debug for errors, feature for "how does X work"
- Template at `~/.claude/templates/project-claude-md-template.md` — copy to each new project
- MCP `qdrant-knowledge` confirmed in global `~/.claude/settings.json` — no change needed

---

## SESSION METADATA

- **Total chunks**: 3
- **Qdrant collection**: knowledge
- **Primary project**: homelab
- **Stack involved**: bash, jq, n8n, Qdrant, Claude Code CLI, CLAUDE.md
- **Files modified**: `.claude/skills/rag-knowledge-capture-cli/SKILL.md`, `~/scripts/push-to-qdrant.sh`, `~/.claude/CLAUDE.md`, `~/.claude/templates/project-claude-md-template.md`
- **Git branch**: main
- **Unresolved items**: Add Project Identity section to PetroChina project CLAUDE.md; run validation tests (Test 1/2/3 from Phase 3 instructions)
- **Author**: Figur Ulul Azmi
- **Generated by**: Claude Code CLI — RAG Knowledge Capture Skill
