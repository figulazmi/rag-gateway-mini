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
| G1 | **Trigger** | Automatic on confirmation signal | Claude judgment per CLAUDE.md prompt rules | No hook/daemon/cron — depends entirely on Claude's attention | `[x] FIXED (2026-04-18)` — Checkpoint Trigger Rules added to CLAUDE.md (85%/75% token thresholds) |
| G2 | **Detect** | Structured signal parsing | LLM heuristic | `rag pipe` + `<<<RAG_META:...>>>` exists but CLAUDE.md explicitly forbids emitting those markers — automated detection path is disabled | `[x] FIXED (2026-04-18)` — `rag checkpoint` replaces need for signal detection; explicit command with structured flags |
| G3 | **Draft** | Per-chunk, immediate, isolated | `rag add` heredoc via Bash | (a) ~~Heredoc terminator collisions~~ **FIXED 2026-04-19** — `RAGBODY_EOF` terminator in CLAUDE.md; (b) ~~cp1252 em dash corruption~~ **FIXED 2026-04-25** — `encoding="utf-8"` enforced on all stdin reads; (c) ~~Draft folder global mix~~ **FIXED 2026-04-25** — `get_project_draft_dir(project)` isolates per-project subdirs | `[x] FIXED (2026-04-25)` |
| G4 | **Merge** | Automatic at session end | Manual — Claude must remember before `/clear` | If session cleared without merge, drafts orphaned in `~/.rag_drafts/` with no in-session reminder | `[x] FIXED (2026-04-18)` — Checkpoints bypass draft/merge cycle entirely; saved directly to `.claude/checkpoints/` |
| G5 | **Push** | Automatic post-merge | Manual — user copies push command from stdout text | No hook, no CI trigger. Reminder is text only, not executed. Creates backlog of unpushed `.md` files | `[x] FIXED (2026-04-19)` — `auto_push()` in `cmd_merge()` runs push-to-qdrant.sh immediately; on fail queues to `~/.rag_push_queue` |
| G6 | **Verify** | Confirm searchable in Qdrant | None | HTTP 200 from n8n != vector indexed. Ollama/Qdrant failure inside n8n is invisible to the shell | `[x] FIXED (2026-04-19)` — `get_point_count()` in push-to-qdrant.sh checks delta before/after; logs `+N indexed` or `⚠️ delta=0` to stderr |

---

## Single Points of Failure (SPOF Checklist)

Ranked by likelihood. Fix these to prevent silent capture loss.

---

### SPOF-1 — Claude skips `rag add` entirely
**Status:** `[x] FIXED (2026-04-18)`

**What happened:** Claude did not recognize confirmation signals → no capture even after solved session.

**Fix applied:** `rag checkpoint` command added with explicit 85%/75% token triggers in CLAUDE.md. Checkpoint captures *momentum* (in-progress state) regardless of whether problem is solved. `rag resume` at session start surfaces any missed captures.

---

### SPOF-2 — Session cleared before `rag merge`
**Status:** `[x] FIXED (2026-04-18)`

**What happened:** `/clear` wiped context; drafts orphaned in `~/.rag_drafts/`.

**Fix applied:** Checkpoints bypass the draft/merge cycle entirely — `rag checkpoint` writes directly to `.claude/checkpoints/` and should be pushed immediately. No merge step needed before `/clear`. `rag resume` at next session start recovers any un-pushed checkpoints from disk.

---

### SPOF-3 — `push-to-qdrant.sh` never run after merge
**Status:** `[x] FIXED (2026-04-19)`

**What happened:** `.claude/summaries/` accumulated `.md` files that were never pushed.

**Fix applied:** `auto_push()` added to `cmd_merge()` in `rag_capture.py`. After writing the merged file, immediately runs `bash ~/scripts/push-to-qdrant.sh <file>`. On network failure (non-zero exit), appends file path to `~/.rag_push_queue` instead of silently exiting.

---

### SPOF-4 — Network unreachable at push time
**Status:** `[x] FIXED (2026-04-19)`

**What happened:** LAN + Tailscale both unreachable → push failed silently with no retry.

**Fix applied:** `auto_push()` writes to `~/.rag_push_queue` on failure. New `rag push-pending` command reads the queue and retries each file with exponential backoff (2s, 4s, 8s). Removes entry on success; re-writes remaining failures back to queue file.

---

### SPOF-5 — n8n workflow down
**Status:** `[x] FIXED (2026-04-19)` — via queue integration

**What happened:** n8n non-2xx → script exits, no retry, no dead-letter.

**Fix applied:** When `auto_push()` catches a non-zero exit (regardless of cause — network or n8n down), the file is queued to `~/.rag_push_queue`. `rag push-pending` drains the queue with retries when n8n is back up. Direct per-chunk retry (inside `push-to-qdrant.sh`) remains a future improvement.

---

### SPOF-6 — Heredoc terminator collision
**Status:** `[x] FIXED (2026-04-19)`

**What happened:** Chunk body containing literal `CONTENT` on its own line caused early heredoc termination, silently truncating the body.

**Fix applied:** Changed terminator in `CLAUDE.md` auto-capture section from `CONTENT` to `RAGBODY_EOF` — unique enough to never appear in chunk content. Lines 76 and 89 of `CLAUDE.md`.

---

### SPOF-7 — `rag pipe` signal path blocked by CLAUDE.md
**Status:** `[x] FIXED (2026-04-25)`

**What happened:** `rag_capture.py` had full signal-based auto-detection via `<<<RAG_META:...>>>` and `<<<RAG_CHUNK_START/END>>>` — but CLAUDE.md line 97 explicitly forbids Claude from emitting these markers. The feature was architecturally present but operationally dead.

**Fix applied:** Dead code path (`cmd_pipe` + signal parser) removed from `rag_capture.py`. The `rag checkpoint` / `rag add` explicit-command flow is the canonical path; signal-based pipe added confusion without benefit.

---

## Fix Priority Order

```
[x] SPOF-2 (session clear guard)  ← FIXED 2026-04-18 via checkpoint bypass
[x] SPOF-1 (trigger reliability)  ← FIXED 2026-04-18 via 85%/75% token triggers
[x] G2     (re-enable rag pipe)   ← FIXED 2026-04-18 via rag checkpoint command
[x] G1     (trigger automation)   ← FIXED 2026-04-18 via CLAUDE.md trigger rules
[x] G4     (merge dependency)     ← FIXED 2026-04-18 via direct checkpoint save

[x] SPOF-6 (heredoc terminator)   ← FIXED 2026-04-19: RAGBODY_EOF in CLAUDE.md
[x] SPOF-3 (auto-push on merge)   ← FIXED 2026-04-19: auto_push() in cmd_merge()
[x] SPOF-4 (push queue)           ← FIXED 2026-04-19: ~/.rag_push_queue + rag push-pending
[x] SPOF-5 (n8n retry)            ← FIXED 2026-04-19: via queue integration
[x] G5     (push automation)      ← FIXED 2026-04-19: auto_push() in cmd_merge()
[x] G6     (verify step)          ← FIXED 2026-04-19: get_point_count() delta in push-to-qdrant.sh

[x] SPOF-7 (rag pipe dead code)   ← FIXED 2026-04-25: dead cmd_pipe removed
[x] G3(b)  (cp1252 em dash)       ← FIXED 2026-04-25: utf-8 enforced on stdin
[x] G3(c)  (draft folder mix)     ← FIXED 2026-04-25: get_project_draft_dir() per-project
```

---

*Generated: 2026-04-17 | Source files analyzed: `CLAUDE.md`, `scripts/push-to-qdrant.sh`, `~/scripts/rag-capture-v2/rag_capture.py`*
