# Project Context

Last updated: {{DATE}}
Last reviewed: {{DATE}}
Owner: {{OWNER}}

Use this file as the compact operating context for humans, Claude Code, and future automation.

---

## Project Identity

Last updated: {{DATE}}

| Field | Value |
|---|---|
| Project | {{PROJECT_NAME}} |
| Repository | {{REPO_NAME}} |
| Stack | {{STACK}} |
| Owner | {{OWNER}} |
| Primary docs | `docs/README.md`, `docs/TASKS.md`, `docs/ONBOARDING.md` |

---

## Purpose

Last updated: {{DATE}}

Describe what this project does, who uses it, and why it exists.

Minimum required detail:

- Main user or system served by the project.
- Primary problem this project solves.
- The value delivered when the project works correctly.

---

## Scope

Last updated: {{DATE}}

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

Last updated: {{DATE}}

| Constraint | Reason | Impact |
|---|---|---|
| Do not commit secrets | Prevent credential exposure | Use templates, placeholders, and documented secret locations only |
| Require evidence before DONE | Prevent stale task state | Update canonical trackers only after verification |
| Keep task status in one owner | Prevent conflicting docs | Use `docs/TASKS.md` as index only |
| Keep changes scoped | Reduce review and rollback risk | Each task must define included and excluded work |

---

## Source of Truth Order

Last updated: {{DATE}}

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

Last updated: {{DATE}}

- Durable decisions belong in `docs/architecture/DECISIONS.md`.
- Active task discovery belongs in `docs/TASKS.md`.
- Detailed task status belongs only in the owning `## Canonical Task Tracker`.
- Completed notable changes belong in `docs/history/CHANGELOG.md`.
- Runtime settings and secret locations belong in `docs/config/CONFIGURATION.md`.
- Verification expectations belong in `docs/testing/TEST_STRATEGY.md`.

---

## Task Scope Boundary Rule

Last updated: {{DATE}}

Every active task entry must make the boundary clear enough that an implementer knows what not to touch.

Each task should define:

- Included work.
- Excluded work.
- Expected evidence.
- Owning document or source of truth.

If the boundary is unclear, do not implement. Clarify or split the task first.

---

## Verification Rules

Last updated: {{DATE}}

A task is not done until verification evidence exists.

Valid evidence includes:

- Passing command output.
- Endpoint, CLI, UI, or deployment smoke test.
- Linked artifact, report, or generated file.
- Manual check with exact steps and observed result.

---

## Open Questions

Last updated: {{DATE}}

| Question | Owner | Needed by | Status |
|---|---|---|---|
| None | None | None | None |

---

*Last updated: {{DATE}} · Owner: {{OWNER}}*