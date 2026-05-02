# Configuration

Use this template for environment variables, config files, secret locations, and safe defaults.

Do not store secrets in this file.

---

## Configuration Sources

| Source | Purpose | Secret? | Notes |
|---|---|---:|---|
| `.env.example` | Local environment template | No | Commit placeholders only |
| Production secret store | Runtime secrets | Yes | Document location, not values |

---

## Required Settings

| Key | Required | Example | Owner | Notes |
|---|---:|---|---|---|
| `SETTING_NAME` | Yes | `placeholder` | Team or system | Explanation |

---

## Secrets Rules

- Commit examples and templates only.
- Keep real secrets outside git.
- Document rotation and recovery steps.
- Verify examples do not contain live credentials.

---

## Configuration Change Checklist

| Check | Required? |
|---|---:|
| Template updated | Yes |
| Runtime location documented | Yes |
| Secret excluded from git | Yes |
| Restart/deploy steps documented | Yes |
| Verification command documented | Yes |

---

*Last updated: YYYY-MM-DD · Owner: NAME*