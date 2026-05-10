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
Open: SS-1 semi-auto capture assistant workflow plan is ready for implementation
Blocked: none
Deferred: P2.2-B (reranker — needs TEI+BGE on VM B1), Pipeline #2C (sparse IDF tuning)
Next: Implement SS-1 semi-auto capture workflow, then continue steady-state maintenance as features ship
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
| Steady State | This file | Semi-auto capture workflow planned for implementation | SS-1 | Implement a user-confirmed capture assistant before considering full auto-capture |

---

## Steady-State Backlog

### SS-1 — Level 1 Semi-Auto Knowledge Capture

**Status:** Planned

**Goal:** Reduce manual capture effort while preserving user control and Qdrant corpus quality. The workflow should detect when a task appears solved, propose a draft capture, ask for approval, then run the existing local `rag add` → `rag merge` → auto-push pipeline only after confirmation.

**Why this is next:** P1-P4 are closed, and future ROI now depends on keeping `knowledge_v2_keyfacts` current without polluting it. Full auto-capture has higher false-positive risk. Semi-auto capture gives most of the effort reduction while keeping a review gate.

**Scope:**

- Add a semi-auto capture workflow around the existing local capture toolchain.
- Reuse `~/scripts/rag-capture-v2/rag_capture.py` and existing `rag merge` auto-push behavior.
- Keep all persistence local until the user approves capture.
- Do not change n8n, Qdrant schema, vector search, or eval scoring for this task.

**Non-goals:**

- No silent full-auto capture.
- No background writes to Qdrant without explicit user approval.
- No new chunk schema unless required by existing validators.
- No reranker, sparse IDF tuning, or retrieval algorithm changes.

**Recommended implementation approach:**

1. **Define solved-task detection rules.**
   - Trigger candidates when the user says signals such as `works`, `berhasil`, `fixed`, `oke sudah`, or asks to save/capture.
   - Trigger candidates when a verified build/test/smoke passes after a fix.
   - Do not trigger on intermediate debugging, failed attempts, pure discussion, or typo-only edits.

2. **Create a capture proposal object.**
   - Fields: topic, chunk_type, project, tags, environment, status, source summary, target files, verification evidence, and proposed key facts.
   - Enforce topic ASCII and max 60 chars before showing the proposal.
   - Default project for this repo: `homelab`.
   - Default status: `implemented`.

3. **Add a user approval gate.**
   - Present a concise proposal in card format, not a markdown table.
   - Choices: `Approve`, `Edit`, `Skip`.
   - `Approve` runs capture immediately.
   - `Edit` lets the user change topic, type, tags, or key facts before running.
   - `Skip` records nothing and does not create drafts.

4. **Generate the chunk body after approval.**
   - Use existing section rules: `### Context`, `### Problem`, `### Solution`, `### Key Facts`, optional `### Code`.
   - For `implementation-spec`, include required sections: `### Target Files`, `### Interfaces`, `### Dependencies`, `### Contract`, `### Anti-Patterns`, `### Verification`, `### Key Facts`.
   - Avoid em dash, non-ASCII topic text, placeholder values, and angle-bracket examples that can break shell handling.

5. **Execute the existing pipeline locally.**
   - Run `rtk python ~/scripts/rag-capture-v2/rag_capture.py add ...` using heredoc input.
   - Run `rtk python ~/scripts/rag-capture-v2/rag_capture.py merge -p homelab --output YYYY-MM-DD-short-topic.md`.
   - Rely on current `rag merge` auto-push behavior to call `push-to-qdrant.sh`.
   - Confirm Qdrant point delta and HTTP 200 result from command output.

6. **Add validation and failure handling.**
   - Before `rag add`, validate topic length <= 60 and `topic.isascii()`.
   - If `rag add` rejects content, sanitize and retry once after explaining the exact validation error.
   - If merge push partially fails, inspect the failed chunk title and frontmatter topic first.
   - Never use `Write` to create `.claude/summaries/*.md`; only `rag_capture.py merge` may do that.

7. **Document operator usage.**
   - Add a short runbook section explaining when to approve, edit, or skip.
   - Include examples of high-value captures: debug fix, feature implementation, runbook, implementation-spec.
   - Include examples to skip: typo fixes, failed hypotheses, pure brainstorming, temporary logs.

8. **Verification checklist.**
   - Dry-run with one approved debug chunk using a safe topic under 60 chars.
   - Confirm draft is created in the local draft folder.
   - Confirm merge creates `.claude/summaries/YYYY-MM-DD-*.md`.
   - Confirm auto-push returns HTTP 200 and Qdrant point count increases or updates.
   - Query `search_knowledge` for the topic and confirm the new chunk is retrievable.
   - Confirm `docs/TASKS.md` can be updated from `Planned` to `Done` after verification.

**Acceptance criteria:**

- User is prompted before any new knowledge chunk is persisted or pushed.
- Approved capture completes with `rag add`, `rag merge`, and Qdrant push using existing tooling.
- Skipped capture creates no draft and no Qdrant point.
- Topic validation prevents the known n8n `must be ASCII and 1-60 chars` error.
- The final operator workflow is documented enough to resume in a new Claude Code session.

**Parallelization:**

- Can run independently from P2.2-B reranker and Pipeline #2C.
- Should not run in parallel with edits to `rag_capture.py` or `push-to-qdrant.sh` unless using separate worktrees.

**Next action for tomorrow:**

Start from SS-1 step 1: decide whether the semi-auto workflow should live as a Claude Code instruction/skill update, a wrapper script around `rag_capture.py`, or both. Recommended first implementation is instruction/skill-level orchestration that reuses the existing CLI unchanged.

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