# Test Strategy

Use this document to define what must be verified before marking work done.

Task-specific evidence belongs in the owning `## Canonical Task Tracker`.

---

## Test Layers

| Layer | Purpose | Typical command or evidence | Required before DONE? |
|---|---|---|---:|
| Static checks | Catch compile, lint, formatting, and schema issues | Project-specific command | Yes when code changes |
| Unit tests | Verify isolated behavior | Project-specific command | Yes when available |
| Integration tests | Verify external service boundaries | Docker/service smoke result | Yes for infra/API changes |
| Manual smoke test | Verify golden path behavior | Endpoint, UI, CLI, or workflow output | Yes for user-visible behavior |
| Regression check | Confirm related existing behavior still works | Focused command or scenario | Yes for risky changes |

---

## Evidence Rules

- Evidence must be observable and repeatable.
- A passing command, deployed service check, endpoint response, or linked artifact is valid evidence.
- "Looks good" is not evidence.
- If verification cannot run, mark the task `[~] IN PROGRESS` or `[!] BLOCKED` with the reason.

---

## Standard Verification Checklist

| Change type | Minimum verification |
|---|---|
| Documentation only | Link/readability check and index references |
| Configuration | Template check plus runtime location check |
| API behavior | Contract check plus smoke request |
| Pipeline/script | Dry run or focused sample input/output |
| Security control | Positive and negative verification |
| Deployment | Service status plus endpoint smoke test |

---

## Canonical Task Tracker

| Order | ID | Task | Status | Evidence | Next action |
|---:|---|---|---|---|---|
| 1 | TEST-1 | Define project-specific test commands | `[ ] OPEN` | Required commands are listed in this document | Add exact build/test/smoke commands for this repo |

---

*Last updated: 2026-05-02 · Owner: Figur Ulul Azmi*