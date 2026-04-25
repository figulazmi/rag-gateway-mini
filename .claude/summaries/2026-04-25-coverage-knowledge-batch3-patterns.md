---
id: 2026-04-25-pattern-n8n-raw-body-expression-prefix-m-001
date: 2026-04-25
source: claude-code-cli
collection: knowledge_v2
project: homelab
chunk_type: pattern
topic: Pattern: n8n raw body expression prefix must be exactly ={{ no leading equals or spaces
tags: [homelab, vm-b1, n8n, docker, pattern, expression]
related: []
session_type: 
environment: homelab
git_branch: 
status: implemented
chunk_source: code
---

## CHUNK 1: Pattern: n8n raw body expression prefix must be exactly ={{ no leading equals or spaces
<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, n8n, docker, pattern, expression] -->

### Context
n8n workflows on VM B1 use HTTP Request nodes with raw JSON body and n8n expression syntax to call Qdrant, Ollama, and other services. The body field value must use the exact n8n expression prefix.

### Pattern
The raw body expression prefix must be exactly `={{ ... }}` -- a single equals sign immediately followed by double braces. No leading equals signs, no spaces between `=` and `{{`.

### When to Apply
Every HTTP Request node in n8n that uses a raw JSON body built from an n8n expression. Also applies to any field value that computes content dynamically using `$json`, `$input`, or `JSON.stringify(...)`.

### Anti-Pattern
DO NOT use `=={{ ... }}` (double equals) or `=  ={{ ... }}` (space before braces). n8n evaluates the extra `=` as a literal prefix string, prepending it to the computed body. The resulting non-JSON prefix causes downstream services to return cryptic parse errors (Qdrant returns "Not existing vector name: ''" instead of a JSON parse error).

### Key Facts
- n8n expression prefix: exactly `={{ value }}` -- single `=` then `{{`
- Double equals `=={{ }}` causes n8n to prepend literal `=` to the body string
- The resulting body is not valid JSON -- downstream errors are misleading, not a JSON parse error
- Qdrant error "Not existing vector name: ''" can indicate a malformed request body, not an actual empty vector name
- Always test n8n nodes with a fixed string body first, then switch to expression after confirming the static payload works

## CHUNK 2: Pattern: Qdrant named vector collection requires using field in every prefetch leg
<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, qdrant, hybrid-search, pattern, dotnet] -->

### Context
Qdrant collection knowledge_v2 uses named vectors: "dense" (float32, cosine, 768-dim) and "sparse" (uint modifier IDF). The RAG Gateway queries via POST /collections/knowledge_v2/points/query using prefetch legs with RRF fusion.

### Pattern
Every prefetch leg in a named-vector Qdrant query MUST include the `using` field specifying which vector to use. The outer query (fusion) does not need `using`, but each prefetch entry does.

### When to Apply
Any time you query a Qdrant collection that uses named vectors (as opposed to a single unnamed vector). This applies to both dense prefetch (using: "dense") and sparse prefetch (using: "sparse").

### Anti-Pattern
DO NOT omit the `using` field from a prefetch leg. Without it, Qdrant returns HTTP 400 with an error about an empty or missing vector name. This is a silent misconfiguration -- the collection exists and responds, but every query fails at runtime.

### Key Facts
- Named vector query requires: `{ "prefetch": [{ "query": vector, "using": "dense", "limit": N }], "query": { "fusion": "rrf" }, "limit": M }`
- Omitting `using` in prefetch causes HTTP 400 "Not existing vector name: ''"
- The sparse prefetch uses document syntax: `{ "query": { "text": "...", "model": "Qdrant/bm25" }, "using": "sparse" }`
- ScoreThreshold for RRF results should be 0.35, not 0.55 -- RRF scores are reciprocal-rank normalized, not cosine
- Config key in appsettings.json: DenseVectorName = "dense", SparseVectorName = "sparse"

## CHUNK 3: Pattern: never hardcode secrets in tracked files use env var with fail-fast guard
<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, security, secrets, pattern, bash, python] -->

### Context
The homelab monorepo is a PUBLIC GitHub repository. Scripts in the repo (bash, Python, Node.js) need API keys for Qdrant, n8n, and other services. Secrets must not appear in any git-tracked file.

### Pattern
Read secrets exclusively from environment variables. Use a fail-fast guard so scripts abort immediately when the variable is unset -- never continue with a null/undefined/empty value that could silently cause wrong behavior.

### When to Apply
Every script, config file, or application that needs an API key, password, or token and runs from a tracked repo. Applies to bash, Python, and Node.js scripts equally.

### Anti-Pattern
DO NOT hardcode secret values as string literals in any tracked file. Even a single commit with a literal key leaks it permanently into git history -- the file deletion does not help. Always check: the key is still in history until filter-repo plus force-push is run.

### Key Facts
- Bash fail-fast: `KEY="${KEY:?KEY not set -- source ~/.config/qdrant-knowledge.env}"` under `set -euo pipefail`
- Python fail-fast: `KEY = os.environ.get("KEY"); if not KEY: raise SystemExit("KEY not set")`
- Node.js fail-fast: `const KEY = process.env.KEY; if (!KEY) { console.error("KEY not set"); process.exit(1); }`
- Source secrets once per shell session: `source ~/.config/qdrant-knowledge.env` (chmod 600, outside repo)
- Git history scrub requires: rotate key + git filter-repo --replace-text + force push origin -- source scrub alone is insufficient
- Claude Code settings.local.json is git-tracked -- do not put literal secrets in permission allowlist entries

## CHUNK 4: Pattern: n8n Code node sandbox blocks fetch and axios use HTTP Request node for outbound calls
<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, n8n, pattern, docker, workflow] -->

### Context
n8n 2.x runs workflow Code nodes inside a task runner sandbox on VM B1. The sandbox restricts which Node.js APIs and npm modules are available inside Code node scripts.

### Pattern
Use the HTTP Request node (not a Code node) for any outbound HTTP call from an n8n workflow. The HTTP Request node runs outside the sandbox with full networking access and supports raw body, custom headers, and response mapping.

### When to Apply
Any n8n workflow that needs to call an external service: Qdrant upsert, Ollama embed, n8n webhook, or any REST API. If the logic can be expressed as a configured HTTP Request node, do not use a Code node.

### Anti-Pattern
DO NOT use `fetch(...)`, `$http.get(...)`, `require('axios')`, or `require('node-fetch')` inside a Code node. All of these are blocked by the n8n task runner sandbox and throw runtime errors. The error message may not clearly indicate the sandbox as the cause.

### Key Facts
- n8n Code node sandbox blocks: fetch, $http, axios, require('axios'), require('node-fetch')
- HTTP Request node: supports raw JSON body, custom headers, any HTTP method -- use it for all outbound calls
- n8n expression in HTTP Request body field: `={{ JSON.stringify({ points: [...] }) }}` with Content-Type: application/json
- Code nodes are still useful for data transformation, string manipulation, and business logic that does not require network calls
- Verify blocked modules: error will appear in n8n execution log, not in the browser console

## CHUNK 5: Pattern: always git pull on VM before docker compose up build compose file on disk drives the build
<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, docker, pattern, git, deployment] -->

### Context
rag-gateway-mini and other homelab services deploy via git push on laptop + git pull + docker compose up --build on VM B1. The docker-compose.yml in the checked-out repo on VM B1 is the build definition used by docker compose.

### Pattern
Always run `git pull origin main` on VM B1 before `docker compose up -d --build`. The compose file already checked out on VM B1 (not the one on your laptop) is what docker compose reads. If you push changes and build without pulling, the old compose file drives the build even though the image source code is updated.

### When to Apply
Every time you change docker-compose.yml, Dockerfile, or any file referenced by a volume mount path in compose. Even if only code files changed, pulling first is a safe habit that avoids subtle compose-vs-code mismatches.

### Anti-Pattern
DO NOT run `docker compose up -d --build` on VM B1 immediately after `git push` on your laptop without first SSH-ing in and doing `git pull`. The build uses whichever files are on disk at build time -- not what you just pushed.

### Key Facts
- Correct deploy sequence: `git push origin main` (laptop) then `git pull origin main` + `docker compose up -d --build` (VM B1)
- Volume mount paths in docker-compose.yml must also match the actual file system layout on VM B1 after the pull
- `docker compose up -d --build` handles both initial build and incremental rebuild -- no separate build step needed
- After compose file change: `docker compose down` then `docker compose up -d --build` to recreate containers with updated config
- Verify: `docker ps | grep rag-gateway` should show the updated image creation time

## CHUNK 6: Pattern: Qdrant error Not existing vector name empty string indicates malformed request body not missing vector
<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, qdrant, pattern, debugging, hybrid-search] -->

### Context
Qdrant knowledge_v2 uses named vectors (dense + sparse). HTTP clients posting to /collections/knowledge_v2/points/query or /points (upsert) may receive HTTP 400 with error messages about vector names.

### Pattern
When Qdrant returns HTTP 400 "Not existing vector name: ''" (empty string), the root cause is almost always a malformed or non-JSON request body -- not an actual empty vector name in the payload. Fix: inspect the raw body being sent, not the vector name fields.

### When to Apply
Any time a Qdrant request returns a vector name error and you have verified that the vector names in your payload look correct. Specifically applies when n8n HTTP Request nodes or bash curl scripts send dynamically constructed bodies.

### Anti-Pattern
DO NOT spend time debugging vector name configuration in Qdrant or changing collection settings when you see the empty-string vector name error. The collection is not the problem -- the client is sending a body that is not valid JSON, causing Qdrant to fail before it can parse vector names.

### Key Facts
- Qdrant "Not existing vector name: ''" = malformed body (not valid JSON or has leading non-JSON prefix)
- Common cause: n8n body field with double-equals prefix `=={{ }}` prepends literal `=` to the body
- Common cause: bash heredoc with unescaped special characters producing invalid JSON
- Debug approach: log the raw request body before sending and validate it with `python3 -m json.tool`
- If Content-Type header is missing or wrong, Qdrant may also return this error with a slightly different message

## CHUNK 7: Pattern: ASP.NET Core health endpoint requires explicit MapHealthChecks call in Program.cs not auto registered
<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, dotnet, aspnetcore, pattern, rag-gateway] -->

### Context
rag-gateway-mini is an ASP.NET Core 9 API on VM B1. Deployment documentation references `GET /health` as the liveness probe. Other ASP.NET Core services in the homelab stack may also document health endpoints.

### Pattern
A `/health` endpoint in ASP.NET Core is NOT automatically created by the framework. It requires two explicit calls in Program.cs: `builder.Services.AddHealthChecks()` to register the service, and `app.MapHealthChecks("/health")` to expose the endpoint. Without both calls, any GET /health request returns 404.

### When to Apply
Whenever documenting or implementing a health check endpoint for any ASP.NET Core service. Also applies when verifying that a deployed service is healthy -- always confirm MapHealthChecks is in Program.cs before trusting curl /health output.

### Anti-Pattern
DO NOT assume that creating a controller named HealthController is the same as ASP.NET Core health checks. Do not reference /health in CLAUDE.md, docker-compose healthcheck, or monitoring configs until MapHealthChecks is confirmed in Program.cs.

### Key Facts
- Required in Program.cs: `builder.Services.AddHealthChecks();` (registration) + `app.MapHealthChecks("/health");` (routing)
- Optional: `app.MapHealthChecks("/health/ready", new HealthCheckOptions { ... })` for readiness vs liveness split
- Default response: 200 with body "Healthy" -- can be customized with HealthCheckOptions.ResponseWriter
- Alternative liveness probe until /health is implemented: `GET /scalar/` or `GET /openapi/v1.json`
- Docs drift risk: CLAUDE.md or README referencing /health before MapHealthChecks is added will cause operator confusion

## CHUNK 8: Pattern: keep production secrets outside repo in dedicated path and volume mount read-only into container
<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, docker, dotnet, pattern, security, secrets] -->

### Context
rag-gateway-mini is a public GitHub repo. It contains docker-compose.yml with volume mounts and appsettings.Production.json.template. The actual production secrets (QdrantApiKey, connection strings) must never be committed.

### Pattern
Store production secret files (appsettings.Production.json, .env) at a fixed path OUTSIDE the repo clone on VM B1. Mount them read-only into the container via docker-compose.yml volumes. The template file (with placeholder values) is committed; the actual file is created manually on the server during first deploy and never touched by git.

### When to Apply
Every ASP.NET Core service, Python app, or any containerized service that needs runtime credentials. The pattern applies even if the repo is private -- secrets should never be in source control.

### Anti-Pattern
DO NOT store production secrets inside the repo directory, even in a gitignored file -- gitignore only prevents accidental commits, not mistakes. Do not bake secrets into the Docker image via build args or ENV instructions -- they appear in `docker history` and image layers.

### Key Facts
- Secrets path on VM B1: `/opt/rag-gateway/appsettings.Production.json` (outside repo at `/opt/homelab/ai-stack/rag-gateway-mini/`)
- Volume mount in docker-compose.yml: `- /opt/rag-gateway/appsettings.Production.json:/app/appsettings.Production.json:ro`
- The `:ro` flag prevents the container from writing back to the secrets file
- Template committed at `src/appsettings.Production.json.template` with `<YOUR_VALUE>` placeholders
- First deploy: `cp template /opt/rag-gateway/appsettings.Production.json && nano` to fill values
- Never run `docker compose up --build` before creating the secrets file -- container starts with missing config

## CHUNK 9: Pattern: always backup n8n data volume before major version upgrade workflow export alone is insufficient
<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, n8n, docker, pattern, backup, disaster-recovery] -->

### Context
n8n on VM B1 runs in Docker with a named volume `n8n_data` storing all workflows, credentials, and execution history. Major version upgrades (e.g., 1.44.1 to 2.15.0) can change the data schema, and Community Edition lacks built-in version rollback.

### Pattern
Before any n8n major version upgrade, backup the full `n8n_data` Docker volume as a tar.gz archive. Workflow JSON export alone is insufficient -- it does not capture credentials, execution history, or node connection state. A volume backup is the only reliable restore point.

### When to Apply
Before every n8n image version change in docker-compose.yml that changes the major or minor version number. Also before any Compose config change that recreates the n8n container (`docker compose down`).

### Anti-Pattern
DO NOT rely on "Export all workflows" from the n8n UI as a complete backup strategy. Exported workflow JSON does not include credentials (which are encrypted per-instance). If the n8n container is recreated with a new version, credentials are lost and workflows that depend on them fail silently.

### Key Facts
- Backup command: `docker run --rm -v n8n_data:/source -v /home/figulazmi/backups:/backup alpine tar czf /backup/n8n_data_backup_$(date +%Y%m%d).tar.gz -C /source .`
- Restore command: stop n8n, run `docker run --rm -v n8n_data:/target -v /home/figulazmi/backups:/backup alpine tar xzf /backup/n8n_data_backup_YYYYMMDD.tar.gz -C /target`, then start n8n
- Backup before upgrade -- n8n 1.44 to 2.x migration is one-way; downgrade requires restore from backup
- n8n 1.44.1 had a webhook URL bug (UUID in path) -- upgrade to 2.x was mandatory, not optional
- After upgrade verify all workflows are present and credentials are intact before deleting the backup

---

## SESSION METADATA

- **Total chunks**: 9
- **Qdrant collection**: knowledge_v2
- **Generated by**: rag_capture.py v2 -- Incremental Capture
- **Author**: Figur Ulul Azmi
- **Date**: 2026-04-25
- **Unresolved items**: (fill manually if needed)