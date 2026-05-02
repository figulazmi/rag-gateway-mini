# Project Documentation Template

Use this template when starting or refactoring documentation for another project.

The goal is to keep navigation, task status, decisions, runbooks, and history separate so documentation stays useful as the project changes.

---

## Recommended Folder Structure

```text
docs/
  README.md                         # navigation and reading order
  TASKS.md                          # cross-document active task index
  ONBOARDING.md                     # fast-start guide and working rules
  planning/
    ROADMAP.md                      # strategic roadmap and canonical roadmap tasks
  architecture/
    DECISIONS.md                    # durable architecture/workflow decisions
  quality/
    QUALITY_TRACKER.md              # quality metrics, audits, and improvements
  security/
    SECURITY_TRACKER.md             # security hardening tracker
  testing/
    TEST_STRATEGY.md                # verification layers and evidence rules
  config/
    CONFIGURATION.md                # configuration sources and secret locations
  reference/
    RUNBOOK.md                      # operational commands and procedures
    TRACKING_STATUS_STANDARD.md     # canonical task tracker rules
    PROJECT_DOCS_TEMPLATE.md        # reusable template
  history/
    CHANGELOG.md                    # notable completed changes
  incidents/
    INCIDENT_LOG.md                 # incident records and follow-up links
  risks/
    RISK_REGISTER.md                # risks, mitigations, and review dates
  templates/
    *_TEMPLATE.md                   # blank reusable docs templates
```

---

## README.md Starter

```markdown
# docs/ - Navigation Index

Short description of the project and what these docs cover.

> Active task status lives in each document's `## Canonical Task Tracker`. Use `TASKS.md` only as a cross-document index.

## Folder Structure

| Folder | Purpose |
|---|---|
| planning/ | Roadmaps and strategic plans |
| architecture/ | Durable decisions and tradeoffs |
| quality/ | Evaluation, audit, and quality trackers |
| security/ | Security posture and hardening trackers |
| testing/ | Test strategy and evidence rules |
| config/ | Runtime settings and secret locations |
| reference/ | Runbooks, standards, and templates |
| history/ | Notable completed changes |
| incidents/ | Incident records and follow-up links |
| risks/ | Risk register and mitigation tracking |
| templates/ | Blank reusable templates |

## Reading Order

1. `ONBOARDING.md` - fast-start path
2. `TASKS.md` - current active work
3. `planning/ROADMAP.md` - roadmap and priorities
4. `reference/RUNBOOK.md` - operational procedures
5. `testing/TEST_STRATEGY.md` - verification rules
6. `config/CONFIGURATION.md` - runtime settings and secrets handling
7. `architecture/DECISIONS.md` - why key choices were made

## Quick Status

| Area | Highest open item | Source |
|---|---|---|
| Planning | TASK-ID | `planning/ROADMAP.md` |
```

---

## TASKS.md Starter

````markdown
# Task Index

This file is an index, not the source of truth. Each task status is owned by the linked document's `## Canonical Task Tracker`.

## Quick Status

```text
Done: see owning trackers
Open: TASK-ID
Blocked: None
Next: TASK-ID - short next action
```

## Cross-Area Task Index

| Area | Source of truth | Current focus | Next task ID | Notes |
|---|---|---|---|---|
| Planning | `planning/ROADMAP.md` | Current roadmap focus | P1-A | Keep evidence in roadmap tracker |
````

---

## Tracker Starter

Use this in roadmap, quality, security, pipeline, migration, or audit docs.

```markdown
# Tracker Title

Purpose and scope of this tracker.

Legacy sections may contain historical status text. Current source of truth is [Canonical Task Tracker](#canonical-task-tracker).

## Context

Why this tracker exists.

## Current Findings

Facts, metrics, analysis, or design notes. Avoid owning task status here.

## Canonical Task Tracker

| Order | ID | Task | Status | Evidence | Next action |
|---:|---|---|---|---|---|
| 1 | P1-A | Implement one concrete outcome | `[ ] OPEN` | Required proof before done | Exact next command or decision |

---

*Last updated: YYYY-MM-DD · Owner: NAME*
```

---

## DECISIONS.md Starter

```markdown
# Architecture Decisions

## ADR-000 - Short decision title

| Field | Value |
|---|---|
| Date | YYYY-MM-DD |
| Status | Proposed / Accepted / Superseded / Deprecated |
| Context | Constraint or tradeoff |
| Decision | Chosen approach |
| Consequences | What changes because of this decision |
| Related docs | Links |
```

---

## CHANGELOG.md Starter

```markdown
# Change History

## YYYY-MM-DD - Short change title

| Field | Value |
|---|---|
| Type | docs / code / infra / security / quality / decision |
| Summary | What changed |
| Evidence | Command output, PR, commit, deployed check, or doc link |
| Related tasks | TASK-ID or `None` |
| Follow-up | TASK-ID or `None` |
```

---

## Rules for Reuse

1. Keep `README.md` focused on navigation and reading order.
2. Keep `ONBOARDING.md` focused on fast-start workflow and definitions.
3. Keep `TASKS.md` focused on cross-document task discovery.
4. Keep task status in exactly one canonical tracker per document.
5. Keep `CHANGELOG.md` for completed notable changes only.
6. Keep `DECISIONS.md` for why choices were made, not implementation todos.
7. Keep `CONFIGURATION.md` free of real secrets.
8. Keep `TEST_STRATEGY.md` focused on repeatable evidence.
9. Require evidence before marking a task `[x] DONE (YYYY-MM-DD)`.
10. Search for task IDs before reporting completion to avoid stale references.

---

## Blank Templates

Copy files from `docs/templates/` when bootstrapping another project, then rename them to the project-specific paths listed above.

---

*Last updated: 2026-05-02 · Owner: Figur Ulul Azmi*