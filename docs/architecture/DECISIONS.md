# Architecture Decisions

Use this file for durable decisions that explain why the project works the way it does.

Task status belongs in canonical trackers. Change history belongs in [`../history/CHANGELOG.md`](../history/CHANGELOG.md).

---

## Decision Format

```markdown
## ADR-000 - Short decision title

| Field | Value |
|---|---|
| Date | YYYY-MM-DD |
| Status | Proposed / Accepted / Superseded / Deprecated |
| Context | The constraint, problem, or tradeoff that forced the decision |
| Decision | The chosen approach |
| Consequences | What becomes easier, harder, or intentionally excluded |
| Related docs | Links to trackers, runbooks, or implementation docs |
```

---

## ADR-001 - Keep task status in canonical trackers only

| Field | Value |
|---|---|
| Date | 2026-05-02 |
| Status | Accepted |
| Context | Documentation can become stale when README files, planning docs, and tracker sections repeat the same task status. |
| Decision | Each tracker owns exactly one `## Canonical Task Tracker`; index files may link to task IDs but must not duplicate detailed status or evidence. |
| Consequences | Readers have one source of truth for each task, while `docs/README.md` and `docs/TASKS.md` stay lightweight navigation layers. |
| Related docs | [`../reference/TRACKING_STATUS_STANDARD.md`](../reference/TRACKING_STATUS_STANDARD.md), [`../TASKS.md`](../TASKS.md) |

---

*Last updated: 2026-05-02 · Owner: Figur Ulul Azmi*