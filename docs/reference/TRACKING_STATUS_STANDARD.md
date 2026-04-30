# Tracking Status Standard

Use this standard for every planning, audit, quality, security, and pipeline tracker under `docs/`.

The goal is to prevent stale documentation where a task was already executed but another checklist still shows it as open.

---

## Canonical Rule

Each tracker must have exactly one canonical status table for its own tasks.

The canonical table heading must be:

```markdown
## Canonical Task Tracker
```

Place `## Canonical Task Tracker` as the final operational section before footer metadata, appendix-only notes, or generated provenance. This makes the unfinished work easy to find after reading the document.

Quick summaries, priority boards, and README indexes may reference task IDs, but must not duplicate detailed status values unless they explicitly say they are derived from the canonical table.

Legacy sections above the canonical tracker may contain historical status text. If they do, add this note near the top:

```markdown
Legacy sections may contain historical status text. Current source of truth is [Canonical Task Tracker](#canonical-task-tracker).
```

---

## Table Types

Not every table is a task tracker.

| Table type | May appear near analysis? | Source of task status? | Rule |
|---|---:|---:|---|
| Metric or score table | Yes | No | Show measurements only; use task IDs in notes when needed |
| Snapshot or distribution table | Yes | No | Show current/baseline state only |
| Priority board or index | Yes | No | Link to canonical status source |
| Canonical Task Tracker | Final operational section | Yes | Owns Status, Evidence, and Next action |

Metric rows may say that a metric was achieved, but task completion status still belongs in `## Canonical Task Tracker`.

---

## Canonical Table Columns

Use this table shape for new trackers and when refactoring old trackers:

| Order | ID | Task | Status | Evidence | Next action |
|---:|---|---|---|---|---|
| 1 | P1-A | Short imperative task name | `[ ] OPEN` | Observable proof required to mark done | Immediate next command or decision |

Column rules:

| Column | Rule |
|---|---|
| `Order` | Execution order, not priority label. Keep stable unless order truly changes. |
| `ID` | Stable task ID. Never reuse an ID for a different task. |
| `Task` | One concrete outcome, written as an imperative phrase. |
| `Status` | One of the allowed status values below. |
| `Evidence` | Required for DONE. Use command output, deployed service check, test result, or doc link. |
| `Next action` | Required for OPEN, IN PROGRESS, BLOCKED, or DEFERRED. Use `None` only when DONE or OBSOLETE. |

---

## Allowed Status Values

| Status | Meaning | Required evidence or note |
|---|---|---|
| `[ ] OPEN` | Not started | Next action must be clear |
| `[~] IN PROGRESS` | Started but not verified | Evidence must show current partial state |
| `[x] DONE (YYYY-MM-DD)` | Implemented and verified | Evidence is mandatory |
| `[!] BLOCKED` | Cannot proceed until dependency changes | Name dependency and owner/system |
| `[ ] DEFERRED` | Valid task intentionally postponed | State exact revisit condition |
| `[x] OBSOLETE (YYYY-MM-DD)` | No longer needed | State replacement or why it was dropped |

Avoid custom synonyms like `FIXED`, `TODO`, `MET`, or raw `BLOCKED` in task trackers. If a legacy doc uses them, add a mapping note or migrate them during the next edit.

---

## Quick Summary Format

Quick summaries should list IDs only:

```text
Done: P1-A, P1-B, P1-C
Open: P4-C
Blocked: P5
Next: P4-C — re-push summaries and rerun eval
```

Do not repeat detailed evidence or independent status labels in the quick summary.

---

## Update Discipline

1. When code, scripts, infra, or docs complete a tracked task, update the canonical row in the same working set.
2. A task is not DONE until verification passes.
3. If implementation is done but verification is pending, use `[~] IN PROGRESS`.
4. If a blocker becomes stale, update `Evidence` and `Next action` immediately.
5. If another doc references the task, reference its ID and canonical doc instead of copying the status.
6. Before reporting a tracked task as complete, run a text search for its ID and update stale references.

---

## Cross-Doc Reference Pattern

Use this format when one tracker depends on another:

```markdown
Status source: [`RAG_SECURITY_POSTURE.md`](../security/RAG_SECURITY_POSTURE.md), task `P0-3`.
```

This makes it clear which file owns the status.
