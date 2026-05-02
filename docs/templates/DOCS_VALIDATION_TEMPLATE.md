# Docs Validation

Last updated: {{DATE}}
Last reviewed: {{DATE}}
Owner: {{OWNER}}

Use this file to record documentation validation results from humans or LLM prompt testers.

---

## Validation Inputs

Last updated: {{DATE}}

| Input | Required? | Notes |
|---|---:|---|
| `CONTEXT.md` | Yes | Provides constraints, source-of-truth order, scope, and verification rules |
| `docs/TASKS.md` | Yes | Provides current task index and scope boundaries |
| `docs/reference/TRACKING_STATUS_STANDARD.md` | Recommended | Provides canonical task status rules |
| `docs/architecture/DECISIONS.md` | Recommended | Provides durable decisions |
| `docs/testing/TEST_STRATEGY.md` | Recommended | Provides verification expectations |

---

## Six Prompt Tester Results

Last updated: {{DATE}}

| Set | What it tests | Expected pass signal | Failure interpretation | Fix location |
|---:|---|---|---|---|
| 1 | Context and constraints | Constraints are explicit and actionable | `CONTEXT.md` needs clearer constraints | `CONTEXT.md`, `CONTEXT_TEMPLATE.md` |
| 2 | Freshness metadata | Last updated/reviewed timestamps are visible | Add timestamps to sections | `CONTEXT.md`, tracker footers |
| 3 | Documentation depth | Docs are detailed enough to act on | Add required details and examples | Owning docs and templates |
| 4 | Source-of-truth conflict handling | Current docs override stale RAG/memory | Add docs-over-RAG rule | `CONTEXT.md`, `CLAUDE.md` |
| 5 | Task scope boundaries | Task entries define included/excluded work | Add scope boundary per task | `TASKS.md`, tracker rows |
| 6 | LLM recommendations | Gaps are captured and routed | Record recommendations and owners | This file and owning trackers |

---

## Latest Validation Run

Last updated: {{DATE}}

| Field | Value |
|---|---|
| Date | {{DATE}} |
| Validator | Manual / LLM / CI |
| Result | Not run |
| Evidence | None |
| Follow-up tasks | None |

---

## Recommendations Log

Last updated: {{DATE}}

| ID | Recommendation | Source | Owner | Target doc | Status | Evidence |
|---|---|---|---|---|---|---|
| DOCVAL-1 | Replace this row with the first recommendation | Tester set 6 | {{OWNER}} | Target file | `[ ] OPEN` | Required proof before done |

---

## Pass Criteria

Last updated: {{DATE}}

The docs template is production-ready when:

- Set 1 passes: constraints are explicit in `CONTEXT.md`.
- Set 2 passes: freshness timestamps are visible.
- Set 3 passes: sparse docs have enough minimum detail to act on.
- Set 4 passes: docs-over-RAG conflict rule is explicit.
- Set 5 passes: task scope boundaries are present.
- Set 6 passes: LLM recommendations are recorded and assigned.

---

*Last updated: {{DATE}} · Owner: {{OWNER}}*