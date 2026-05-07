# Test Strategy

Use this document to define what must be verified before marking work done.

Task-specific evidence belongs in the owning `## Canonical Task Tracker`.

---

## Test Layers

| Layer | Purpose | Typical command or evidence | Required before DONE? |
|---|---|---|---:|
| Static checks | Catch compile, lint, formatting, and schema issues | Project-specific command | Yes when code changes |
| Unit tests | Verify isolated behavior | Project-specific command | Yes when available |
| Integration tests | Verify external service boundaries | Docker/service smoke result | Yes for infra/API changes |
| Manual smoke test | Verify golden path behavior | Endpoint, UI, CLI, or workflow output | Yes for user-visible behavior |
| Regression check | Confirm related existing behavior still works | Focused command or scenario | Yes for risky changes |

---

## Evidence Rules

- Evidence must be observable and repeatable.
- A passing command, deployed service check, endpoint response, or linked artifact is valid evidence.
- "Looks good" is not evidence.
- If verification cannot run, mark the task `[~] IN PROGRESS` or `[!] BLOCKED` with the reason.

---

## Standard Verification Checklist

| Change type | Minimum verification |
|---|---|
| Documentation only | Link/readability check and index references |
| Configuration | Template check plus runtime location check |
| API behavior | Contract check plus smoke request |
| Pipeline/script | Dry run or focused sample input/output |
| Security control | Positive and negative verification |
| Deployment | Service status plus endpoint smoke test |

---


## Project-Specific Verification Commands

Run commands from the repository root unless a command says otherwise. Prefix shell commands with `rtk` in Claude Code sessions.

### Documentation-only changes

```bash
rtk git diff -- docs/
```

Pass criteria: diff touches only intended docs, links are repo-relative, and any changed task status is reflected in the owning canonical tracker.

### .NET build and static check

```bash
rtk dotnet build rag-gateway-mini.sln --configuration Release --warnaserror
```

Pass criteria: build exits 0 with zero warnings. There is currently no test project in this repo; add a test command here when one is introduced.

### RAG retrieval eval

```bash
set -a; source "$HOME/.config/qdrant-knowledge.env"; set +a
rtk python scripts/eval-retrieval-quality.py \
  --project homelab \
  --collection knowledge_v2_keyfacts \
  --qdrant-url http://192.168.18.199:6333 \
  --ollama-url http://192.168.18.199:11434 \
  --output .claude/reports/eval-$(date +%Y-%m-%d).json
```

Pass criteria: command exits 0, report is saved, Hit@3 stays at or above 0.85, MRR stays at or above 0.80, and NDCG@5 stays at or above 0.75. For production keyfacts checks, compare against the latest `knowledge_v2` fallback report when pipeline behavior changes.

### Local API smoke

```bash
rtk dotnet run --project src
rtk curl -s -o /tmp/rag_scalar.out -w "%{http_code}" http://localhost:5200/scalar/
rtk curl -s -o /tmp/rag_openapi.json -w "%{http_code}" http://localhost:5200/openapi/v1.json
```

Pass criteria: app starts, Scalar and OpenAPI return HTTP 200, and logs show no startup errors. There is no `/health` endpoint. Use configured local appsettings or environment variables for Qdrant and Ollama.

### VM B1 production smoke

```bash
rtk curl -s -o /tmp/rag_scalar.out -w "%{http_code}" http://192.168.18.199:5200/scalar/
rtk curl -s -o /tmp/rag_openapi.json -w "%{http_code}" http://192.168.18.199:5200/openapi/v1.json
rtk curl -s -o /tmp/rag_search_positive.json -w "%{http_code}" \
  -X POST http://192.168.18.199:5200/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query":"What port does rag-gateway-mini listen on?","project":"homelab","knowledge_expansion":true}'
rtk curl -s -o /tmp/rag_answer_positive.json -w "%{http_code}" \
  -X POST http://192.168.18.199:5200/rag/answer \
  -H "Content-Type: application/json" \
  -d '{"query":"how to push knowledge chunk to Qdrant","project":"homelab","knowledge_expansion":true,"citation_verify":true}'
rtk curl -s -o /tmp/rag_answer_negative.json -w "%{http_code}" \
  -X POST http://192.168.18.199:5200/rag/answer \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the project-alpha Blazor login flow?","project":"homelab","knowledge_expansion":true,"citation_verify":true}'
```

Pass criteria: Scalar and OpenAPI return HTTP 200; `/rag/search` returns HTTP 200 with `status=found` for positive homelab queries; positive `/rag/answer` returns HTTP 200 with `status=found`, populated `sources`, and citation verifier output when `citation_verify=true`; negative `/rag/answer` returns HTTP 200 with `status=not_found` and `message="NOT FOUND IN RAG"`.

### VM B1 redeploy verification

```bash
rtk git push origin main
rtk ssh figulazmi@192.168.18.199 'cd /opt/homelab/ai-stack/rag-gateway-mini && ~/bin/rtk sudo git fetch origin && ~/bin/rtk sudo git reset --hard origin/main && cd src && ~/bin/rtk sudo docker compose up -d --build'
rtk curl -s -o /tmp/rag_scalar.out -w "%{http_code}" http://192.168.18.199:5200/scalar/
rtk curl -s -o /tmp/rag_openapi.json -w "%{http_code}" http://192.168.18.199:5200/openapi/v1.json
```

Pass criteria: container rebuild succeeds and endpoint smokes pass. Do not modify production secrets during redeploy. Use `~/bin/rtk` inside VM B1 SSH command bodies because non-interactive SSH may not load the user PATH. There is no `/health` endpoint; use `/scalar/`, `/openapi/v1.json`, `/rag/search`, or `/rag/answer` for liveness and behavior.

### Security and secret checks

```bash
rtk git grep -n -I -E "(QDRANT_API_KEY=|api-key: [0-9a-f]{16,}|Authorization: Bearer|BEGIN (RSA|OPENSSH|PRIVATE) KEY|ghp_[A-Za-z0-9]|github_pat_)" -- docs scripts src CLAUDE.md README.md
rtk git diff -- docs scripts src CLAUDE.md README.md
```

Pass criteria: no literal Qdrant API key, bearer token, GitHub token, or private key is introduced in tracked files. Secret examples must use placeholders such as `FILL_WITH_REAL_KEY` and may document secret locations, not secret values.

### Docs-driven DONE gate

Before marking any docs-owned task DONE:

1. Update the owning canonical tracker row with evidence.
2. Search for stale references to the task ID in indexes and related docs.
3. Update `docs/TASKS.md` only as an index, not a second source of detailed status.
4. Run the documentation-only diff check and the relevant command from this strategy.
5. Leave the task `[~] IN PROGRESS` or `[!] BLOCKED` if any required evidence could not run.

---

## Canonical Task Tracker

| Order | ID | Task | Status | Evidence | Next action |
|---:|---|---|---|---|---|
| 1 | TEST-1 | Define project-specific test commands | `[x] DONE (2026-05-07)` | `rtk dotnet build rag-gateway-mini.sln --configuration Release --warnaserror` passed with 0 errors and 0 warnings; exact documentation, .NET build, RAG eval, `/rag/search`, `/rag/answer`, VM redeploy, and secret-check commands are listed above | Keep commands current when tests or deployment topology change |

---

*Last updated: 2026-05-07 · Owner: Figur Ulul Azmi*