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

Quick summaries, priority boards, README indexes, and `docs/TASKS.md` may reference task IDs, but must not duplicate detailed status values unless they explicitly say they are derived from the canonical table.

Legacy sections above the canonical tracker may contain historical status text. If they do, add this note near the top:

```markdown
Legacy sections may contain historical status text. Current source of truth is [Canonical Task Tracker](#canonical-task-tracker).
```

---

## Documentation Roles

| File | Role | Owns task status? |
|---|---|---:|
| `docs/README.md` | Navigation, reading order, and top-level orientation | No |
| `docs/TASKS.md` | Cross-document active task index | No |
| `docs/ONBOARDING.md` | Fast-start path, definition of ready, and definition of done | No |
| `docs/history/CHANGELOG.md` | Notable completed changes and historical context | No |
| `docs/architecture/DECISIONS.md` | Durable decisions, rationale, and consequences | No |
| `docs/config/CONFIGURATION.md` | Configuration sources, required settings, and secret locations | No |
| `docs/testing/TEST_STRATEGY.md` | Verification expectations and evidence rules | Yes, only for testing-documentation tasks |
| `docs/risks/RISK_REGISTER.md` | Risk identification, mitigation, and review dates | No |
| `docs/incidents/INCIDENT_LOG.md` | Incident records and follow-up task links | No |
| `CLAUDE.md` | Project instructions for Claude Code and future agents | No |
| `CONTRIBUTING.md` | Contribution workflow and verification checklist | No |
| `docs/automation/AUTOMATION.md` | CI/CD, hooks, cron, and scheduled automation inventory | No |
| `docs/templates/` | Blank reusable templates for other projects | No |
| Any tracker document | Planning, audit, quality, security, migration, or pipeline task ownership | Yes, only in `## Canonical Task Tracker` |

Use `ONBOARDING.md` to start quickly, `TASKS.md` to find work, `TEST_STRATEGY.md` to verify work, `CONFIGURATION.md` to locate runtime settings safely, `CHANGELOG.md` to understand what changed, and `DECISIONS.md` to understand why a choice was made.

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

| Order | ID | Task | Scope boundary | Status | Evidence | Next action |
|---:|---|---|---|---|---|---|
| 1 | P1-A | Short imperative task name | Includes the named outcome only; excludes unrelated refactors | `[ ] OPEN` | Observable proof required to mark done | Immediate next command or decision |

Column rules:

| Column | Rule |
|---|---|
| `Order` | Execution order, not priority label. Keep stable unless order truly changes. |
| `ID` | Stable task ID. Never reuse an ID for a different task. |
| `Task` | One concrete outcome, written as an imperative phrase. |
| `Scope boundary` | Explicitly states included work and excluded work. |
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
4. Every active task must have a scope boundary that states included and excluded work.
5. If a blocker becomes stale, update `Evidence` and `Next action` immediately.
5. If another doc references the task, reference its ID and canonical doc instead of copying the status.
6. Before reporting a tracked task as complete, run a text search for its ID and update stale references.

---

## Definition of Done

A task may be marked `[x] DONE (YYYY-MM-DD)` only when all required conditions are true:

| Condition | Requirement |
|---|---|
| Complete | The implementation, documentation, or operational change is finished |
| Verified | Evidence exists in the owning canonical tracker row |
| Linked | Related docs reference the owning tracker instead of duplicating status |
| Safe | Secrets, destructive commands, and risky operations were handled according to project rules |
| Current | Stale references to the task ID were searched and updated |

If any condition is missing, use `[~] IN PROGRESS`, `[!] BLOCKED`, or `[ ] DEFERRED` instead of DONE.

---

## Documentation Hygiene Checklist

Before ending a documentation-changing task, check:

1. `docs/README.md` links any new folder or important document.
2. `docs/TASKS.md` links any new active tracker.
3. The owning tracker has exactly one `## Canonical Task Tracker` section.
4. `docs/history/CHANGELOG.md` records notable completed changes.
5. `docs/architecture/DECISIONS.md` records durable decisions, not todos.
6. `docs/reference/PROJECT_DOCS_TEMPLATE.md` and `docs/templates/` stay generic enough to reuse.

---

## Archive Rule

Move old material to history or archive form when it no longer drives current work:

| Content | Archive destination |
|---|---|
| Completed notable change | `docs/history/CHANGELOG.md` |
| Superseded decision | Mark ADR as `Superseded` and link replacement |
| Obsolete task | Mark `[x] OBSOLETE (YYYY-MM-DD)` in owning tracker |
| Incident follow-up completed | Keep incident record, link completed task evidence |

Do not delete historical context if it explains why a current decision exists.

---

## Cross-Doc Reference Pattern

Use this format when one tracker depends on another:

```markdown
Status source: [`RAG_SECURITY_POSTURE.md`](../security/RAG_SECURITY_POSTURE.md), task `P0-3`.
```

This makes it clear which file owns the status.
