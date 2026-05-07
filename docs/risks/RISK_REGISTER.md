# Risk Register

Use this file to track risks before they become incidents.

Active mitigation work should link to a canonical tracker task instead of duplicating status here.

---

## Risk Scoring

| Score | Meaning |
|---:|---|
| 1 | Low impact or unlikely |
| 2 | Moderate impact or plausible |
| 3 | High impact, likely, or hard to recover |

Risk level = impact x likelihood.

---

## Active Risks

| ID | Risk | Impact | Likelihood | Level | Mitigation | Owner | Review date | Related task |
|---|---|---:|---:|---:|---|---|---|---|
| RISK-1 | Documentation status drift causes wrong task selection | 2 | 1 | 2 | Keep status in canonical trackers only, use `TASKS.md` as index, and require the reusable `Docs-driven DONE gate` checklist in `testing/TEST_STRATEGY.md` before marking docs-driven work done | Figur Ulul Azmi | 2026-06-02 | TEST-2 |

---

## Review Rules

- Review high-level risks at least monthly for active projects.
- Convert a risk into a tracker task when mitigation requires work.
- Move resolved risks to the history section with evidence.

---

## Resolved Risks

| ID | Resolution date | Evidence | Notes |
|---|---|---|---|
| RISK-2 | 2026-05-07 | `git grep` audit across tracked `docs`, `scripts`, `src`, `CLAUDE.md`, and `README.md` found only secret-location guidance and placeholders such as `FILL_WITH_REAL_KEY`; no real secret literal was present in committed docs/examples/templates | Keep using placeholder-only templates and document locations, not values |

---

*Last updated: 2026-05-07 · Owner: Figur Ulul Azmi*