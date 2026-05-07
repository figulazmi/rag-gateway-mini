# Task Index

This file is the cross-document entry point for active work.

It is an index, not the source of truth. Each task status must be owned by the `## Canonical Task Tracker` inside the linked document.

---

## Source of Truth Rule

- Use this file to find the next task quickly.
- Update detailed status only in the owning tracker.
- Link to task IDs instead of copying evidence or status text.
- If a row here looks stale, verify the owning canonical tracker first.

---

## Quick Status

```text
Done: P1-3, P1-4, P1-5, P2-1, P2-3, and P2-4 completed in security tracker; see owning tracker for full evidence
Open: Security P2-2
Blocked: none listed here
Deferred: P2.2-B, OI-5
Next: Finish P2-2 verification and close the remaining citation-grounding gap
```

---

## Cross-Area Task Index

| Area | Source of truth | Current focus | Next task ID | Notes |
|---|---|---|---|---|
| Security | [`security/RAG_SECURITY_POSTURE.md`](security/RAG_SECURITY_POSTURE.md) | Finish `/rag/answer` verification and close citation-grounding rollout | P2-2 | P2-3 and P2-4 are complete; use security tracker for remaining P2-2 evidence |
| Quality | [`quality/RAG_EVAL_HARNESS.md`](quality/RAG_EVAL_HARNESS.md) | Broaden eval beyond retrieval-only metrics | See tracker | Keep metric history in quality docs |
| Pipeline | [`pipeline/RAG_BOTTLENECK_FIXES.md`](pipeline/RAG_BOTTLENECK_FIXES.md) | Deferred sparse-text and IDF tuning | #2C | Revisit after corpus diversity improves |
| Planning | [`planning/RAG_V2_ROADMAP.md`](planning/RAG_V2_ROADMAP.md) | Keyfacts production default maintenance | See tracker | Read before pipeline changes |
| Coverage | [`quality/COVERAGE_KNOWLEDGE_TRACKER.md`](quality/COVERAGE_KNOWLEDGE_TRACKER.md) | Knowledge coverage improvement | OI-5 | Deferred until implementation-spec capture is active |
| Reference | [`reference/RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md`](reference/RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md) | New device/server bootstrap | See tracker | Use only for migration or rebuild work |
| Testing | [`testing/TEST_STRATEGY.md`](testing/TEST_STRATEGY.md) | Maintain exact repo verification commands | See tracker | Required before using this docs system as a strict DONE gate |
| Configuration | [`config/CONFIGURATION.md`](config/CONFIGURATION.md) | Keep runtime settings and secret locations documented | See document | Do not store secrets in docs |
| Risk | [`risks/RISK_REGISTER.md`](risks/RISK_REGISTER.md) | Review documentation drift and secret exposure risks | RISK-1 | Convert mitigation into tracker task if active work is needed |
| Incidents | [`incidents/INCIDENT_LOG.md`](incidents/INCIDENT_LOG.md) | Record production-impacting failures only | None | Use changelog for normal completed changes |

---

## Add a New Area

When a new tracker is added, append one row here:

```markdown
| Area name | [`path/TO_TRACKER.md`](path/TO_TRACKER.md) | Current focus | TASK-ID | One operational note |
```

The linked tracker must contain exactly one `## Canonical Task Tracker` section.

---

## Update Discipline

1. Update the owning canonical tracker first.
2. Update this index only if the current focus or next task ID changes.
3. Do not paste detailed evidence here.
4. Before reporting a task complete, search for its task ID and update stale references.

---

*Last updated: 2026-05-07 · Owner: Figur Ulul Azmi*