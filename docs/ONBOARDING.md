# Onboarding

Use this document to understand the project quickly before editing code, docs, infrastructure, or automation.

---

## 15-Minute Path

| Step | Read | Goal |
|---:|---|---|
| 1 | [`README.md`](README.md) | Understand the docs map and reading order |
| 2 | [`TASKS.md`](TASKS.md) | Find the active work and owning trackers |
| 3 | [`planning/RAG_V2_ROADMAP.md`](planning/RAG_V2_ROADMAP.md) | Understand current roadmap priorities |
| 4 | [`reference/RAG_MANUAL_BOOK.md`](reference/RAG_MANUAL_BOOK.md) | Learn operational commands and project workflows |
| 5 | [`architecture/DECISIONS.md`](architecture/DECISIONS.md) | Understand durable decisions and tradeoffs |

---

## Before Changing Anything

- Check [`TASKS.md`](TASKS.md) for active task ownership.
- Check the owning document's `## Canonical Task Tracker` before changing status.
- Check [`history/CHANGELOG.md`](history/CHANGELOG.md) for recent notable changes.
- Check [`architecture/DECISIONS.md`](architecture/DECISIONS.md) before reversing a documented decision.
- Keep evidence with the task that owns the status.

---

## Project-Specific Starting Points

| Need | Start here |
|---|---|
| Current todo | [`TASKS.md`](TASKS.md) |
| RAG roadmap | [`planning/RAG_V2_ROADMAP.md`](planning/RAG_V2_ROADMAP.md) |
| Retrieval quality | [`quality/RAG_EVAL_HARNESS.md`](quality/RAG_EVAL_HARNESS.md) |
| Security posture | [`security/RAG_SECURITY_POSTURE.md`](security/RAG_SECURITY_POSTURE.md) |
| Deployment or recovery | [`reference/RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md`](reference/RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md) |
| Reusable docs template | [`reference/PROJECT_DOCS_TEMPLATE.md`](reference/PROJECT_DOCS_TEMPLATE.md) |

---

## Definition of Ready

A task is ready to start when:

- The owning tracker row has a clear `Next action`.
- The expected evidence is understandable.
- Dependencies are not blocked, or the blocker is explicitly named.
- The scope is small enough to verify in one working session.

---

## Definition of Done

A task is done only when:

- The implementation or document change is complete.
- Verification evidence exists.
- The owning canonical tracker row is updated.
- Cross-document references to the task ID are not stale.
- `CHANGELOG.md` is updated if the change is notable after the current task.

---

*Last updated: 2026-05-02 · Owner: Figur Ulul Azmi*