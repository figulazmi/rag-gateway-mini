# docs/ — Navigation Index

All documents cover the RAG knowledge pipeline for `rag-gateway-mini`
(stack: Qdrant `knowledge_v2` · nomic-embed-text · Ollama · n8n · ASP.NET Core 9 · VM B1).

> All tracking docs should follow [`reference/TRACKING_STATUS_STANDARD.md`](reference/TRACKING_STATUS_STANDARD.md) to avoid stale duplicate status checklists.

---

## Folder Structure

```
docs/
  README.md     — navigation index and reading order
  TASKS.md      — cross-document active task index
  ONBOARDING.md — fast-start guide for contributors and future agents
  planning/     — roadmaps, strategic plans, restoration plans
  architecture/ — durable architecture and workflow decisions
  pipeline/     — ingestion & retrieval pipeline: fixes, gaps, session continuity
  quality/      — retrieval evaluation, Qdrant health audit, coverage tracking
  security/     — security posture hardening & threat model tracker
  testing/      — test strategy and verification expectations
  config/       — configuration, environment, and secret location docs
  reference/    — manual book, runbooks, standards, templates
  history/      — notable completed changes
  incidents/    — incident records and post-incident follow-up
  risks/        — risk register and mitigation tracking
  templates/    — reusable blank templates for other projects
```

---

## Fast Start

| Document | Purpose | Status |
|---|---|---|
| [TASKS.md](TASKS.md) | Cross-document active task index; links to canonical trackers without owning detailed status | Active |
| [ONBOARDING.md](ONBOARDING.md) | 15-minute onboarding path, definition of ready, and definition of done | Active |

---

## pipeline/ — Ingestion & Retrieval

| Document | Purpose | Status |
|---|---|---|
| [RAG_BOTTLENECK_FIXES.md](pipeline/RAG_BOTTLENECK_FIXES.md) | Pipeline A (write/ingest) and Pipeline B (read/retrieve) bottleneck fixes with test evidence | Active |
| [RAG_CAPTURE_PIPELINE_GAPS.md](pipeline/RAG_CAPTURE_PIPELINE_GAPS.md) | Gap analysis: `rag add` → `rag merge` → `push-to-qdrant.sh` → n8n → Qdrant | Active |
| [RAG_CHECKPOINT_SYSTEM.md](pipeline/RAG_CHECKPOINT_SYSTEM.md) | Session continuity: `rag checkpoint`, `rag resume`, `rag promote` commands | Reference |

---

## quality/ — Retrieval Quality

| Document | Purpose | Status |
|---|---|---|
| [RAG_EVAL_HARNESS.md](quality/RAG_EVAL_HARNESS.md) | Benchmark metrics (MRR@5, faithfulness), labeled query set, score tracking | Active |
| [RAG_QDRANT_AUDIT.md](quality/RAG_QDRANT_AUDIT.md) | 5-dimension health audit: score 6.8/10 → 8.1/10 + fix tracker | Active |
| [COVERAGE_KNOWLEDGE_TRACKER.md](quality/COVERAGE_KNOWLEDGE_TRACKER.md) | Before/after history for every coverage improvement | Active |

---

## security/ — Security Posture

| Document | Purpose | Status |
|---|---|---|
| [RAG_POWER_SECURITY_INDEX.md](security/RAG_POWER_SECURITY_INDEX.md) | **Entry point** — priority board P0/P1/P2 with quick nav to all items | Active |
| [RAG_SECURITY_POSTURE.md](security/RAG_SECURITY_POSTURE.md) | Phase 1–3 hardening tracker: threat model, fix steps, verification commands | Active |

---

## planning/ — Roadmaps & Plans

| Document | Purpose | Status |
|---|---|---|
| [RAG_V2_ROADMAP.md](planning/RAG_V2_ROADMAP.md) | Active feature roadmap for `knowledge_v2` — P1/P2/P3 priorities, strategic goal | **Active — read before any pipeline change** |
| [RAG_EXTERNAL_BRAIN_PLAN.md](planning/RAG_EXTERNAL_BRAIN_PLAN.md) | Strategic improvement plan: reliability → quality → implementer-grade chunks | Reference |
| [VM105_RESTORATION_PLAN.md](planning/VM105_RESTORATION_PLAN.md) | VM105 restore gap checklist against VM B1 April 27 target; live verification shows current VM has 368 `knowledge_v2` points | Active |

---

## architecture/ — Decisions

| Document | Purpose | Status |
|---|---|---|
| [DECISIONS.md](architecture/DECISIONS.md) | Durable architecture and workflow decisions with rationale and consequences | Active |

---

## testing/ — Verification

| Document | Purpose | Status |
|---|---|---|
| [TEST_STRATEGY.md](testing/TEST_STRATEGY.md) | Test layers, evidence rules, and verification expectations before DONE | Active |

---

## config/ — Configuration

| Document | Purpose | Status |
|---|---|---|
| [CONFIGURATION.md](config/CONFIGURATION.md) | Configuration sources, required settings, secret rules, and change checklist | Active |

---

## reference/ — Manual & Runbooks

| Document | Purpose | Status |
|---|---|---|
| [RAG_MANUAL_BOOK.md](reference/RAG_MANUAL_BOOK.md) | Complete operational manual: commands, config, troubleshooting, architecture | Reference |
| [RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md](reference/RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md) | Bootstrap/disaster-recovery checklist for new local device or server rebuild | Active |
| [TRACKING_STATUS_STANDARD.md](reference/TRACKING_STATUS_STANDARD.md) | Canonical status table standard for all docs trackers | Active |
| [PROJECT_DOCS_TEMPLATE.md](reference/PROJECT_DOCS_TEMPLATE.md) | Copyable documentation structure template for other projects | Active |

---

## history/ — Change History

| Document | Purpose | Status |
|---|---|---|
| [CHANGELOG.md](history/CHANGELOG.md) | Notable completed changes; not a todo list | Active |

---

## incidents/ — Incident Records

| Document | Purpose | Status |
|---|---|---|
| [INCIDENT_LOG.md](incidents/INCIDENT_LOG.md) | Production-impacting failures, post-incident evidence, and follow-up links | Active |

---

## risks/ — Risk Register

| Document | Purpose | Status |
|---|---|---|
| [RISK_REGISTER.md](risks/RISK_REGISTER.md) | Risks, mitigations, owners, review dates, and related tasks | Active |

---

## templates/ — Blank Reusable Templates

| Document | Purpose | Status |
|---|---|---|
| [ROOT_README_TEMPLATE.md](templates/ROOT_README_TEMPLATE.md) | Blank root project README | Template |
| [CLAUDE_TEMPLATE.md](templates/CLAUDE_TEMPLATE.md) | Blank project instructions for Claude Code and future agents | Template |
| [CONTRIBUTING_TEMPLATE.md](templates/CONTRIBUTING_TEMPLATE.md) | Blank contribution workflow | Template |
| [TASKS_TEMPLATE.md](templates/TASKS_TEMPLATE.md) | Blank cross-document task index | Template |
| [TRACKER_TEMPLATE.md](templates/TRACKER_TEMPLATE.md) | Blank canonical tracker | Template |
| [ADR_TEMPLATE.md](templates/ADR_TEMPLATE.md) | Blank architecture decision record | Template |
| [CHANGELOG_TEMPLATE.md](templates/CHANGELOG_TEMPLATE.md) | Blank change history entry | Template |
| [RUNBOOK_TEMPLATE.md](templates/RUNBOOK_TEMPLATE.md) | Blank operational runbook | Template |
| [CONFIGURATION_TEMPLATE.md](templates/CONFIGURATION_TEMPLATE.md) | Blank configuration guide | Template |
| [TEST_STRATEGY_TEMPLATE.md](templates/TEST_STRATEGY_TEMPLATE.md) | Blank test strategy | Template |
| [ONBOARDING_TEMPLATE.md](templates/ONBOARDING_TEMPLATE.md) | Blank onboarding guide | Template |
| [RISK_REGISTER_TEMPLATE.md](templates/RISK_REGISTER_TEMPLATE.md) | Blank risk register | Template |
| [INCIDENT_LOG_TEMPLATE.md](templates/INCIDENT_LOG_TEMPLATE.md) | Blank incident log | Template |
| [SECURITY_BASELINE_TEMPLATE.md](templates/SECURITY_BASELINE_TEMPLATE.md) | Blank security baseline checklist | Template |
| [AUTOMATION_TEMPLATE.md](templates/AUTOMATION_TEMPLATE.md) | Blank CI/CD, hook, cron, and scheduled automation inventory | Template |

---

## Reading Order (new contributor / new session)

1. [`ONBOARDING.md`](ONBOARDING.md) — 15-minute fast-start path
2. [`TASKS.md`](TASKS.md) — active cross-document task index
3. [`planning/RAG_V2_ROADMAP.md`](planning/RAG_V2_ROADMAP.md) — strategic goal and current priorities
4. [`quality/RAG_QDRANT_AUDIT.md`](quality/RAG_QDRANT_AUDIT.md) — current health score and open issues
5. [`pipeline/RAG_BOTTLENECK_FIXES.md`](pipeline/RAG_BOTTLENECK_FIXES.md) — what's already been fixed in retrieval
6. [`pipeline/RAG_CAPTURE_PIPELINE_GAPS.md`](pipeline/RAG_CAPTURE_PIPELINE_GAPS.md) — what's been fixed in capture
7. [`security/RAG_POWER_SECURITY_INDEX.md`](security/RAG_POWER_SECURITY_INDEX.md) — security hardening status
8. [`testing/TEST_STRATEGY.md`](testing/TEST_STRATEGY.md) — verification rules before DONE
9. [`config/CONFIGURATION.md`](config/CONFIGURATION.md) — runtime settings and secret handling
10. [`architecture/DECISIONS.md`](architecture/DECISIONS.md) — durable decisions and tradeoffs
11. [`history/CHANGELOG.md`](history/CHANGELOG.md) — notable completed changes

---

## Quick Status: Open Priorities

| Area | Highest open item | Doc |
|---|---|---|
| Security | P0-3: Harden cosine gate (hard abort on verification failure) | [security/RAG_SECURITY_POSTURE.md](security/RAG_SECURITY_POSTURE.md#p0-3--harden-cosine-gate-hard-abort) |
| Quality | Expand measured baseline beyond retrieval-only metrics (faithfulness, latency, relevance) | [quality/RAG_EVAL_HARNESS.md](quality/RAG_EVAL_HARNESS.md#5-baseline-vs-current-comparison) |
| Pipeline | IDF weighting (Opsi C) — deferred (revisit after corpus diversity and post-baseline metrics) | [pipeline/RAG_BOTTLENECK_FIXES.md](pipeline/RAG_BOTTLENECK_FIXES.md#7--idf-weighting-mismatch-between-c-and-qdrant-bm25-) |
| Reference | New device/server bootstrap checklist is available for future migration/rebuilds | [reference/RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md](reference/RAG_BOOTSTRAP_NEW_DEVICE_AND_SERVER.md) |
| Planning | VM105 restore checklist: current VM verified at 368 points; use remaining-fix list only when rebuilding from Apr 13 backup | [planning/VM105_RESTORATION_PLAN.md](planning/VM105_RESTORATION_PLAN.md) |

---

*Last updated: 2026-05-02 · Owner: Figur Ulul Azmi*  
*Update this index when adding new docs or changing subfolder structure.*
