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

## 2026-05-03 - Hardened keyfacts negative-query gate

| Field | Value |
|---|---|
| Type | code / quality |
| Summary | Added a separate not-found confidence threshold so low-score generic RAG matches do not return `status=found`. |
| Evidence | [`../planning/RAG_V2_ROADMAP.md`](../planning/RAG_V2_ROADMAP.md), [`../quality/RAG_EVAL_HARNESS.md`](../quality/RAG_EVAL_HARNESS.md), `rtk dotnet build`, `rtk dotnet test`, 2026-05-03 read-only soak |
| Related tasks | P2.8 |
| Follow-up | Deploy/restart gateway, then run positive and negative smoke |

---

## 2026-05-02 - Validated keyfacts retrieval-only production

| Field | Value |
|---|---|
| Type | quality / decision |
| Summary | Recorded rollback-safe retrieval-only production validation for `knowledge_v2_keyfacts` while leaving legacy ingest on `knowledge_v2`. |
| Evidence | [`../planning/RAG_V2_ROADMAP.md`](../planning/RAG_V2_ROADMAP.md), [`../quality/RAG_EVAL_HARNESS.md`](../quality/RAG_EVAL_HARNESS.md) |
| Related tasks | P2.6, P2.7 |
| Follow-up | Full ingest cutover remains future work |

---

## 2026-05-02 - Documented keyfacts production candidate path

| Field | Value |
|---|---|
| Type | quality / docs |
| Summary | Recorded `knowledge_v2_keyfacts` production criteria, initial soak findings, and safe cutover boundaries while preserving the legacy push path. |
| Evidence | [`../planning/RAG_V2_ROADMAP.md`](../planning/RAG_V2_ROADMAP.md), [`../quality/RAG_EVAL_HARNESS.md`](../quality/RAG_EVAL_HARNESS.md) |
| Related tasks | P2.5, P2.6, P2.7 |
| Follow-up | P2.6, P2.7 |

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