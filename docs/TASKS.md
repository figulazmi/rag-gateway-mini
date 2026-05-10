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
Done: Security posture tracker complete through P2-4; Quality threshold table complete; Testing closure checklist complete; Risk review complete; P3.2 implementation-correctness smoke complete
Open: no active Security, Quality threshold, Testing, or Risk item
Blocked: none listed here
Deferred: P2.2-B, OI-5, Pipeline #2C
Next: Capture /rag/answer implementation-spec chunk and expand knowledge coverage (OI-5)
```

---

## Cross-Area Task Index

| Area | Source of truth | Current focus | Next task ID | Notes |
|---|---|---|---|---|
| Security | [`security/RAG_SECURITY_POSTURE.md`](security/RAG_SECURITY_POSTURE.md) | Security posture tracker complete | Complete | P0 through P2-4 are done in the canonical security tracker |
| Quality | [`quality/RAG_EVAL_HARNESS.md`](quality/RAG_EVAL_HARNESS.md) | Gap-fill follow-up eval complete; corpus at 577 points; hybrid Hit@1 0.9574 MRR 0.9574 NDCG@5 0.9186 | Complete | Keep metric history in quality docs |
| Pipeline | [`pipeline/RAG_BOTTLENECK_FIXES.md`](pipeline/RAG_BOTTLENECK_FIXES.md) | Deferred sparse-text and IDF tuning | #2C | Revisit only if corpus diversity grows and eval shows persistent sparse false positives |
| Planning | [`planning/RAG_V2_ROADMAP.md`](planning/RAG_V2_ROADMAP.md) | P3.2 smoke complete; /rag/search implementation-spec captured and pushed; harness at scripts/smoke-p32-implementation-correctness.py | OI-5 / /rag/answer spec | Next: capture /rag/answer spec, then open OI-5 coverage work |
| Coverage | [`quality/COVERAGE_KNOWLEDGE_TRACKER.md`](quality/COVERAGE_KNOWLEDGE_TRACKER.md) | Knowledge coverage improvement | OI-5 | Ready to open: implementation-spec capture is now active (P3.2 DONE) |
| Reference | [`reference/RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md`](reference/RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md) | New device/server bootstrap | See tracker | Use only for migration or rebuild work |
| Testing | [`testing/TEST_STRATEGY.md`](testing/TEST_STRATEGY.md) | Docs-driven DONE gate checklist is now reusable guidance | Complete | Mitigates RISK-1 documentation drift with a canonical closure checklist |
| Configuration | [`config/CONFIGURATION.md`](config/CONFIGURATION.md) | Keep runtime settings and secret locations documented | See document | Do not store secrets in docs |
| Risk | [`risks/RISK_REGISTER.md`](risks/RISK_REGISTER.md) | Risk review complete | Complete | Convert new risks into tracker tasks only when active mitigation work is needed |
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

*Last updated: 2026-05-08 · Owner: Figur Ulul Azmi*