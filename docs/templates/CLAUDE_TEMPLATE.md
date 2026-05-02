# CLAUDE.md

Project instructions for Claude Code and future coding agents.

---

## Project Identity

| Field | Value |
|---|---|
| Project | {{PROJECT_NAME}} |
| Repository | {{REPO_NAME}} |
| Stack | {{STACK}} |
| Owner | {{OWNER}} |

---

## Critical Rules

- Use English for code, comments, logs, and documentation.
- Do not commit secrets, credentials, tokens, private keys, or real production config.
- Prefer focused edits over broad refactors.
- Update documentation when behavior, configuration, deployment, or task status changes.
- A task is not done until verification evidence exists.

---

## Source of Truth

When sources conflict, use this order:

1. Current repository files.
2. Project docs in this repository.
3. `CONTEXT.md`.
4. `docs/architecture/DECISIONS.md`.
5. RAG, memory, or external knowledge base.
6. General model knowledge.

Current repository docs override stale RAG, memory, or external knowledge. If RAG disagrees with current docs, trust the current docs and flag the RAG entry as potentially stale.

---

## Documentation Workflow

Before changing existing behavior:

1. Read `CONTEXT.md` for constraints, scope, source-of-truth order, and rejected approaches.
2. Read `docs/ONBOARDING.md` for the project workflow.
3. Check `docs/TASKS.md` for active work and task boundaries.
4. Check the owning document's `## Canonical Task Tracker`.
5. Check `docs/architecture/DECISIONS.md` before reversing a documented decision.
6. Check `docs/config/CONFIGURATION.md` before changing runtime settings or secrets handling.
7. Check `docs/testing/TEST_STRATEGY.md` before claiming verification.

---

## RAG / Knowledge Capture

If this project uses a project knowledge base, query it before answering project-specific architecture, deployment, debugging, or pattern questions.

If no project knowledge base exists yet, state that the answer is based on current repository files and general knowledge.

---

## Build and Test

```bash
{{INSTALL_COMMAND}}
{{RUN_COMMAND}}
{{TEST_COMMAND}}
```

---

## Session End Checklist

- Update the owning canonical tracker.
- Update `docs/history/CHANGELOG.md` for notable completed changes.
- Update `docs/architecture/DECISIONS.md` for durable decisions.
- Do not leave generated secrets, local logs, or cache files staged.

---

*Last updated: {{DATE}} · Owner: {{OWNER}}*