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

---

## Review Rules

- Review high-level risks at least monthly for active projects.
- Convert a risk into a tracker task when mitigation requires work.
- Move resolved risks to the history section with evidence.

---

## Resolved Risks

| ID | Resolution date | Evidence | Notes |
|---|---|---|---|
| RISK-1 | 2026-05-08 | `testing/TEST_STRATEGY.md` owns the reusable Docs-driven DONE gate through TEST-2, `TASKS.md` is kept as an index only, and Quality/Security status rows were updated only after canonical tracker verification | Keep applying the checklist before marking docs-driven work complete |
| RISK-2 | 2026-05-07 | `git grep` audit across tracked `docs`, `scripts`, `src`, `CLAUDE.md`, and `README.md` found only secret-location guidance and placeholders such as `FILL_WITH_REAL_KEY`; no real secret literal was present in committed docs/examples/templates | Keep using placeholder-only templates and document locations, not values |

---

*Last updated: 2026-05-08 · Owner: Figur Ulul Azmi*