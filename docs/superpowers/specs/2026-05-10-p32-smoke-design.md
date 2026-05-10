# P3.2 Implementation-Correctness Smoke — Design Spec

**Date:** 2026-05-10
**Status:** Ready for parallel execution
**Owner:** Figur Ulul Azmi
**Roadmap source:** `docs/planning/RAG_V2_ROADMAP.md` — P3.2

---

## Purpose and Scope

Validate whether a 9routers-managed AI assistant can implement code directly from a retrieved `implementation-spec` chunk without hallucinating extra files, routes, config keys, or DTO fields.

**In scope:**
- Retrieve exactly one implemented homelab `implementation-spec` chunk via the gateway or MCP.
- Feed the chunk to a 9routers-routed assistant with a bounded implementation instruction.
- Verify produced code against the chunk contract.
- Record outcome and push results.

**Out of scope:**
- Retrieval optimization, RRF tuning, reranker work (P2.2-B).
- qwen2.5-coder benchmark runs (optional, not the production path).
- New chunk capture or knowledge-base expansion.

---

## Inputs

Retrieve exactly one implemented spec. Preferred first cases (in order):

| Priority | Query | Expected contract |
|---|---|---|
| 1 | `rag gateway retrieval service contract` | `/rag/search` thresholds and response shape |
| 2 | `rag gateway knowledge expansion retrieval` | Variant generation and aggregation rules |
| 3 | grounded answer path spec once captured | `/rag/answer` plus citation tagging |

**Retrieval command (MCP):**
```bash
# In Claude Code — use MCP tool
search_knowledge("rag gateway retrieval service contract implementation spec target files interfaces", project="homelab")
```

**Retrieval command (gateway HTTP):**
```bash
rtk curl -s -X POST http://192.168.18.199:5200/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query":"rag gateway retrieval service contract","project":"homelab","chunk_type":"implementation-spec","knowledge_expansion":false}'
```

If the returned `status` is `not_found`, fall back to the next priority case. If all three return `not_found`, do not proceed — capture a spec first.

---

## Task 2 — Manual Smoke Run Workflow

**Operator:** human running Claude Code, one session, one worktree.

### Step 1 — Retrieve

Run one of the retrieval commands above. Copy the full chunk `content` field from the response.

### Step 2 — Instruct the assistant

Open the 9routers-managed assistant session with this bounded prompt:

```
Implement exactly this contract in the specified files. Do not invent new endpoints,
config keys, routes, or DTO fields outside what the spec lists.
Do not edit any file not named in ### Target Files.

<retrieved_spec>
[paste chunk content here]
</retrieved_spec>
```

### Step 3 — Verify

Run in order:

```bash
rtk dotnet build rag-gateway-mini.sln --configuration Release --warnaserror
```

Then run the relevant API smoke from `docs/testing/TEST_STRATEGY.md` for the touched endpoint:

- `/rag/search` touched → run Local API smoke + VM B1 production smoke for search.
- `/rag/answer` touched → run Local API smoke + VM B1 production smoke for answer.

### Step 4 — Record

Fill the report template below and save to `.claude/reports/p32-smoke-YYYY-MM-DD.json`.

---

## Task 3 — Automated Harness Requirements

**Scope:** add a repeatable script that automates Steps 1 and 3 of the manual workflow and produces a machine-readable report in the same style as `scripts/eval-retrieval-quality.py`.

**Requirements:**
- Retrieve the spec via `/rag/search` HTTP (no MCP dependency).
- Validate `status == found` and `chunk_type == implementation-spec` before proceeding.
- Run `dotnet build` and capture exit code and stderr.
- Optionally run the API smoke via `curl` and record HTTP status.
- Output a timestamped JSON report to `.claude/reports/p32-smoke-<timestamp>.json` with the schema below.
- Reuse the report field conventions from `scripts/eval-retrieval-quality.py` (timestamp, version, collection, per-query list).
- Do not duplicate retrieval scoring — this harness measures implementation correctness only.

**Script location:** `scripts/smoke-p32-implementation-correctness.py`

---

## Pass Criteria

All of the following must be true:

- [ ] The AI assistant edited only files named in `### Target Files` of the retrieved chunk.
- [ ] Produced method and DTO names match `### Interfaces` exactly.
- [ ] No new config keys, routes, or payload fields appear outside `### Dependencies` and `### Contract`.
- [ ] `rtk dotnet build rag-gateway-mini.sln --configuration Release --warnaserror` exits 0.
- [ ] Relevant API smoke from `docs/testing/TEST_STRATEGY.md` returns correct HTTP status and response shape.

## Fail Criteria

Any of the following cause a `fail` outcome:

- The assistant invented extra files, routes, config keys, or DTO fields.
- Generated code violates an Anti-Pattern named by the chunk.
- Build exits non-zero or emits warnings.
- Endpoint contract differs from `### Contract` or smoke returns the wrong status.

A `partial` outcome applies when the build passes but one API smoke or contract check fails.

---

## Report Template

Save as `.claude/reports/p32-smoke-YYYY-MM-DD.json`:

```json
{
  "date": "YYYY-MM-DD",
  "session": "describe session (terminal 2 / manual operator)",
  "retrieval": {
    "query": "exact query used",
    "chunk_topic": "topic from retrieved chunk",
    "chunk_id": "point id if available",
    "gateway_status": "found | not_found",
    "gateway_url": "http://192.168.18.199:5200/rag/search"
  },
  "implementation": {
    "assistant": "copilot | claude | other",
    "routing": "9routers",
    "instruction": "bounded instruction text used",
    "target_files_in_spec": ["list from chunk ### Target Files"],
    "files_actually_changed": ["list from git diff --name-only"]
  },
  "verification": {
    "build_exit_code": 0,
    "build_warnings": 0,
    "api_smoke_endpoint": "/rag/search | /rag/answer",
    "api_smoke_http_status": 200,
    "api_smoke_response_status": "found | not_found"
  },
  "conformance": {
    "only_target_files_changed": true,
    "interface_names_match": true,
    "no_invented_fields": true,
    "no_antipattern_violations": true
  },
  "outcome": "pass | partial | fail",
  "failure_reason": "first compile or smoke error, or null"
}
```

---

## Parallelization Contract

Tasks 2 and 3 may run in parallel **only after this spec is committed and pushed to `main`**.

Each task must use its own git worktree and branch:

```bash
# Task 2 worktree
git worktree add .worktrees/smoke-run -b feat/p32-smoke-run

# Task 3 worktree
git worktree add .worktrees/smoke-harness -b feat/p32-smoke-harness
```

Task 3 must not block on Task 2's outcome. If the harness produces a report, Task 2 may use it as evidence, but the manual run is the primary smoke record for this iteration.

---

## Verification of This Spec

- Links to `docs/planning/RAG_V2_ROADMAP.md:236-246` for canonical pass/fail criteria.
- References `docs/testing/TEST_STRATEGY.md` for existing API smoke commands.
- Report schema reuses field conventions from `scripts/eval-retrieval-quality.py`.
- Does not assert the smoke has been run — this is a design document only.
