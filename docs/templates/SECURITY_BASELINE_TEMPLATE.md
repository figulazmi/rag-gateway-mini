# Security Baseline

Baseline security checklist for {{PROJECT_NAME}}.

Use this document to establish minimum security expectations. Detailed security tasks belong in `docs/security/SECURITY_TRACKER.md`.

---

## Secrets and Credentials

| Check | Status | Evidence |
|---|---|---|
| Real secrets are not committed | `[ ] OPEN` | Verify with git status/diff and secret scanning |
| Example config uses placeholders only | `[ ] OPEN` | Check config templates |
| Secret locations are documented | `[ ] OPEN` | `docs/config/CONFIGURATION.md` |
| Rotation process is documented | `[ ] OPEN` | Runbook or secret manager notes |

---

## Dependency and Supply Chain

| Check | Status | Evidence |
|---|---|---|
| Dependency install command is documented | `[ ] OPEN` | Root README and runbook |
| Lockfile policy is documented | `[ ] OPEN` | Project docs |
| Critical dependency owners are known | `[ ] OPEN` | Dependency notes or tracker |

---

## Input and Boundary Safety

| Check | Status | Evidence |
|---|---|---|
| User input boundaries are identified | `[ ] OPEN` | API/UI/CLI docs |
| External service boundaries are identified | `[ ] OPEN` | Configuration and runbook |
| Auth or access assumptions are documented | `[ ] OPEN` | Security tracker or decisions |

---

## Operational Safety

| Check | Status | Evidence |
|---|---|---|
| Destructive operations require explicit confirmation | `[ ] OPEN` | Runbook |
| Rollback path is documented for deployment | `[ ] OPEN` | Runbook |
| Incident log exists | `[x] DONE ({{DATE}})` | `docs/incidents/INCIDENT_LOG.md` |

---

*Last updated: {{DATE}} · Owner: {{OWNER}}*