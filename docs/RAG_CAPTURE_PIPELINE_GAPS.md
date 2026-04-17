# RAG Capture Pipeline — Gap Analysis

> **How to track progress:** When a gap is fixed, edit `[ ] OPEN` to `[x] FIXED (YYYY-MM-DD)`.
> Claude will check this file before suggesting fixes — OPEN items are next priority.

---

## Actual Pipeline Flow

```
╔══════════════════════════════════════════════════════════════════╗
║  TRIGGER  (Manual / LLM-judgment)                                ║
║  Claude reads CLAUDE.md rules, detects confirmation signals      ║
║  ("works", "fixed", "berhasil", "oke", "chunk this")            ║
║  No hook, no daemon, no cron — pure prompt instruction           ║
╚═══════════════════════════════╦══════════════════════════════════╝
                                │ Claude decides to capture
                                ▼
╔══════════════════════════════════════════════════════════════════╗
║  CAPTURE  (rag add)                                              ║
║  cat <<'CONTENT' | rag add -p P -t T --topic "..."              ║
║  Entry: cmd_add() in ~/scripts/rag-capture-v2/rag_capture.py    ║
║  validate_content() → save_draft()                               ║
║  Output: ~/scripts/.rag_drafts/chunk_NNN.md                     ║
╚═══════════════════════════════╦══════════════════════════════════╝
                                │ One draft file per rag add call
                                ▼
╔══════════════════════════════════════════════════════════════════╗
║  DRAFT STORE  (global, cross-project)                            ║
║  ~/scripts/.rag_drafts/chunk_001.md  ...                        ║
║  Persists across sessions until rag merge or rag clear           ║
╚═══════════════════════════════╦══════════════════════════════════╝
                                │ Manual — Claude calls at session end
                                ▼
╔══════════════════════════════════════════════════════════════════╗
║  MERGE  (rag merge --output YYYY-MM-DD-slug.md)                  ║
║  cmd_merge() reads all chunk_*.md, concatenates bodies           ║
║  Output: {project_root}/.claude/summaries/YYYY-MM-DD-slug.md   ║
║  Auto-clears drafts when stdin is non-tty (Claude Bash tool)    ║
║  Prints push reminder as stdout text (not executed)              ║
╚═══════════════════════════════╦══════════════════════════════════╝
                                │ Manual — user runs from reminder text
                                ▼
╔══════════════════════════════════════════════════════════════════╗
║  PUSH  (push-to-qdrant.sh <file.md>)                             ║
║  Network detect: local-b1 → LAN → Tailscale → unreachable       ║
║  Splits .md by ## CHUNK markers → per-chunk JSON payload         ║
║  POST to n8n webhook: /webhook/knowledge-ingest                  ║
║  n8n handles: Ollama embeddings + Qdrant upsert into knowledge_v2║
║  Dedup/upsert logic lives inside n8n workflow, not this script   ║
╚═══════════════════════════════╦══════════════════════════════════╝
                                │ HTTP 2xx = n8n accepted (not indexed)
                                ▼
╔══════════════════════════════════════════════════════════════════╗
║  VERIFY  (none)                                                  ║
║  No step confirms Qdrant actually indexed or is searchable       ║
╚══════════════════════════════════════════════════════════════════╝

--- BLOCKED PATH (exists in code, never activated) -----------------
  rag pipe <- parses <<<RAG_META:...>>> signal from stdin
  CLAUDE.md line 97 forbids printing <<<RAG_CHUNK_*>>> markers
  => signal-based auto-pipe is dead code in practice
--------------------------------------------------------------------
```

---

## Gap Analysis by Pipeline Step

| # | Step | Ideal | Actual | Gap | Status |
|---|------|-------|--------|-----|--------|
| G1 | **Trigger** | Automatic on confirmation signal | Claude judgment per CLAUDE.md prompt rules | No hook/daemon/cron — depends entirely on Claude's attention | `[ ] OPEN` |
| G2 | **Detect** | Structured signal parsing | LLM heuristic | `rag pipe` + `<<<RAG_META:...>>>` exists but CLAUDE.md explicitly forbids emitting those markers — automated detection path is disabled | `[ ] OPEN` |
| G3 | **Draft** | Per-chunk, immediate, isolated | `rag add` heredoc via Bash | (a) Heredoc terminator collisions when body contains literal "CONTENT"; (b) cp1252 em dash corruption on Windows stdin; (c) Draft folder is global — multi-project sessions silently mix | `[ ] OPEN` |
| G4 | **Merge** | Automatic at session end | Manual — Claude must remember before `/clear` | If session cleared without merge, drafts orphaned in `~/.rag_drafts/` with no in-session reminder | `[ ] OPEN` |
| G5 | **Push** | Automatic post-merge | Manual — user copies push command from stdout text | No hook, no CI trigger. Reminder is text only, not executed. Creates backlog of unpushed `.md` files | `[ ] OPEN` |
| G6 | **Verify** | Confirm searchable in Qdrant | None | HTTP 200 from n8n != vector indexed. Ollama/Qdrant failure inside n8n is invisible to the shell | `[ ] OPEN` |

---

## Single Points of Failure (SPOF Checklist)

Ranked by likelihood. Fix these to prevent silent capture loss.

---

### SPOF-1 — Claude skips `rag add` entirely
**Status:** `[ ] OPEN`

**What happens:** Claude does not recognize confirmation signals → no `rag add` is called → nothing is saved even after a solved session.

**Fix hint:** Add a Claude Code hook on `Stop` event that runs `rag status` and warns if drafts are zero after a long session, or enable the `rag pipe` signal path (see G2).

---

### SPOF-2 — Session cleared before `rag merge`
**Status:** `[ ] OPEN`

**What happens:** `/clear` wipes conversation context. Drafts survive on disk in `~/scripts/.rag_drafts/` but user has no in-session cue they exist.

**Fix hint:** Add a `PreToolUse` hook on the `/clear` slash command (or `Stop` event) that runs `rag remind` and blocks clear if draft count > 0.

---

### SPOF-3 — `push-to-qdrant.sh` never run after merge
**Status:** `[ ] OPEN`

**What happens:** `.claude/summaries/` accumulates `.md` files that were never pushed. Knowledge never reaches Qdrant.

**Fix hint:** Run `push-to-qdrant.sh` automatically as the last step inside `cmd_merge()` when network is reachable, or add a `Stop` hook that checks for unpushed summaries.

---

### SPOF-4 — Network unreachable at push time
**Status:** `[ ] OPEN`

**What happens:** Neither LAN (`192.168.18.169`) nor Tailscale (`100.120.249.99`) reachable → `push-to-qdrant.sh` exits 1 with no queuing or retry.

**Fix hint:** Add a local queue file (e.g., `~/.rag_push_queue`) that records unpushed file paths. A separate `rag push-pending` command drains the queue when network returns.

---

### SPOF-5 — n8n workflow down
**Status:** `[ ] OPEN`

**What happens:** n8n returns non-2xx → `FAIL_COUNT > 0` → script exits with fail count but no retry, no dead-letter queue.

**Fix hint:** Add `--retry N` flag to `push-to-qdrant.sh` with exponential backoff, or integrate with SPOF-4 queue solution.

---

### SPOF-6 — Heredoc terminator collision
**Status:** `[ ] OPEN`

**What happens:** If chunk body contains the literal word `CONTENT` on its own line, the heredoc closes early. Body silently truncated. `validate_content()` may still pass if remaining words are >= 50.

**Fix hint:** Always use a unique terminator like `RAGBODY_EOF` or `RAG_CHUNK_BODY_END` in `rag add` invocations, especially when body includes code examples. Document this in CLAUDE.md auto-capture section.

---

### SPOF-7 — `rag pipe` signal path blocked by CLAUDE.md
**Status:** `[ ] OPEN`

**What happens:** `rag_capture.py` has full signal-based auto-detection via `<<<RAG_META:...>>>` and `<<<RAG_CHUNK_START/END>>>` — but CLAUDE.md line 97 explicitly forbids Claude from emitting these markers. The feature is architecturally present but operationally dead.

**Fix hint:** Either (a) remove the prohibition in CLAUDE.md and enable the pipe path for structured capture, or (b) remove the dead `cmd_pipe` / signal parser code to reduce confusion.

---

## Fix Priority Order (suggested)

```
SPOF-2 (session clear guard)  ← highest ROI, prevents most common loss scenario
SPOF-1 (trigger reliability)  ← hooks or signal path
G2     (re-enable rag pipe)   ← unblocks SPOF-1 fix
SPOF-6 (heredoc terminator)   ← quick CLAUDE.md edit
SPOF-3 (auto-push on merge)   ← automates last manual step
SPOF-4 (push queue)           ← robustness
SPOF-5 (n8n retry)            ← robustness
G6     (verify step)          ← observability
```

---

*Generated: 2026-04-17 | Source files analyzed: `CLAUDE.md`, `scripts/push-to-qdrant.sh`, `~/scripts/rag-capture-v2/rag_capture.py`*
