---
id: 2026-04-11-rag-gateway-docker-deploy-vm-b1
date: 2026-04-11
source: claude-code-cli
project: homelab
topic: RAG Gateway Mini Docker Deployment to VM B1 - Build Fixes and Deploy Workflow
tags: [docker, dotnet, rag-gateway, homelab, vm-b1, docker-compose, fixed, implemented]
related: [qdrant-mcp-server, ollama-embeddings, rag-pipeline]
session_type: setup
environment: homelab
git_branch: main
status: implemented
chunk_source: code
---

## CHUNK 1: Docker Build Fails Because Directory.Packages.props Outside Build Context

### Context

rag-gateway-mini is a .NET 9 ASP.NET Core RAG gateway deployed via Docker Compose on VM B1 (192.168.18.169). The repo structure places `Directory.Packages.props` (Central Package Management) at the repo root, while `Dockerfile` and `docker-compose.yml` live inside `src/`.

### Problem

`docker compose up --build` failed because `docker-compose.yml` set `context: .` (resolving to `src/`), but `Dockerfile` line 8 contained `COPY ["Directory.Packages.props", "."]`. The file is at the repo root — outside the build context — so Docker could not find it and the build failed.

### Solution

Changed `docker-compose.yml` build context from `context: .` to `context: ..` (repo root), and updated `dockerfile` path to `src/Dockerfile`. Then updated `Dockerfile` COPY paths to use `src/` prefix for all source files:

```yaml
# src/docker-compose.yml
build:
  context: ..
  dockerfile: src/Dockerfile
```

```dockerfile
# src/Dockerfile — build stage
COPY ["src/RagGateway.csproj", "src/"]
COPY ["Directory.Packages.props", "."]
RUN dotnet restore "src/RagGateway.csproj"
COPY src/ src/
RUN dotnet publish "src/RagGateway.csproj" -c Release -o /app/publish --no-restore
```

### Key Facts

- `Directory.Packages.props` for Central Package Management must be within the Docker build context to be COPY-able
- When Dockerfile and docker-compose.yml are inside a subdirectory (`src/`), set `context: ..` in docker-compose to use repo root as build context
- After changing context, all COPY paths for source files must be prefixed with `src/`
- This pattern is required any time a .NET solution-level file (Directory.Packages.props, Directory.Build.props) is above the Dockerfile's directory

---

## CHUNK 2: Docker Build Fails with "pull access denied for publish"

### Context

Same rag-gateway-mini Docker build, after fixing the build context issue in Chunk 1. The multi-stage Dockerfile has a `build` stage but the final stage referenced `--from=publish`.

### Problem

Build failed with: `failed to resolve source metadata for docker.io/library/publish:latest: pull access denied`. Docker interpreted `--from=publish` as a public image name rather than a local build stage, because no stage named `publish` existed in the Dockerfile.

### Solution

Corrected the final stage COPY instruction from `--from=publish` to `--from=build` to match the actual stage name:

```dockerfile
# Wrong
COPY --from=publish /app/publish .

# Fixed
COPY --from=build /app/publish .
```

### Key Facts

- Docker `COPY --from=X` references a named stage in the same Dockerfile — if the name does not match any `AS` alias, Docker tries to pull `X` as a public image
- Stage name in this Dockerfile is `build` (declared as `FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build`)
- The dotnet publish output directory `/app/publish` is set via `-o /app/publish` in the `dotnet publish` command — must match exactly
- Error message "pull access denied for publish:latest" is the symptom of a mismatched `--from` stage name

---

## CHUNK 3: Docker Compose v2 on Linux VM - No docker-compose Binary

### Context

VM B1 runs a recent Docker Engine version. After pulling the fixed code and trying to run deployment, the command `docker-compose` was not found on the system.

### Problem

`docker-compose: command not found`. VM B1 has Docker Engine with Compose v2 installed as a plugin, not the legacy standalone `docker-compose` v1 binary.

### Solution

Use `docker compose` (space-separated, as a Docker subcommand) instead of `docker-compose`:

```bash
docker compose up -d --build
docker compose logs -f rag-gateway
docker compose restart
```

### Key Facts

- Docker Compose v2 is a plugin built into Docker CLI — invoked as `docker compose` (space, no hyphen)
- Docker Compose v1 (`docker-compose`) is a separate Python binary, deprecated and not installed by default on modern systems
- VM B1 has Docker Compose v5.1.1 (plugin)
- Optional alias for convenience: `echo 'alias docker-compose="docker compose"' >> ~/.bashrc`

---

## CHUNK 4: VM B1 Deployment Workflow for rag-gateway-mini

### Context

rag-gateway-mini is deployed on homelab VM B1 at 192.168.18.169 port 5200. The repo was cloned to `/opt/homelab/ai-stack/rag-gateway-mini`. Production secrets (QdrantApiKey) are kept outside the repo at `/opt/rag-gateway/appsettings.Production.json`, mounted read-only into the container via docker-compose volume.

### Problem

Need a repeatable, documented workflow for initial deploy and future redeployments after code changes.

### Solution

**Initial deploy (one-time):**
```bash
git clone https://github.com/figulazmi/rag-gateway-mini.git /opt/homelab/ai-stack/rag-gateway-mini
mkdir -p /opt/rag-gateway
cp /opt/homelab/ai-stack/rag-gateway-mini/src/appsettings.Production.json.template \
   /opt/rag-gateway/appsettings.Production.json
nano /opt/rag-gateway/appsettings.Production.json  # fill QdrantApiKey
cd /opt/homelab/ai-stack/rag-gateway-mini/src
docker compose up -d --build
```

**Update / redeploy after code changes:**
```bash
# Laptop
git push origin main

# VM B1
cd /opt/homelab/ai-stack/rag-gateway-mini
git pull origin main
cd src
docker compose up -d --build
```

**Verify:**
```bash
docker ps | grep rag-gateway
curl http://localhost:5200/health
# Scalar UI: http://192.168.18.169:5200/scalar/
```

### Key Facts

- App deployed and live at `http://192.168.18.169:5200/scalar/`
- Clone path on VM: `/opt/homelab/ai-stack/rag-gateway-mini` (not `/opt/rag-gateway-mini`)
- Secrets file path: `/opt/rag-gateway/appsettings.Production.json` — outside repo, never committed
- Template already has correct IPs for Qdrant (6333), Ollama (11434), Seq (5341) — only QdrantApiKey needs filling
- `docker compose up -d --build` handles both first-time build and incremental rebuilds
- Deployment notes documented in `CLAUDE.md` in the repo for future reference

---

## SESSION METADATA

- **Total chunks**: 4
- **Qdrant collection**: knowledge
- **Primary project**: homelab
- **Stack involved**: .NET 9, Docker, Docker Compose v2, ASP.NET Core, Qdrant, Ollama
- **Files modified**: src/Dockerfile, src/docker-compose.yml, CLAUDE.md
- **Git branch**: main
- **Unresolved items**: none
- **Author**: Figur Ulul Azmi
- **Generated by**: Claude Code CLI — RAG Knowledge Capture Skill
