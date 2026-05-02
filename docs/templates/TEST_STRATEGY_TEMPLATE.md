# Test Strategy

Use this template to define verification expectations.

---

## Test Layers

| Layer | Purpose | Command or evidence | Required before DONE? |
|---|---|---|---:|
| Static checks | Compile, lint, format, schema | `command` | Yes when code changes |
| Unit tests | Isolated behavior | `command` | Yes when available |
| Integration tests | External service boundary | `command` | Yes for service changes |
| Manual smoke test | Golden path behavior | Endpoint/UI/CLI result | Yes for user-visible behavior |
| Regression check | Related existing behavior | Focused command or scenario | Yes for risky changes |

---

## Evidence Rules

- Evidence must be observable and repeatable.
- Passing command output, endpoint response, deployed check, or linked artifact is valid evidence.
- If verification cannot run, do not mark the task DONE.

---

## Canonical Task Tracker

| Order | ID | Task | Status | Evidence | Next action |
|---:|---|---|---|---|---|
| 1 | TEST-1 | Define exact project test commands | `[ ] OPEN` | Commands listed in this document | Add commands |

---

*Last updated: YYYY-MM-DD · Owner: NAME*