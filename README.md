# RAG Gateway Mini

A lightweight ASP.NET Core 9 API that bridges your LLM tools and a Qdrant vector database.
It embeds queries via Ollama and returns the most relevant knowledge chunks — no generation, pure deterministic retrieval.

Terminology:
- **Deterministic retrieval core**: gateway search engine that returns retrieved chunks only (no text generation).
- **Adapter outputs**: CLI/MCP output modes (`RAG_CONTEXT`, `--claude`, `--strict`, `--raw`) that package retrieval results for downstream tools.

The repo also ships a **RAG CLI pipeline**: a set of Bash scripts that let any developer on any device capture knowledge, search it, and feed it into Claude or GitHub Copilot — with zero hallucination.

---

## Architecture

```
          ┌──────────────────────────┐
          │   Qdrant (Knowledge Base)│  <- all project knowledge lives here (VM B1)
          └────────────┬─────────────┘
                       │
          ┌────────────▼─────────────┐
          │   RAG Gateway Mini API   │  <- REST bridge to Qdrant (VM B1:5200)
          └────────────┬─────────────┘
                       │
          ┌────────────▼─────────────┐
          │     ~/scripts/rag        │  <- CLI you use every day
          └──────────┬───────────────┘
                     │
           ┌─────────┴──────────┐
           │                    │
  ┌────────▼────────┐  ┌────────▼────────┐
  │  GitHub Copilot  │  │     Claude      │
  │  (light tasks)   │  │  (heavy tasks)  │
  └──────────────────┘  └─────────────────┘
```

| Component | Role |
|---|---|
| **Qdrant** | Vector store — ground truth for all project knowledge |
| **RAG Gateway** | API layer — called by `rag` CLI and MCP server |
| **rag CLI** | Your daily terminal tool for search and capture |
| **rag-tools** | Separate repo — rag CLI, push-to-qdrant.sh, MCP server, n8n workflow |
| **GitHub Copilot** | Fast code generation for small tasks |
| **Claude** | Reasoning engine for complex tasks and architecture |

---

## Quick Setup — New Device

> Clone the repo and run one command. Everything else is automated.

### Prerequisites

| Tool | Install |
|---|---|
| `curl` | pre-installed on most systems |
| `jq` | `winget install jqlang.jq` / `brew install jq` / `apt install jq` |
| `python3` | [python.org](https://python.org) (needed for `rag add` / `rag merge`) |
| SSH key | must have access to VM B1 (`figulazmi@192.168.18.199`) |

### Install

```bash
# 1. Clone rag-tools (tooling repo, separate from this project)
rtk git clone https://github.com/figulazmi/rag-tools.git ~/rag-tools
rtk bash ~/rag-tools/rag-capture-v2/rag-setup.sh
# Prompts: Qdrant URL, API key, author name, VM B1 LAN IP, Tailscale IP, SSH user
# Installs: rag CLI wrapper, ~/.rag_config.json, MCP connect script, patches ~/.claude/settings.json

# 2. Append RAG-first protocol to Claude Code global config
rtk bash -lc 'cat ~/rag-tools/rag-capture-v2/CLAUDE_snippet.md >> ~/.claude/CLAUDE.md'

# 3. Restart Claude Code to activate MCP server
```

### Update (after changes to rag-tools)

```bash
cd ~/rag-tools && rtk git pull
# Wrapper points to repo clone — git pull takes effect immediately, no reinstall needed
```

---

## Mandatory Session Start Protocol

Run this sequence at the beginning of every session:

```bash
# 1. Resume checkpoint first
rtk python "C:/Users/Clandesitine/scripts/rag-capture-v2/rag_capture.py" resume
# If the rag wrapper is installed and known-good, `rtk rag resume` is equivalent.

# 2. Load deferred schema
ToolSearch select:mcp__qdrant-knowledge__search_knowledge

# 3. Query RAG before reading source files
search_knowledge("descriptive query with project context", project="homelab")

# 4. Only then do targeted reads for files indicated by RAG
rtk read src/Infrastructure/AI/QdrantVectorSearchClient.cs
```

If step 1 returns FOUND, skip broad exploration and continue from checkpoint `next_step`.

## RAG CLI Usage

### Basic search

```bash
rag "query keywords here" -p homelab
rag "query keywords here" -p petrochina-eproc
```

### Output modes

| Command | Output | Use for |
|---|---|---|
| `rag "query" -p <project>` | `// RAG_CONTEXT:` comment block | Paste into `.cs` file → Copilot generates |
| `rag "query" --claude "task"` | Structured Claude prompt | Paste into Claude chat |
| `rag "query" --strict` | Claude prompt + zero-hallucination enforcement | Critical decisions, auth, financial logic |
| `rag "query" --raw` | Plain text | Custom processing |
| `rag "query" --debug` | Raw scores + threshold info | Diagnose low-relevance results |
| `rag "query" --copy` | Same output + copies to clipboard | Skip manual select + copy |

### Intent auto-detection

Queries containing `design`, `architecture`, `implement`, `system`, `flow`, `explain`, `how does`, `why does`, `compare`, `plan` are automatically routed to Claude mode. No flag needed.

```bash
# Auto Claude mode (contains "design"):
rag "design single device login" -p petrochina-eproc

# Copilot mode (no trigger word):
rag "SDL session kicked detection" -p petrochina-eproc
```

### Project filter (always use -p)

```bash
rag "..." -p petrochina-eproc   # .NET, Blazor, EF Core, MediatR, Hangfire
rag "..." -p homelab            # VM B1, Docker, n8n, Qdrant, Ollama, infra
```

---

## RAG_BASE_URL Auto-Detection

The `rag` CLI detects the gateway automatically — no manual URL config needed on most setups.

Detection order (first reachable wins):

```
localhost:5200          <- local dev or running directly on VM B1
192.168.18.199:5200     <- office LAN
100.120.249.99:5200     <- Tailscale VPN (remote access)
```

To override:

```bash
export RAG_BASE_URL=http://your-host:5200
# or add to ~/.config/rag-gateway.env:
# RAG_BASE_URL=http://your-host:5200
```

---

## Capture Knowledge (Write Pipeline)

After solving a problem or completing a feature, capture it to Qdrant so the team can retrieve it later. The `rag` CLI is a wrapper around `rag_capture.py`; if the wrapper is unavailable or ambiguous, call `rtk python "C:/Users/Clandesitine/scripts/rag-capture-v2/rag_capture.py" ...` with the same flags.

```bash
cat <<'EOF' | rtk rag add -p homelab -t debug --topic "topic here" --tags "homelab,docker,qdrant"
### Context
[1-2 sentences. What system, goal, constraint.]
### Problem
[Specific issue or requirement.]
### Solution
[The actual fix or decision.]
### Key Facts
- fact 1
- fact 2
- fact 3
EOF

# Merge drafts and follow the push reminder printed by the CLI:
rtk rag merge --output 2026-01-01-topic.md
```

Chunk types: `debug` | `feature` | `runbook` | `pattern` | `decision` | `reference` | `implementation-spec`. Production retrieval uses `knowledge_v2_keyfacts`; keep implementation-spec capture aligned with `docs/planning/RAG_V2_ROADMAP.md` before changing pipeline behavior.

---

## Typical Workflows

### Small task — Copilot

```bash
# 1. Get context
rag "vendor repository EF Core pattern" -p petrochina-eproc --copy

# 2. Open file in VS Code
# 3. Paste // RAG_CONTEXT: above the method
# 4. Type signature -> Copilot generates
```

### Medium task — plan in Claude, implement with Copilot

```bash
rag "email notification purchase order approval" -p petrochina-eproc \
  --claude "design the notification flow and list files to change" --copy
# Paste into Claude -> get plan -> use Copilot per file
```

### Large task — full Claude with strict mode

```bash
rag "single device login session management refresh token" -p petrochina-eproc \
  --claude "design the full SDL system" --strict --copy
# Claude cites every claim to a SOURCE, outputs NOT FOUND IN RAG for unknowns
```

---

## Claude Code MCP Setup

The MCP server `qdrant-knowledge` lets Claude query Qdrant directly — no CLI needed.

MCP setup is handled automatically by `rag-setup.sh` (cross-platform: Windows + Mac/Linux).
No manual configuration needed — the script generates the connect script and patches
`~/.claude/settings.json` for you.

Operational deep-dive manual: `docs/reference/RAG_MANUAL_BOOK.md` (session-start protocol, threshold semantics, chunk taxonomy, troubleshooting).

To set up or re-run:

```bash
rtk bash ~/rag-tools/rag-capture-v2/rag-setup.sh
# Restart Claude Code after setup
```

Verify:

```bash
claude mcp list   # should show qdrant-knowledge
```

---

## Troubleshooting

### `Error: cannot reach RAG Gateway`

The CLI tried localhost, LAN, and Tailscale — all failed.

```bash
# Check which path is reachable:
rtk curl -s --connect-timeout 3 http://192.168.18.199:5200/scalar/
rtk curl -s --connect-timeout 3 http://100.120.249.99:5200/scalar/

# Override manually:
export RAG_BASE_URL=http://192.168.18.199:5200
```

### `Error: jq is not installed`

```bash
# Windows
rtk winget install jqlang.jq

# Mac
rtk brew install jq

# Linux
rtk sudo apt install jq
```

### `rag: command not found`

```bash
rtk bash -lc 'echo $PATH | tr '"'"':'"'"' '\''\n'\'' | grep scripts'   # check if ~/scripts is in PATH
rtk bash -lc 'source ~/.bashrc'                                        # reload
```

### RAG results not relevant (low scores)

```bash
rtk rag "your query" -p homelab --debug   # shows raw scores and threshold
# Distinguish thresholds:
# - ScoreThreshold (default 0.35): per-result inclusion threshold
# - NOT_FOUND gate (topScore < 0.50): return explicit NOT FOUND IN RAG
```

---

## Gateway API Reference

The gateway runs at `http://localhost:5200` (local) or `http://192.168.18.199:5200` (VM B1).

### `POST /rag/search`

Search the knowledge base.

**Request:**
```json
{ "query": "how to configure retry policy", "project": "homelab" }
```

**Response — found:**
```json
{
  "status": "found",
  "query": "...",
  "normalized_query": "...",
  "results": [{ "score": 0.82, "content": "...", "metadata": {} }]
}
```

**Response — not found:**
```json
{ "status": "not_found", "message": "NOT FOUND IN RAG" }
```

### `POST /rag/debug`

Returns all raw Qdrant results before threshold filtering. Use to tune `ScoreThreshold`.

**Request:** same as `/rag/search`

**Response:**
```json
{
  "normalized_query": "...",
  "threshold": 0.35,
  "total_raw_results": 5,
  "results_above_threshold": 2,
  "results": [...]
}
```

### `GET /scalar/`

```bash
rtk curl http://localhost:5200/scalar/
```

### `GET /openapi/v1.json`

```bash
rtk curl http://localhost:5200/openapi/v1.json
```

---

## Configuration

Update both config files together to avoid drift:
- `src/appsettings.json` (dev)
- `/opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json` (VM B1 runtime mount)

```json
{
  "RagGateway": {
    "OllamaBaseUrl": "http://192.168.18.199:11434",
    "QdrantBaseUrl": "http://192.168.18.199:6333",
    "OllamaModel": "nomic-embed-text",
    "QdrantCollection": "knowledge_v2_keyfacts",
    "QdrantApiKey": "",
    "ScoreThreshold": 0.35,
    "ResultLimit": 8,
    "DenseVectorName": "dense",
    "SparseVectorName": "sparse",
    "EnableHybridSearch": true,
    "HybridPrefetchLimit": 30,
    "SparsePrefetchLimit": 5,
    "SparseScoreThreshold": 0.01,
    "FusionMethod": "rrf",
    "SparseInferenceModel": "Qdrant/bm25"
  }
}
```

---

## Running the Gateway

**Local:**
```bash
rtk dotnet run --project src
```

**Docker (VM B1):**
```bash
rtk git push origin main
rtk ssh figulazmi@192.168.18.199 \
  'cd /opt/homelab/ai-stack/rag-gateway-mini && rtk sudo git fetch origin && rtk sudo git reset --hard origin/main && cd src && rtk sudo docker compose up -d --build'
rtk curl http://192.168.18.199:5200/scalar/
rtk curl http://192.168.18.199:5200/openapi/v1.json
```

Interactive API docs (Scalar UI): `http://localhost:5200/scalar/`

For exact production verification commands and current pass criteria, use `docs/testing/TEST_STRATEGY.md` as the canonical source.
