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
Done: see owning trackers
Open: P0-3, P2.3
Blocked: none listed here
Deferred: P2.2, P2.2-B, OI-5
Next: P0-3 - harden cosine gate verification failure handling
```

---

## Cross-Area Task Index

| Area | Source of truth | Current focus | Next task ID | Notes |
|---|---|---|---|---|
| Security | [`security/RAG_SECURITY_POSTURE.md`](security/RAG_SECURITY_POSTURE.md) | Hardening and threat controls | P0-3 | Use security tracker for evidence and verification steps |
| Quality | [`quality/RAG_EVAL_HARNESS.md`](quality/RAG_EVAL_HARNESS.md) | Broaden eval beyond retrieval-only metrics | See tracker | Keep metric history in quality docs |
| Pipeline | [`pipeline/RAG_BOTTLENECK_FIXES.md`](pipeline/RAG_BOTTLENECK_FIXES.md) | Deferred sparse-text and IDF tuning | #2C | Revisit after corpus diversity improves |
| Planning | [`planning/RAG_V2_ROADMAP.md`](planning/RAG_V2_ROADMAP.md) | RAG v2 implementation roadmap | P2.3 | Read before pipeline changes |
| Coverage | [`quality/COVERAGE_KNOWLEDGE_TRACKER.md`](quality/COVERAGE_KNOWLEDGE_TRACKER.md) | Knowledge coverage improvement | OI-5 | Deferred until implementation-spec capture is active |
| Reference | [`reference/RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md`](reference/RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md) | New device/server bootstrap | See tracker | Use only for migration or rebuild work |

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

*Last updated: 2026-05-02 · Owner: Figur Ulul Azmi*