---
id: 2026-04-25-pattern-n8n-blocks-env-vars-in-expressio-001
date: 2026-04-25
source: claude-code-cli
collection: knowledge_v2
project: homelab
chunk_type: pattern
topic: Pattern: n8n blocks env vars in expressions by default requires explicit flag
tags: [homelab, vm-b1, n8n, docker, pattern, configuration]
related: []
session_type: 
environment: homelab
git_branch: 
status: implemented
chunk_source: code
---

<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, n8n, docker, pattern, configuration] -->
## CHUNK 1: Pattern: n8n blocks env vars in expressions by default requires explicit flag

### Context
n8n workflow engine on VM B1 Docker. Any workflow that reads environment variables inside node expressions using $env.* syntax.

### Pattern
Always add N8N_BLOCK_ENV_ACCESS_IN_NODE=false to the n8n service environment block in docker-compose.yml. Without this flag, $env.* resolves to empty string silently -- no error, just wrong behavior.

### When to Apply
Every time a new n8n service is deployed or an existing one cannot read env vars in expressions. Affects all HTTP Request nodes that use $env.QDRANT_API_KEY, $env.OLLAMA_URL, or any other env-based credentials.

### Anti-Pattern
DO NOT assume that docker exec n8n printenv VAR_NAME proving the variable exists inside the container means expressions can read it. Container env and expression engine env are isolated in n8n v1.x by default. A correct printenv result combined with empty expression output is the signature of this bug.

### Key Facts
- n8n default: N8N_BLOCK_ENV_ACCESS_IN_NODE is implicitly true -- blocks $env.* in all node expressions
- Fix: add N8N_BLOCK_ENV_ACCESS_IN_NODE=false to n8n environment block, then docker compose up -d n8n
- Qdrant 401 with empty api-key header is indistinguishable from a wrong key -- always verify via printenv first
- docker exec n8n printenv confirms container env; it does NOT confirm expression engine can read it
- Commit workflow JSON with $env.VARIABLE_NAME expressions instead of hardcoded values so secrets never enter git

<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, docker, networking, pattern, n8n, ollama, qdrant] -->
## CHUNK 2: Pattern: inside Docker network always use service hostname not localhost

### Context
Services running inside Docker Compose network on VM B1: n8n, Ollama, Qdrant, rag-gateway. Each service that makes HTTP calls to another service in the same compose network.

### Pattern
Always use the Docker service name as the hostname when one container calls another. Use docker-compose.yml service keys (ollama, qdrant, n8n) -- never 127.0.0.1 or localhost -- for inter-container communication.

### When to Apply
Every time a container needs to call another container in the same docker network: n8n calling Ollama for embeddings, n8n calling Qdrant for upserts, rag-gateway calling Ollama or Qdrant.

### Anti-Pattern
DO NOT use localhost or 127.0.0.1 for inter-container calls. Inside a Docker container, localhost refers to the container itself -- not the host or other containers. Using localhost causes connection refused that can be confused with a service-down error.

### Key Facts
- Docker service hostnames: ollama (port 11434), qdrant (port 6333), n8n (port 5678)
- External access (from laptop or SSH): use 192.168.18.199 or Tailscale 100.120.249.99
- Snap Ollama on host binds to 127.0.0.1:11434 -- blocks Docker Ollama from the same port; disable snap Ollama
- Verify inter-container routing: docker exec n8n wget -qO- http://qdrant:6333/collections
- All containers must be on the same docker network (rag-net) for hostname resolution to work

<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, docker, pattern, docker-compose] -->
## CHUNK 3: Pattern: Docker Compose v2 uses space separator not hyphen

### Context
Any Linux VM with modern Docker Engine (Docker Desktop or package manager install). VM B1 runs Docker Engine with Compose plugin v2.

### Pattern
Use docker compose (space, as a Docker subcommand) not docker-compose (hyphen, legacy binary). The v1 binary is a separate Python package that is deprecated and not installed on modern Docker setups.

### When to Apply
Every Bash command, runbook, Makefile target, or CI script that manages containers on VM B1. Also applies when writing CLAUDE.md or docs that include Docker commands.

### Anti-Pattern
DO NOT write docker-compose up or docker-compose down in scripts or docs. The hyphenated form will fail with command not found on VM B1 and any system using Docker Engine 23+.

### Key Facts
- VM B1 has Docker Compose plugin v5.1.1 installed as part of Docker Engine
- Correct form: docker compose up -d --build, docker compose logs -f, docker compose restart
- Alias if needed: echo 'alias docker-compose="docker compose"' >> ~/.bashrc
- Docker Compose v1 (docker-compose) was deprecated in July 2023 and removed from Docker Desktop in 2024
- docker compose --version prints the plugin version; docker-compose --version prints nothing or error

<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, docker, pattern, deployment] -->
## CHUNK 4: Pattern: docker cp changes are ephemeral and lost on container recreate

### Context
VM B1 homelab. Any deployment that uses docker cp to push files into a running container instead of rebuilding the image.

### Pattern
Treat docker cp as a temporary hotfix only -- never as a permanent deployment method. Changes made via docker cp exist only in the writable layer of the running container and are lost the moment the container is recreated (docker compose up, docker restart with --force-recreate, or image update).

### When to Apply
When Gitea CI is down and a quick frontend fix is needed. When testing a config change without a full rebuild cycle. Always document that the change is temporary and schedule a proper rebuild.

### Anti-Pattern
DO NOT use docker cp as the standard deploy mechanism for frontend builds or config files. If the container is ever recreated (which happens on every docker compose up --build), all docker cp changes are silently discarded.

### Key Facts
- docker cp + nginx -s reload is safe for nginx frontend-only hotfixes (no rebuild needed)
- Scope: only works while container is running and has not been recreated
- VM B1 constraint: no internet access means cannot pull new base images directly; local build + scp + docker cp is the offline workflow
- Permanent fix always requires: docker build (or compose up --build) with correct source files
- figulazmi has docker group access but no passwordless sudo -- docker cp works without sudo

<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, qdrant, pattern, migration, sparse-vector, hybrid-search] -->
## CHUNK 5: Pattern: Qdrant cannot add sparse vector config to existing collection requires recreation

### Context
Qdrant vector database on VM B1. Any scenario where hybrid search (dense + sparse BM25) needs to be added to an existing dense-only collection.

### Pattern
When adding sparse vector support to an existing Qdrant collection: create a new collection with both vector configs from the start, migrate all points from old to new, then switch the gateway config. Qdrant does not support ALTER COLLECTION -- schema is immutable after creation.

### When to Apply
- Adding BM25 sparse vectors to a dense-only collection
- Renaming vectors from unnamed to named format
- Changing vector distance metric or size

### Anti-Pattern
DO NOT attempt to patch an existing collection's sparse_vectors_config via the REST API. Qdrant will return 400. DO NOT run the migration on the same collection name (drop + recreate) without verifying the gateway is offline first -- concurrent reads during migration return inconsistent results.

### Key Facts
- Qdrant collection schema (vector configs) is immutable after creation -- cannot add, rename, or resize vectors
- Migration pattern: create knowledge_v2 -> migrate from knowledge -> update gateway config -> verify -> keep old as backup
- models.Document(text, model="Qdrant/bm25") triggers server-side sparse generation during upsert (requires qdrant-client >= 1.13.0 and Qdrant >= 1.15.2)
- Payload indexes must be created on the new collection before bulk upsert for best performance
- Reuse dense vectors from old collection (no re-embedding) to avoid embedding drift

<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, docker, pattern, configuration, appsettings, deployment] -->
## CHUNK 6: Pattern: Docker volume mount path must exactly match host filesystem path

### Context
rag-gateway-mini on VM B1. Any Docker service that mounts a host file into the container for config or secrets (appsettings.Production.json, .env files, TLS certs).

### Pattern
Always verify the host-side path in docker-compose.yml volume mount matches the actual file location on the VM filesystem before deploying. A wrong mount path causes the container to start successfully (no error) but with missing config, leading to runtime 500 errors that appear unrelated to the config issue.

### When to Apply
- After moving a secrets file to a new location on the host
- When copying a docker-compose.yml from one environment to another
- After a VM IP change or path refactor (e.g., moving from /opt/rag-gateway/ to /opt/homelab/ai-stack/rag-gateway-mini/)

### Anti-Pattern
DO NOT assume a container started successfully means its volume mounts are correct. Docker will start the container with an empty mount point if the source path does not exist -- it does not fail at startup.

### Key Facts
- Production override path (current): /opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json
- Mount in docker-compose.yml: /opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json:/app/appsettings.Production.json:ro
- Symptom of wrong path: container starts healthy but /rag/search returns 500 with null QdrantApiKey
- Verify mount: docker inspect rag-gateway | grep -A5 Mounts
- After editing docker-compose.yml on laptop: always git pull on VM before docker compose up

<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, docker, snap, pattern, ollama, networking] -->
## CHUNK 7: Pattern: Snap service and Docker service conflict on same port disable Snap first

### Context
VM B1 Ubuntu with both Snap-installed and Docker-installed versions of the same service (Ollama). Snap Ollama binds to 127.0.0.1:11434 on the host. Docker Ollama needs to bind to 0.0.0.0:11434 and join the rag-net Docker network.

### Pattern
When adding a Dockerized service that was previously installed via Snap on the same VM: disable the Snap service first, remove its container if stale, then bring up the Docker version. Never run both simultaneously.

### When to Apply
- Before deploying Docker Ollama on a VM that already has Snap Ollama
- When n8n container shows connection refused to ollama:11434 despite Ollama appearing up
- Any time `curl localhost:11434` works from the host but fails from inside a container

### Anti-Pattern
DO NOT let Snap Ollama and Docker Ollama run simultaneously. The Snap process owns 127.0.0.1:11434 on the host -- Docker cannot bind the same port, and inter-container resolution fails because Snap process is not on the Docker network.

### Key Facts
- Disable Snap Ollama permanently: sudo snap disable ollama
- Verify Docker Ollama joined rag-net: docker network inspect rag-net | grep ollama
- Test from n8n container: docker exec n8n wget -qO- http://ollama:11434/api/tags
- 4 models must be visible after reconnection: nomic-embed-text and at least 3 others
- Snap services use different update channels and can auto-restart -- always disable, not just stop

<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, deployment, pattern, docker, networking, offline] -->
## CHUNK 8: Pattern: VM B1 has no internet access build images locally then deploy via SCP

### Context
VM B1 homelab server cannot reach the public internet -- Docker Hub, GitHub, PyPI, and npm registry are all unreachable from inside the VM. All image builds and package installs must be done on a machine with internet access (Windows laptop) and transferred manually.

### Pattern
Build artifacts on the internet-connected laptop, transfer via SCP, then deploy on VM B1. For Docker images: build locally, docker save, scp .tar to VM, docker load. For frontend: npm build locally, scp dist/, docker cp into container. For Python: pip download on laptop, scp .whl files, pip install --offline on VM.

### When to Apply
- Any new Docker image that requires base image pull (FROM python:3.11, FROM node:20, etc.)
- npm install / pip install inside a Dockerfile that runs on VM B1
- Any time docker compose up --build fails with network timeout on VM B1

### Anti-Pattern
DO NOT write Dockerfile or compose files that assume internet access during build. DO NOT add new pip/npm dependencies to a Dockerfile without pre-downloading them. DO NOT try to configure a proxy -- VM B1 network policy blocks external egress.

### Key Facts
- VM B1 LAN: 192.168.18.199, Tailscale: 100.120.249.99 -- inbound SSH works, outbound internet blocked
- SCP to VM: scp file figulazmi@192.168.18.199:/tmp/
- figulazmi has docker group access -- docker load, docker cp, docker compose all work without sudo
- Gitea CI on VM B1 can deploy from local Gitea repos (not GitHub) -- use Gitea for automated deploys
- docker save + docker load workflow: docker save myimage:tag | gzip > image.tar.gz -> scp -> docker load < image.tar.gz

<!-- rag_chunk_meta chunk_type=decision tags=[homelab, vm-b1, qdrant, hybrid-search, decision, djb2, bm25, adr] -->
## CHUNK 9: Decision: client-side djb2 BM25 chosen over Qdrant server-side inference for knowledge_v2

### Context
knowledge_v2 collection requires sparse BM25 vectors at both index-time (push-to-qdrant.sh / n8n workflow) and query-time (qdrant-mcp-server.js, QdrantVectorSearchClient.cs). Two approaches were considered: client-side djb2 hash or Qdrant server-side Qdrant/bm25 model inference.

### Decision
Use client-side djb2 hash for all sparse vector generation in knowledge_v2.

### Rationale
knowledge_v2 was originally indexed using the n8n JS node's djb2 implementation. Qdrant server-side BM25 (model: Qdrant/bm25) uses a different tokenizer and produces different index positions -- switching at query-time without re-indexing would produce mismatched sparse indices and degrade retrieval to effectively zero keyword recall. Client-side djb2 was already implemented in three places (JS, Python, C#), so consistency is achievable. Re-indexing all 262+ points using server-side BM25 was rejected because it would require re-embedding (or at minimum re-uploading) all points.

### Consequences
- All clients (JS MCP server, Python rag_capture.py, C# rag-gateway) must use identical djb2 algorithm
- Algorithm must be explicitly documented: h=5381; h=((h<<5)+h+ord(ch))&0x7FFFFFFF; tokenize /[a-z0-9]+/
- New collections built from scratch may choose server-side BM25 (cleaner, no algorithm lock-in)
- Verification: inspect stored sparse.indices -- large integers (>10M) = djb2, small sequential = server BM25

### Key Facts
- Index-time tokenizer must match query-time tokenizer exactly or keyword recall collapses
- Qdrant/bm25 server-side inference would require re-indexing all existing points to switch
- rag-gateway-mini uses server-side Qdrant/bm25 inference via its own search endpoint (separate from knowledge_v2 ingest path -- no conflict)
- djb2 produces large hash integers (e.g., 19522071) identifiable in stored vector inspection

<!-- rag_chunk_meta chunk_type=decision tags=[homelab, vm-b1, docker, security, decision, appsettings, adr, secrets] -->
## CHUNK 10: Decision: production secrets as Docker volume mount not baked into image

### Context
rag-gateway-mini ASP.NET Core 9 service needs QdrantApiKey and other production-specific config values that must never enter git history. Two approaches: bake into image at build time via ARG/ENV, or mount at runtime as a file volume.

### Decision
Keep production secrets in /opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json on VM B1 host, mounted read-only (:ro) into the container at /app/appsettings.Production.json.

### Rationale
Baking secrets into the image creates a permanent, extractable copy in the image layer history (docker history --no-trunc reveals ARG values). Volume mount keeps secrets on the host filesystem only, outside the image and outside git. ASP.NET Core's configuration system natively supports appsettings.{Environment}.json overlay -- zero code change needed.

### Consequences
- After any docker compose up --build, the production file must exist on VM B1 at the exact mount path
- New VM or fresh clone requires manual creation of the production file from the .template
- Secrets never appear in CI logs, git blame, or docker image layers
- Mount path must be kept in sync between docker-compose.yml and actual file location on VM

### Key Facts
- Template: src/appsettings.Production.json.template checked into git with placeholder values
- Actual file: /opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json (outside repo, never committed)
- ASPNETCORE_ENVIRONMENT=Production set in docker-compose.yml causes ASP.NET Core to load and overlay the production file
- Build context is repo root (not src/) so Directory.Packages.props is included -- Dockerfile references ../Directory.Packages.props

<!-- rag_chunk_meta chunk_type=decision tags=[homelab, vm-b1, rag-gateway, decision, dotnet, aspnetcore, adr, architecture] -->
## CHUNK 11: Decision: ASP.NET Core chosen over FastAPI for rag-gateway because of type safety and DI ecosystem

### Context
rag-gateway-mini needed a thin HTTP gateway to bridge Claude Code (MCP) and Qdrant/Ollama on VM B1. Two main candidates: ASP.NET Core 9 (.NET) and FastAPI (Python). The developer has deep .NET expertise but is comfortable with Python for scripts.

### Decision
Use ASP.NET Core 9 for the RAG gateway service.

### Rationale
The gateway involves typed DTOs (search requests, RAG results, debug payloads), interface abstractions (IVectorSearchClient), and configuration binding (QdrantOptions, OllamaOptions). ASP.NET Core's DI container, IOptions pattern, and Serilog structured logging make this structure natural with zero boilerplate. FastAPI would be faster to prototype but looser typed -- errors in payload mapping would surface at runtime rather than compile time. The gateway is a long-lived service (not a one-off script) so the cost of stronger typing pays off over time. Scalar API docs are auto-generated from the existing controller annotations.

### Consequences
- All gateway code in C# -- Python/shell only used for scripts (rag_capture.py, push-to-qdrant.sh)
- Requires .NET 9 SDK on development machine and Docker image with .NET 9 runtime
- Zero-warning policy enforced (treat warnings as errors) for compile-time safety
- Future implementer models (qwen2.5-coder) can generate C# from implementation-spec chunks

### Key Facts
- Language boundary: C# for gateway, Python for capture/push scripts, JS for MCP server
- Port: 5200 on VM B1; Scalar UI at /scalar/; health at /health
- Config system: appsettings.json (dev) + appsettings.Production.json (prod overlay)
- DI pattern: interfaces in Application/Interfaces/, implementations in Infrastructure/

<!-- rag_chunk_meta chunk_type=feature tags=[homelab, vm-b1, n8n, qdrant, ollama, feature, knowledge-capture, workflow] -->
## CHUNK 12: Feature: n8n knowledge-ingest workflow v2 pipeline Ollama embed then Qdrant upsert

### Context
VM B1 homelab AI stack. n8n workflow that receives chunk payloads from push-to-qdrant.sh webhook, generates dense embeddings via Ollama, and upserts to Qdrant knowledge_v2 with both dense and sparse vectors.

### Architecture
Webhook trigger (POST /webhook/knowledge-ingest) -> Validate and Clean node -> Ollama embed (HTTP Request to http://ollama:11434/api/embeddings, model: nomic-embed-text) -> Build Qdrant payload (Code node constructs djb2 sparse vector + dense vector) -> Qdrant upsert (HTTP Request to http://qdrant:6333/collections/knowledge_v2/points).

### Key Implementation Choices
- HTTP Request node for both Ollama and Qdrant (NOT Code node -- n8n 2.x Code node sandbox blocks fetch/axios)
- n8n 2.x body parsing: $input.first().json.body ?? $input.first().json (handles both wrapped and raw webhook body)
- Qdrant payload wrapped in { points: [...] } with named vector dict: { dense: [...], sparse: { indices: [], values: [] } }
- API key: hardcoded directly in Qdrant node header (Variables = paid feature in Community Edition)
- Workflow JSON committed as n8n-knowledge-ingest-workflow-v2.json for disaster recovery

### Key Facts
- Workflow file: n8n-knowledge-ingest-workflow-v2.json (committed to repo for backup)
- n8n version: 2.15.0 (must be >= 2.0 for webhook URL without UUID suffix and Publish button)
- Ollama URL inside n8n: http://ollama:11434 (Docker service hostname, NOT localhost)
- Qdrant URL inside n8n: http://qdrant:6333 (Docker service hostname, NOT localhost)
- Sparse vector generated client-side via djb2 in n8n Code node -- must match rag_capture.py and QdrantVectorSearchClient.cs
- Before upgrade: always backup n8n_data volume with docker run alpine tar czf

<!-- rag_chunk_meta chunk_type=feature tags=[homelab, vm-b1, proxmox, backup, feature, disaster-recovery] -->
## CHUNK 13: Feature: Proxmox VM B1 backup and restore workflow via vzdump vma.zst

### Context
VM B1 runs on Proxmox VE as a QEMU VM (VM ID 100). The VM hosts the entire homelab AI stack. Backup and restore capability is critical for hardware migration and disaster recovery.

### Architecture
Proxmox vzdump creates a .vma.zst compressed backup of the full VM disk. Backup is stored locally on the Proxmox host or transferred to a Windows laptop via SCP. Restore uses qmrestore on the destination Proxmox host.

### Key Implementation Details
- Backup command: vzdump 100 --compress zstd --storage local (or via Proxmox UI: Backup tab)
- Backup file format: vzdump-qemu-100-YYYY_MM_DD-HH_MM_SS.vma.zst
- Restore on new host: qmrestore /path/to/vzdump-qemu-100-*.vma.zst 100 --storage local-lvm
- VM ID can be changed at restore time if 100 is already taken
- Tailscale reconnects automatically after restore -- no reconfiguration needed
- Docker containers auto-start if configured with restart: always or unless-stopped in compose files

### Verification After Restore
```bash
qm list                            # VM 100 running
curl http://<VM-IP>:5200/health   # rag-gateway responding
curl http://<VM-IP>:3010          # token-monitor dashboard
curl http://<VM-IP>:5678          # n8n webhook reachable
```

### Key Facts
- Backup location on laptop: C:/Users/Clandesitine/Backups/vzdump-qemu-100-*.vma.zst
- qmrestore storage target must exist on new host -- check with pvesm status
- Network IP inside VM stays same after restore; check for LAN conflicts on new physical host
- Always verify Docker services with docker ps after first boot post-restore
- Full restore test is the only reliable DR verification -- periodic restore drills recommended

---

## SESSION METADATA

- **Total chunks**: 13
- **Qdrant collection**: knowledge_v2
- **Generated by**: rag_capture.py v2 -- Incremental Capture
- **Author**: Figur Ulul Azmi
- **Date**: 2026-04-25
- **Unresolved items**: (fill manually if needed)