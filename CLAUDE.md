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

ASP.NET Core 9 RAG gateway. Stack: .NET 9, Serilog, Scalar. Infra: Ollama (embeddings) + Qdrant (vectors). Runs on VM B1 `192.168.18.199:5200` via Docker Compose.

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
ssh figulazmi@192.168.18.199 'cd /opt/homelab/ai-stack/rag-gateway-mini && git pull && cd src && docker compose up -d --build'
curl http://192.168.18.199:5200/health
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
cat <<'RAGBODY_EOF' | rag add -p PROJECT -t TYPE --topic "TOPIC" --tags "tag1,tag2,tag3"
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
RAGBODY_EOF
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
  - **First tag MUST be one of**: `dotnet` | `python` | `homelab`
  - `dotnet` — .NET 9, Blazor, EF Core, MediatR, Hangfire, C# patterns
  - `python` — Python scripts, tools, rag_capture, eval, automation
  - `homelab` — VM B1, Docker, n8n, Qdrant, Ollama, infra, networking

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

## Session Start Protocol (EVERY new session — run FIRST)

```bash
rag resume          # check for open checkpoints from previous sessions
```

- **FOUND** → load all fields from checkpoint, skip codebase exploration entirely,
  execute `next_step` directly using `rtk read` on `files_modified` only
- **NOT FOUND** → proceed with normal RAG-first protocol

RTK precision reads on resume (saves ~75-90% tokens vs broad exploration):

```bash
# For each file in checkpoint's files_modified:
rtk read src/Controllers/RagController.cs   # targeted, not full exploration
```

State explicitly: "Resuming checkpoint: [topic] — executing: [next_step]"

## Checkpoint Trigger Rules

Emit `rag checkpoint` when ANY of these:

1. `/status` shows token usage **>= 85%** (hard limit — safety buffer of 15%)
2. `/status` shows token usage **>= 75%** (early warning — use `--quick` flag)
3. User says "checkpoint" / "save progress" / "lanjut besok" / "lanjut sesi baru"
4. End of complex multi-step session (even if not at token limit)
5. Before switching to a different problem mid-session

**Token budget rule: checkpoint MUST cost < 15% of remaining tokens.**
Achieve this by writing content from active context ONLY. Zero new file reads.

| What                              | How                                    | ~Tokens        |
| --------------------------------- | -------------------------------------- | -------------- |
| Body (Problem/Progress/Key Facts) | from memory                            | 800-1200       |
| `files_modified`                  | `rtk git diff --name-only HEAD` (auto) | 50             |
| `decisions_made`                  | `rtk git log --oneline -5` (auto)      | 100            |
| CLI overhead                      | heredoc pipe                           | 150            |
| **Total**                         |                                        | **~1100-1500** |

Heredoc template (standard mode, ~85% trigger):

```bash
cat <<'RAGCHK' | rag checkpoint -p PROJECT --topic "..." \
  --next-step "exact action: file.cs:line" \
  --hypothesis "current working theory" \
  --trigger "85%"
### Problem
[what we're solving]
### Progress
[what was done this session]
### Key Facts
- fact 1
- fact 2
- fact 3
RAGCHK
```

Emergency quick mode (~75% trigger or <5% remaining):

```bash
rag checkpoint -p PROJECT --topic "..." --next-step "exact action" --trigger "75%" --quick
```

Then push immediately:

```bash
bash ~/scripts/push-to-qdrant.sh .claude/checkpoints/YYYY-MM-DD-*.md
```

When problem is solved, promote checkpoint to knowledge:

```bash
rag promote --file .claude/checkpoints/YYYY-MM-DD-[slug]-001.md
bash ~/scripts/push-to-qdrant.sh .claude/summaries/YYYY-MM-DD-[slug]-promoted.md
```

## Session end (before /clear)

1. Capture any solved-but-unsaved problems via `rag add`
2. Run `rag merge --output YYYY-MM-DD-[slug].md`
3. Relay the push command from rag CLI stdout to user (don't duplicate)
