# Automation

Use this document for CI/CD, hooks, scheduled tasks, cron jobs, bots, and recurring agents.

---

## Automation Inventory

| ID | Automation | Trigger | Owner | Location | Status | Notes |
|---|---|---|---|---|---|---|
| AUTO-1 | Example automation | On push / cron / manual | {{OWNER}} | Path or URL | `[ ] OPEN` | Replace this row |

---

## CI/CD

| Workflow | Trigger | Required checks | Deploy target | Rollback |
|---|---|---|---|---|
| Example workflow | Push to main | `{{TEST_COMMAND}}` | Target environment | Rollback procedure |

---

## Local Hooks

| Hook | Trigger | Purpose | Location | Safe to skip? |
|---|---|---|---|---:|
| Example hook | Pre-commit | Validate files | Path | No |

---

## Scheduled Jobs

| Job | Schedule | Purpose | Owner | Failure signal |
|---|---|---|---|---|
| Example job | Daily / weekly / cron | What it does | {{OWNER}} | Alert/log/check |

---

## Change Rules

- Document every automation that can modify files, deploy code, send notifications, or affect shared state.
- Include rollback or disable steps for production automation.
- Keep secrets out of workflow files unless they reference a secret store.

---

*Last updated: {{DATE}} · Owner: {{OWNER}}*