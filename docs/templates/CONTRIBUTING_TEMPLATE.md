# Contributing

Contribution workflow for {{PROJECT_NAME}}.

---

## Before You Start

1. Read `docs/ONBOARDING.md`.
2. Check `docs/TASKS.md` for current work.
3. Confirm the owning tracker has a clear next action.
4. Create or use a focused branch for the change.

---

## Change Rules

- Keep changes focused on one outcome.
- Do not mix unrelated refactors with feature or bug work.
- Do not commit secrets, generated caches, local logs, or machine-specific config.
- Update docs when behavior, configuration, operations, or task status changes.

---

## Verification Before Commit

```bash
{{TEST_COMMAND}}
```

If verification cannot run, keep the task `[~] IN PROGRESS` or `[!] BLOCKED` and document why.

---

## Commit Checklist

| Check | Required? |
|---|---:|
| Code/docs focused on one outcome | Yes |
| Tests or verification evidence captured | Yes |
| Owning canonical tracker updated | Yes |
| Changelog updated if notable | Yes |
| No secrets or generated junk staged | Yes |

---

## Pull Request Checklist

- Summary explains why the change exists.
- Test plan lists commands or manual checks run.
- Linked task IDs point to canonical trackers.
- Risks, rollback, or migration notes are included when relevant.

---

*Last updated: {{DATE}} · Owner: {{OWNER}}*