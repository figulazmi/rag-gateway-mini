# Project Context

Last updated: {{DATE}}
Last reviewed: {{DATE}}
Owner: {{OWNER}}

Use this file as the compact operating context for humans, Claude Code, and future automation.

---

## LLM Context Injection Order

Before answering any question about this project, read in this order:

1. `CONTEXT.md` - constraints, scope, source-of-truth order, and rejected approaches.
2. `docs/TASKS.md` - current focus and active task boundaries.
3. Relevant sub-docs only if the task requires them.

Do not suggest solutions that conflict with `CONTEXT.md` constraints or rejected approaches.

---

## Project Identity

| Field | Value |
|---|---|
| Project | {{PROJECT_NAME}} |
| Repository | {{REPO_NAME}} |
| Stack | {{STACK}} |
| Owner | {{OWNER}} |
| Primary docs | `docs/README.md`, `docs/TASKS.md`, `docs/ONBOARDING.md` |

---

## Purpose

Describe what this project does, who uses it, and why it exists.

Minimum required detail:

- Main user or system served by the project.
- Primary problem this project solves.
- The value delivered when the project works correctly.

---

## Scope

### In Scope

- Project responsibility 1.
- Project responsibility 2.
- Project responsibility 3.

### Out of Scope

- Explicit non-goal 1.
- Explicit non-goal 2.
- Work that belongs in another project or system.

---

## Constraints

| Constraint | Reason | Impact |
|---|---|---|
| Do not commit secrets | Prevent credential exposure | Use templates, placeholders, and documented secret locations only |
| Require evidence before DONE | Prevent stale task state | Update canonical trackers only after verification |
| Keep task status in one owner | Prevent conflicting docs | Use `docs/TASKS.md` as index only |
| Keep changes scoped | Reduce review and rollback risk | Each task must define included and excluded work |

---

## Rejected Approaches

| Approach | Rejected reason | Date |
|---|---|---|
| None yet | No rejected approaches recorded yet | {{DATE}} |

Record approaches that were considered and rejected so future humans and LLMs do not re-suggest them without new evidence.

---

## Source of Truth Order

When sources conflict, use this order:

1. Current repository files.
2. Project docs in this repository.
3. This `CONTEXT.md` file.
4. `docs/architecture/DECISIONS.md`.
5. RAG, memory, or external knowledge base.
6. General model knowledge.

Current repository docs override stale RAG, memory, or external knowledge. If RAG disagrees with current docs, trust the current docs and flag the RAG entry as potentially stale.

---

## Decision Rules

- Durable decisions belong in `docs/architecture/DECISIONS.md`.
- Active task discovery belongs in `docs/TASKS.md`.
- Detailed task status belongs only in the owning `## Canonical Task Tracker`.
- Completed notable changes belong in `docs/history/CHANGELOG.md`.
- Runtime settings and secret locations belong in `docs/config/CONFIGURATION.md`.
- Verification expectations belong in `docs/testing/TEST_STRATEGY.md`.

---

## Task Scope Boundary Rule

Every active task entry must make the boundary clear enough that an implementer knows what not to touch.

Each task should define:

- Included work.
- Excluded work.
- Expected evidence.
- Owning document or source of truth.

If the boundary is unclear, do not implement. Clarify or split the task first.

---

## Verification Rules

A task is not done until verification evidence exists.

Valid evidence includes:

- Passing command output.
- Endpoint, CLI, UI, or deployment smoke test.
- Linked artifact, report, or generated file.
- Manual check with exact steps and observed result.
- Docs updated: `CONTEXT.md` Rejected Approaches and `docs/TASKS.md` reflect current state.

---

## Open Questions

| Question | Owner | Needed by | Blocks | Status |
|---|---|---|---|---|
| None | None | None | None | None |

If an open question blocks a task and is unresolved by `Needed by`, mark the blocked task `[!] BLOCKED` in its owning canonical tracker.

---

*Last updated: {{DATE}} · Owner: {{OWNER}}*