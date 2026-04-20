# RAG Gateway Mini

A lightweight ASP.NET Core 9 API that bridges your LLM tools and a Qdrant vector database.
It embeds queries via Ollama and returns the most relevant knowledge chunks — no generation, pure deterministic retrieval.

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
git clone <repo-url>
cd rag-gateway-mini
bash install.sh
```

The installer will:
1. Copy `rag` and `push-to-qdrant.sh` to `~/scripts/`
2. Add `~/scripts` to your `PATH`
3. Ask for your `QDRANT_API_KEY` (saved to `~/.config/qdrant-knowledge.env`)
4. Set up `RAG_BASE_URL` — auto-detected at runtime (no manual config needed)
5. Print MCP setup instructions for Claude Code

After install:

```bash
source ~/.bashrc          # reload PATH
bash install.sh --check   # verify everything works
```

### Update (after git pull)

```bash
git pull && bash install.sh --update
# or: make update
```

---

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

After solving a problem or completing a feature, capture it to Qdrant so the team can retrieve it later.

```bash
cat <<'EOF' | rag add -p homelab -t debug --topic "topic here" --tags "homelab,docker,qdrant"
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

# Merge drafts and push to Qdrant:
rag merge --output 2026-01-01-topic.md
```

Chunk types: `debug` | `feature` | `runbook` | `pattern` | `decision` | `reference`

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

**Windows:**

```bash
# 1. Copy template
cp scripts/claude-mcp-connect.ps1.template ~/.claude/claude-mcp-connect.ps1

# 2. Add to ~/.claude/settings.json:
{
  "mcpServers": {
    "qdrant-knowledge": {
      "command": "powershell",
      "args": ["-ExecutionPolicy", "Bypass", "-File",
               "C:\\Users\\<YOU>\\.claude\\claude-mcp-connect.ps1"]
    }
  }
}

# 3. Verify
claude mcp list
```

**Linux / Mac:**

```json
{
  "mcpServers": {
    "qdrant-knowledge": {
      "command": "ssh",
      "args": [
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        "figulazmi@192.168.18.199",
        "set -a; . ~/.qdrant-mcp.env; set +a; node /opt/mcp-servers/qdrant-knowledge/qdrant-mcp-server.js"
      ]
    }
  }
}
```

---

## Troubleshooting

### `Error: cannot reach RAG Gateway`

The CLI tried localhost, LAN, and Tailscale — all failed.

```bash
# Check which path is reachable:
curl -s --connect-timeout 3 http://192.168.18.199:5200/health
curl -s --connect-timeout 3 http://100.120.249.99:5200/health

# Override manually:
export RAG_BASE_URL=http://192.168.18.199:5200
```

### `Error: jq is not installed`

```bash
# Windows
winget install jqlang.jq

# Mac
brew install jq

# Linux
sudo apt install jq
```

### `rag: command not found`

```bash
echo $PATH | tr ':' '\n' | grep scripts   # check if ~/scripts is in PATH
source ~/.bashrc                          # reload
```

### RAG results not relevant (low scores)

```bash
rag "your query" -p homelab --debug   # shows raw scores and threshold
# Score < 0.55 = knowledge not yet captured -> do the work, then rag add
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
  "threshold": 0.55,
  "total_raw_results": 5,
  "results_above_threshold": 2,
  "results": [...]
}
```

### `GET /health`

```bash
curl http://localhost:5200/health
```

---

## Configuration

Edit `appsettings.json` (dev) or `/opt/rag-gateway/appsettings.Production.json` (prod):

```json
{
  "RagGateway": {
    "OllamaBaseUrl": "http://localhost:11434",
    "QdrantBaseUrl": "http://localhost:6333",
    "OllamaModel": "nomic-embed-text",
    "QdrantCollection": "knowledge_v2",
    "QdrantApiKey": "",
    "ScoreThreshold": 0.55,
    "ResultLimit": 5
  }
}
```

---

## Running the Gateway

**Local:**
```bash
dotnet run --project src
```

**Docker (VM B1):**
```bash
git push origin main
ssh figulazmi@192.168.18.199 \
  'cd /opt/homelab/ai-stack/rag-gateway-mini && git pull && cd src && docker compose up -d --build'
curl http://192.168.18.199:5200/health
```

Interactive API docs (Scalar UI): `http://localhost:5200/scalar/v1`
