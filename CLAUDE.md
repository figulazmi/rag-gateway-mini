# CLAUDE.md

## Fallback Essentials (if global CLAUDE.md is absent)

Full versions live in `~/.claude/CLAUDE.md`. Minimal rules below keep this repo self-sufficient.

### RTK (Rust Token Killer)
- Prefix every shell command with `rtk` (git, docker, gh, pnpm, curl, ls, grep, find, etc.). RTK is always safe — passes through if no filter exists.
- Inside chains too: `rtk git add . && rtk git commit -m "..." && rtk git push`.

### RAG-First Protocol
Before answering project-specific questions (architecture, patterns, prior decisions, deploy procedures, past bugs):
1. Load deferred schema once per session: `ToolSearch select:mcp__qdrant-knowledge__search_knowledge`
2. Call `search_knowledge(query, project="homelab")` — query ≥ 8 descriptive words.
3. If found → answer from RAG as ground truth. If not found → state "⚠️ NOT FOUND IN RAG" and proceed with general knowledge disclaimer.
4. Never silently fall back to training data for project questions.

Skip RAG for: general programming questions, framework docs, small talk.

## Project: rag-gateway-mini

ASP.NET Core 9 RAG gateway. Stack: .NET 9, Serilog, Scalar. Infra: Ollama (embeddings) + Qdrant (vectors). Runs on VM B1 `192.168.18.169:5200` via Docker Compose.

```
src/
  Controllers/                    — RagController
  Application/{Services,Interfaces,DTOs}
  Infrastructure/{AI,Configuration,Helpers}
```

## Build & Run

```bash
dotnet run --project src                    # local
cd src && docker compose up -d --build      # docker
```

## VM B1 Redeploy

```bash
git push origin main
ssh figulazmi@192.168.18.169 'cd /opt/homelab/ai-stack/rag-gateway-mini && git pull && cd src && docker compose up -d --build'
curl http://192.168.18.169:5200/health
```

Secrets live outside repo at `/opt/rag-gateway/appsettings.Production.json` (template: `src/appsettings.Production.json.template`). Build context is repo root so `Directory.Packages.props` is included.

## Critical Rules

- **English only** in code, comments, logs.
- **Zero warnings** — treat warnings as errors.
- **Plan first** if touching > 2 files.
- **Never commit** `appsettings.Production.json`.
- **STRICT RAG MODE**: call `search_knowledge(query, project="homelab")` BEFORE reading any source file for architecture/infra/prior-work questions. If empty → say "NOT FOUND IN KNOWLEDGE BASE".

# ═══════════════════════════════════════════════
# RAG INCREMENTAL CAPTURE
# ═══════════════════════════════════════════════

## When to auto-capture (no prompting needed)

Emit a chunk when ANY of these is true:
1. Problem solved + confirmed working ("works", "fixed", "berhasil", "oke")
2. Concrete feature implementation explained
3. Architectural decision made with clear reasoning
4. Step-by-step runbook completed
5. User says "chunk this" / "save this" / "rag capture" / "simpan ke qdrant"

**Skip** if: still debugging, clarifying questions, small talk, no confirmed solution.

## Auto-capture execution (MANDATORY)

Run `rag add` via Bash heredoc directly. **Never print chunk content to chat.**

```bash
cat <<'CONTENT' | rag add -p PROJECT -t TYPE --topic "TOPIC" --tags "tag1,tag2,tag3"
### Context
[1-2 sentences. Self-contained. What system, goal, constraint.]
### Problem
[Specific issue, error, requirement.]
### Solution
[The actual fix/decision/implementation. Be specific.]
### Key Facts
- [Atomic, independently searchable fact 1]
- [Atomic, independently searchable fact 2]
- [Atomic, independently searchable fact 3]
### Code
[Only if essential. Snippet only, not full file.]
CONTENT
```

Then print ONE status line:
```
📦 Captured chunk N: [TOPIC] → ~/scripts/.rag_drafts/chunk_NNN.md
```

**Forbidden:** printing `<<<RAG_CHUNK_*>>>` markers to chat, asking user to paste/run `rag add`, using Write tool to create the .md file (`rag merge` does that).

## Field rules

- **project**: `petrochina-eproc` | `homelab` | `mit-internal` | `homeplate`
- **type**: `debug` (bug fix) | `feature` | `runbook` | `pattern` | `decision` | `reference` (config/topology) | `implementation-spec` (code-ready spec for implementer models)
- **topic**: plain ASCII, no em dash, max 60 chars
- **tags**: comma-separated for `rag add` CLI, max 8, lowercase-hyphenated

## Content rules

- English only, 150–250 words (up to 400 for `implementation-spec`), self-contained
- Min 3 atomic Key Facts (each individually searchable)
- No em dash anywhere
- Code section optional for narrative types; required for `implementation-spec`

## Implementation-spec chunk rules

For chunks targeting consumption by implementer models (qwen2.5-coder etc.) to write code without hallucination. See `docs/RAG_V2_ROADMAP.md` and `~/.claude/commands/rag-knowledge-capture-cli.md` for full template.

Required sections (rag_capture.py warns if missing; hard-reject in P2.1):
- `### Target Files` — repo-relative paths, optional line ranges
- `### Interfaces` — function signatures, class names, DTO shapes
- `### Dependencies` — imports, package versions, config keys, external services
- `### Contract` — input types, output types, error cases, invariants
- `### Anti-Patterns` — "DO NOT X because Y" with brief rationale
- `### Verification` — runnable test or manual check step
- `### Key Facts` — minimum 3, independently searchable

For `feature` / `pattern` types: `### Target Files` is required; Interfaces/Contract/Verification are recommended.

## Session end (before /clear)

1. Capture any solved-but-unsaved problems via `rag add`
2. Run `rag merge --output YYYY-MM-DD-[slug].md`
3. Relay the push command from rag CLI stdout to user (don't duplicate)
