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
Done: All P1-P4 roadmap items complete. P4: reusable RAG scripts moved to rag-tools repo, 6 migration scripts archived, pre-commit frontmatter hook implemented + installed. OI-5: 7 implementation-spec chunks pushed, corpus 602→604, coverage 8.0/10.
Open: none — roadmap P1 through P4 is fully closed
Blocked: none
Deferred: P2.2-B (reranker — needs TEI+BGE on VM B1), Pipeline #2C (sparse IDF tuning)
Next: Steady-state maintenance — capture new chunks as features ship; revisit P2.2-B when TEI infra is ready
```

---

## Cross-Area Task Index

| Area | Source of truth | Current focus | Next task ID | Notes |
|---|---|---|---|---|
| Security | [`security/RAG_SECURITY_POSTURE.md`](security/RAG_SECURITY_POSTURE.md) | Security posture tracker complete | Complete | P0 through P2-4 are done in the canonical security tracker |
| Quality | [`quality/RAG_EVAL_HARNESS.md`](quality/RAG_EVAL_HARNESS.md) | Gap-fill follow-up eval complete; corpus at 604 points; hybrid Hit@1 0.9574 MRR 0.9574 NDCG@5 0.9186 | Complete | Keep metric history in quality docs; re-run eval if fixture regressions appear |
| Pipeline | [`pipeline/RAG_BOTTLENECK_FIXES.md`](pipeline/RAG_BOTTLENECK_FIXES.md) | Deferred sparse-text and IDF tuning | #2C | Revisit only if corpus diversity grows and eval shows persistent sparse false positives |
| Planning | [`planning/RAG_V2_ROADMAP.md`](planning/RAG_V2_ROADMAP.md) | P1-P4 complete; reusable scripts moved to rag-tools; frontmatter hook implemented and installed | Complete | No active roadmap item; only deferred infra-dependent work remains |
| Coverage | [`quality/COVERAGE_KNOWLEDGE_TRACKER.md`](quality/COVERAGE_KNOWLEDGE_TRACKER.md) | OI-5 complete: 7 implementation-spec chunks captured (2026-05-10); corpus 602 → 604; score 8.0/10 | Complete | Maintain capture discipline for new work |
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

*Last updated: 2026-05-10 · Owner: Figur Ulul Azmi*