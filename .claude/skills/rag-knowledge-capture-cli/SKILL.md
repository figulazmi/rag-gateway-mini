---
name: rag-knowledge-capture-cli
description: >
  Generate RAG-optimized knowledge chunks from a Claude Code CLI session (VS Code).
  Integrated with CLAUDE.md Session End Protocol — auto-triggered before /clear.
  Uses rag CLI (rag_capture.py) for draft management and merging — NOT Write tool.
  Qdrant collection: "knowledge_v2". Chunk strategy: split per problem-solution pair.
  Output language: English only (optimized for embedding quality).
  Claude calls `rag add` per chunk, then `rag merge` — rag CLI saves to .claude/summaries/.
  NEVER push to any API. NEVER use Write tool to create .md files.
---

# ⛔ EXECUTION MODE — READ THIS FIRST

When this skill is invoked, Claude MUST execute the flow via Bash tool calls.
Claude MUST NOT print chunk content to the chat as visible markdown for the user to copy/paste.

**Correct flow (automated, zero manual paste):**
1. Claude identifies N distinct problems in the session
2. For EACH problem → Claude calls `Bash` with `cat <<'CONTENT' | rag add ... CONTENT` (content inside heredoc)
3. After all `rag add` calls → Claude calls `Bash` with `rag merge --output YYYY-MM-DD-[slug].md`
4. `rag_capture.py` writes the final .md file to `.claude/summaries/` — user does nothing manually

**WRONG (never do this):**
- ❌ Printing chunk bodies as chat markdown for the user to copy
- ❌ Saying "Run this: rag add ... [paste content]" — Claude is the one who runs it
- ❌ Using Write tool to create the .md file — `rag merge` does it

Fallback if `rag` is missing (`command not found`):
`python "C:/Users/Clandesitine/source/repos/rag-gateway-mini/scripts/rag-capture-v2/rag_capture.py" add ...`
Do NOT fall back to the Write tool.

---

# RAG KNOWLEDGE CAPTURE SKILL

## For: Claude Code CLI (VS Code)
## Integrated with: CLAUDE.md Session End Protocol
## Target: Qdrant collection "knowledge_v2" (VM B1) via ~/scripts/push-to-qdrant.sh
## Language: English only — all output must be in English for embedding quality

---

## PURPOSE

Convert a Claude Code CLI session into RAG-optimized, independently embeddable
knowledge chunks. Each chunk is semantically rich and self-contained — Qdrant
embeds each chunk independently. Poor context = poor retrieval.

---

## WHEN TO TRIGGER

- `/clear` → run BEFORE clearing
- "session end", "end session", "simpan ke qdrant", "rag summary", "knowledge capture"
- "rag capture", "save session", "ringkasan qdrant"

---

## AUTO-SAVE BEHAVIOR (CLI-specific)

After generating all chunk content **internally** (do not print to chat), Claude Code CLI MUST
invoke the `rag` CLI via the Bash tool — NOT the Write tool, NOT via user copy/paste.

### Step 1 — For EACH chunk, call via Bash:

```bash
cat << 'CONTENT' | rag add -p PROJECT -t TYPE --topic "TOPIC" --tags "tag1,tag2,tag3"
### Context
[chunk body starts directly at ### Context — no frontmatter, no "## CHUNK N:" header.
 rag_capture.py auto-generates the "## CHUNK N: <topic>" header from --topic.]
...
CONTENT
```

> ⚠️ **Do NOT include `## CHUNK N: ...` inside the heredoc.** `save_draft` in
> `rag_capture.py` prepends it automatically from `--topic`. Including it yourself
> produces a duplicated header in the merged file.

- `-p` = project: `petrochina-eproc` | `homelab` | `mit-internal` | `homeplate`
- `-t` = type: `debug` | `feature` | `runbook` | `pattern` | `decision` | `reference`
- `--topic` = plain ASCII, no em dash, max 60 chars
- `--tags` = comma-separated, max 8, lowercase-hyphenated
- Optional: `--branch main`, `--environment homelab`, `--status implemented`, `--chunk-source code|design|ops`

> `rag add` saves each chunk as a draft in `~/scripts/.rag_drafts/`. Frontmatter (id, date, source, project, chunk_type, tags, environment, etc.) is generated automatically.

### Step 2 — After ALL chunks, merge and save:

```bash
rag merge --output YYYY-MM-DD-[slug-topic].md
```

- slug-topic: lowercase, hyphenated, max 5 words
- `rag merge` consolidates drafts into `.claude/summaries/YYYY-MM-DD-[topic].md`
- Tool prints push reminder automatically — do not duplicate manually

### What the rag CLI handles automatically
- Frontmatter generation (id, date, source, chunk_type, tags, environment, etc.)
- Draft storage in `~/scripts/.rag_drafts/`
- SESSION METADATA block at end of merged file
- Push command reminder after merge

### What the user does after (printed by `rag merge`):
```bash
bash ~/scripts/push-to-qdrant.sh .claude/summaries/YYYY-MM-DD-[topic].md
```

---

## OUTPUT MODE

DEFAULT: CHUNKED
- One `.md` file per session
- Multiple `## CHUNK` blocks per file (each 150–400 words)
- One chunk per distinct problem-solution pair (PRIMARY RULE)
- Different `chunk_type` values → SEPARATE files (one chunk_type per file)

---

## CHUNK TYPE SELECTION GUIDE

| Trigger | chunk_type |
|---------|------------|
| Error/bug → fix | `debug` |
| Build/implement feature | `feature` |
| "How do I..." procedure | `runbook` |
| Reusable approach across projects | `pattern` |
| "Why A instead of B?" | `decision` |
| Factual reference / config | `reference` |

---

## CHUNK BODY TEMPLATES (paste into heredoc for `rag add`)

> **LANGUAGE LOCK** — ALL content in English. Indonesian is PROHIBITED.

### debug
```markdown
## CHUNK N: [Title]

### Context
[1–3 sentences. System, goal, constraint. Self-contained.]

### Problem
[Specific issue, error message, symptoms.]

### Solution
[Actual fix, decision, reasoning.]

### Key Facts
- Fact 1
- Fact 2
- Fact 3

### Code / Commands
[Only if essential.]

### Caveats
[Only if important gotchas exist.]
```

### feature
```markdown
## CHUNK N: [Feature Name — Phase/Aspect]

### Context
### Requirements
### Architecture Decision
### Implementation
### Key Facts (min 3)
### Code / Commands
### Lessons Learned
```

### runbook
```markdown
## CHUNK N: [Procedure Name]

### Context
### Prerequisites
### Steps (numbered)
### Verification
### Key Facts (min 3)
### Troubleshooting
```

### pattern
```markdown
## CHUNK N: [Pattern Name]

### Context
### When to Use
### When NOT to Use
### Implementation
### Key Facts (min 3)
### Code / Commands
### Variations
```

### decision
```markdown
## CHUNK N: [Decision Title]

### Context
### Decision Required
### Options Considered
### Decision
### Rationale
### Consequences
### Key Facts (min 3)
```

### reference
```markdown
## CHUNK N: [Reference Title]

### Context
### Content
### Key Facts (min 3)
### Related Commands
```

---

## CHUNK SPLITTING RULES

PRIMARY RULE: **one distinct problem/topic = one chunk**

All chunks within a single file MUST share the same `chunk_type`. Session produces
different types → generate SEPARATE files (separate `rag add` batches + separate
`rag merge --output ...` calls).

Split new chunk when:
- New separate problem/topic (even same session)
- Different system or layer
- Independent decision or pattern

Merge into one chunk when:
- Same problem, iterative debugging toward same resolution
- Follow-up discovery caused by same root problem
- Context inseparable

---

## HARD RULES

- NEVER print chunk bodies as chat markdown — pipe them to `rag add` via Bash heredoc
- NEVER use the Write tool to create `.md` files — `rag merge` does it
- NEVER write frontmatter manually — `rag_capture.py` generates it from CLI flags
- NEVER output empty chunks
- NEVER use "as mentioned above" — every chunk is self-contained
- NEVER call any external API or push to Notion
- NEVER skip the auto-save step — call `rag add` via Bash per chunk, then `rag merge`
- NEVER write output in Indonesian — English only, all sections
- NEVER use em dash (—) or special Unicode in `--topic` or `--tags` flags — use plain `-`
- NEVER mix `chunk_type` values in a single file — one file = one chunk_type
- ALWAYS call `rag add` (Bash) for each chunk before calling `rag merge`
- ALWAYS write Key Facts as standalone searchable English sentences
- ALWAYS split at problem-solution boundary — one problem = one chunk
- ALWAYS call `rag merge --output YYYY-MM-DD-[slug].md` after all chunks added
- `rag merge` prints the push reminder automatically — do not duplicate it

---

## CONFLICT WITH /clear

If user types `/clear` without running Session End Protocol first:
→ STOP the clear action
→ Say: "⚠️ Session End Protocol belum dijalankan. Jalankan RAG capture dulu?"
→ Wait for user confirmation

---

## EXAMPLE: two debug chunks, one file

```bash
# Step 1 — chunk 1 (Claude calls this via Bash tool)
cat << 'CONTENT' | rag add -p petrochina-eproc -t debug \
  --topic "Hangfire JDE Sync Silent Null Deserialization" \
  --tags "hangfire,jde-sync,ef-core,system-text-json,petrochina,eproc,debug,fixed" \
  --branch "feature/jde-sync-fix" --environment dev
### Context
PetroChina Eproc uses Hangfire cron (03:00 WIB) to sync JDE data via SyncJdeDataHandler.

### Problem
Job shows "Succeeded" but target tables not updated. No exceptions. Intermittent 2–3x/week.

### Solution
Missing [JsonPropertyName] on JDE DTOs caused System.Text.Json to silently deserialize null.
Added explicit [JsonPropertyName] matching API field names.

### Key Facts
- System.Text.Json silently skips unknown properties — no exception
- Missing [JsonPropertyName] causes silent null deserialization
- BulkSyncAsync TRUNCATE+Insert overwrites valid data with nulls
- Hangfire reports "Succeeded" regardless of data correctness
CONTENT

# Step 2 — chunk 2
cat << 'CONTENT' | rag add -p petrochina-eproc -t debug \
  --topic "CQRS Domain Isolation Violation Sync Handler" \
  --tags "cqrs,clean-architecture,domain-isolation,petrochina,eproc,debug,fixed" \
  --branch "feature/jde-sync-fix"
### Context
Clean Architecture splits D1 (read) from D2 (write). Sync handler lives in D2.

### Problem
D2 handler called D1 DepartmentReadRepository to pre-check existence — violates CQRS.

### Solution
Removed cross-domain call. BulkSyncAsync TRUNCATE+Insert is idempotent — no pre-check needed.

### Key Facts
- CQRS write handlers must never call read repositories from other domain
- BulkSyncAsync is idempotent — no existence pre-check needed
- BulkExtensions BulkMerge is the correct upsert without crossing domains
CONTENT

# Step 3 — merge
rag merge --output 2026-04-06-hangfire-jde-sync-debug.md
```

The final `.md` lands at `.claude/summaries/2026-04-06-hangfire-jde-sync-debug.md` with
auto-generated frontmatter and SESSION METADATA. Zero manual paste.
