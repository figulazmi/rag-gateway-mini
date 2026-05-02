# Change History

Use this file for notable documentation, architecture, infrastructure, workflow, and release history.

This is not a todo list. Active work belongs in the owning `## Canonical Task Tracker`; cross-document navigation belongs in [`../TASKS.md`](../TASKS.md).

---

## Entry Format

```markdown
## YYYY-MM-DD - Short change title

| Field | Value |
|---|---|
| Type | docs / code / infra / security / quality / decision |
| Summary | One-sentence description of what changed |
| Evidence | Command output, PR, commit, deployed check, or doc link |
| Related tasks | TASK-ID or `None` |
| Follow-up | Link to tracker task ID or `None` |
```

---

## 2026-05-02 - Finalized reusable docs tracking structure

| Field | Value |
|---|---|
| Type | docs |
| Summary | Added a reusable docs structure with task index, decision log, changelog, and project template guidance. |
| Evidence | [`../README.md`](../README.md), [`../TASKS.md`](../TASKS.md), [`../reference/PROJECT_DOCS_TEMPLATE.md`](../reference/PROJECT_DOCS_TEMPLATE.md) |
| Related tasks | None |
| Follow-up | None |

---

## Maintenance Rules

- Add entries only for changes worth remembering after the current task is done.
- Keep task status out of this file.
- Link to canonical trackers for follow-up work.
- Prefer one concise entry per meaningful change instead of daily activity logs.

---

*Last updated: 2026-05-02 · Owner: Figur Ulul Azmi*