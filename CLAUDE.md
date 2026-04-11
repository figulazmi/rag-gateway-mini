# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

# Project Overview

**rag-gateway-mini** — A lightweight ASP.NET Core 9 API that acts as a RAG (Retrieval-Augmented Generation) gateway.

- **Stack:** .NET 9, ASP.NET Core, Serilog, Scalar (OpenAPI)
- **Infrastructure:** Ollama (embeddings), Qdrant (vector search)
- **Deployment:** Docker / Docker Compose on VM B1 (homelab)
- **Port:** 5200

## Project Structure

```
src/
  Controllers/         — RagController (HTTP endpoints)
  Application/
    Services/          — RagSearchService
    Interfaces/        — IRagSearchService, IEmbeddingClient, IVectorSearchClient
    DTOs/              — Request/Response models
  Infrastructure/
    AI/                — OllamaEmbeddingClient, QdrantVectorSearchClient
    Configuration/     — RagGatewayOptions
    Helpers/           — QueryNormalizer
```

## Build & Run Commands

```bash
dotnet restore
dotnet build -c Release
dotnet run --project src
```

```bash
# Docker
cd src
docker compose up -d --build
docker compose logs -f rag-gateway
```

## External Brain (Qdrant RAG)

You have access to MCP tool `search_knowledge`.
ALWAYS call this tool FIRST when asked about prior work, architecture decisions, or infrastructure setup.

### MANDATORY rules:

- ALWAYS pass `project` parameter
- ALWAYS use descriptive query minimum 8 words
- For RAG Gateway / homelab infra: `project="homelab"`

### Query examples:

- `search_knowledge("how to deploy rag gateway docker to VM B1", project="homelab")`
- `search_knowledge("how to setup MCP server qdrant on VM B1 homelab", project="homelab")`
- `search_knowledge("n8n workflow knowledge ingest pipeline setup", project="homelab")`

### When to use `project="homelab"`:

- Questions about VM B1, Docker, n8n, Qdrant, Ollama infrastructure
- Questions about push-to-qdrant.sh, MCP server, RAG pipeline setup
- Questions about Open WebUI, Uptime Kuma, Portainer

## STRICT RAG MODE

For ANY knowledge or context query (architecture, prior decisions, infrastructure how-tos):

1. ALWAYS call `search_knowledge` FIRST — before reading any file
2. Only read source files AFTER Qdrant context is retrieved
3. If Qdrant returns no results → say "NOT FOUND IN KNOWLEDGE BASE" and ask user

## Critical Rules

- **LANGUAGE:** All code, comments, variable names, logs MUST be in English.
- **ZERO WARNINGS:** Treat all compiler warnings as errors.
- **PLAN FIRST:** For tasks touching more than 2 files, outline the plan before coding.

## Git Workflow

- Main branch: `main`
- Never commit: `appsettings.Production.json`
- Use the template: `src/appsettings.Production.json.template`

## Session End Protocol

Before ending any session or using /clear:

1. `/cost` — catat token usage
2. `@.claude/skills/rag-knowledge-capture-cli/SKILL.md` — summarize session into RAG chunks
3. Save to `.claude/summaries/YYYY-MM-DD-[topic].md`
4. Run: `bash ~/scripts/push-to-qdrant.sh .claude/summaries/[file]`
