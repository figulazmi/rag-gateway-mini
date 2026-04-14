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

## VM B1 Deployment

App is live at: `http://192.168.18.169:5200/scalar/`

### Initial Deploy (one-time)

```bash
ssh user@192.168.18.169

git clone https://github.com/figulazmi/rag-gateway-mini.git /opt/homelab/ai-stack/rag-gateway-mini

mkdir -p /opt/rag-gateway
cp /opt/homelab/ai-stack/rag-gateway-mini/src/appsettings.Production.json.template \
   /opt/rag-gateway/appsettings.Production.json
nano /opt/rag-gateway/appsettings.Production.json  # fill QdrantApiKey

cd /opt/homelab/ai-stack/rag-gateway-mini/src
docker compose up -d --build
```

### Update / Redeploy

```bash
# Laptop — commit + push
git push origin main

# VM B1 — pull + rebuild
cd /opt/homelab/ai-stack/rag-gateway-mini
git pull origin main
cd src
docker compose up -d --build
```

### Verify

```bash
docker ps | grep rag-gateway
curl http://localhost:5200/health
```

### Notes

- Secrets config lives outside the repo: `/opt/rag-gateway/appsettings.Production.json`
- Use `docker compose` (space, not hyphen) — Docker Compose v2
- Build context is repo root (`..`) so `Directory.Packages.props` is included

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

# ═══════════════════════════════════════════════════════════════

# RAG INCREMENTAL CAPTURE — CLAUDE.md INTEGRATION BLOCK

# ═══════════════════════════════════════════════════════════════

## RAG Capture Protocol

### KAPAN Claude HARUS emit RAG signal (tanpa diminta)

Claude WAJIB emit RAG chunk signal setiap kali salah satu kondisi ini terpenuhi:

1. **Problem solved** — Claude berhasil memberikan solusi yang confirmed working
   (user mengatakan "works", "fixed", "berhasil", "oke", atau Claude menyimpulkan solusi final)

2. **Feature explained** — Claude selesai menjelaskan implementasi sebuah fitur
   (bukan sekedar diskusi — tapi implementasi konkret sudah dijelaskan)

3. **Decision made** — Arsitektur atau pendekatan teknis dipilih dengan reasoning jelas

4. **Runbook complete** — Step-by-step prosedur selesai didefinisikan

5. **User berkata** — "chunk this", "save this", "rag capture", "simpan ke qdrant"

### KAPAN Claude TIDAK emit signal

- Problem masih dalam diskusi / belum ada solusi
- User masih debugging, belum confirmed fix
- Pertanyaan clarifikasi, bukan problem solving
- Small talk atau context setting

---

### FORMAT OUTPUT saat emit RAG signal

Setelah problem selesai, Claude append blok berikut di akhir response:

````
<<<RAG_META:project=PROJECT,type=TYPE,topic=TOPIC PLAIN ASCII NO EM DASH,tags=tag1|tag2|tag3>>>
<<<RAG_CHUNK_START>>>
### Context
[1-2 sentences. What system, what goal, what constraint. Self-contained — no "as discussed above".]

### Problem
[Specific issue, error message, symptom, or requirement that triggered this work.]

### Solution
[The actual fix, decision, or implementation. This is the retrieval core — be specific.]

### Key Facts
- [Atomic, independently searchable English fact 1]
- [Atomic, independently searchable English fact 2]
- [Atomic, independently searchable English fact 3]
- [Add more if essential]

### Code
\```language
// Only if essential. Key snippet only, not full file.
\```
<<<RAG_CHUNK_END>>>
````

### Field rules untuk RAG_META signal

**project** — pilih satu: `petrochina-eproc` | `homelab` | `mit-internal` | `homeplate`

**type** — pilih satu berdasarkan tabel:
| Situasi | type |
|---------|------|
| Bug/error → fix confirmed | `debug` |
| Feature implementation explained | `feature` |
| Step-by-step procedure | `runbook` |
| Reusable approach/pattern | `pattern` |
| Architecture choice + reasoning | `decision` |
| Config, ports, env vars, topology | `reference` |

**topic** — plain ASCII, no em dash (—), no special chars, max 60 chars

- ✅ `SDL Phase 2 - Blazor Client Kicked Session Detection`
- ❌ `SDL Phase 2 — Blazor Client-Side Kicked Session`

**tags** — gunakan pipe (|) bukan koma, max 8 tags, lowercase-hyphenated

- Contoh: `sdl|auth|blazor|middleware|petrochina|eproc|fixed`

### Content rules (di dalam RAG_CHUNK_START...END)

- **English only** — seluruh content dalam Bahasa Inggris
- **150–250 words** — cukup padat tapi tidak verbose
- **Self-contained** — setiap chunk harus bisa dimengerti tanpa context lain
- **Min 3 Key Facts** — masing-masing harus bisa di-search sendiri
- **No em dash** di seluruh output termasuk content
- **Code section optional** — hanya jika snippet essential untuk memahami solusi

---

### AUTO-CAPTURE — Claude eksekusi sendiri, ZERO manual paste

Saat trigger tercapai, Claude WAJIB langsung jalankan `rag add` via Bash heredoc — content chunk TIDAK dicetak ke chat. Marker `<<<RAG_META:...>>>` + `<<<RAG_CHUNK_START/END>>>` hanya struktur internal Claude sebelum eksekusi, bukan output user-visible.

**Pola eksekusi (WAJIB):**

```bash
cat <<'CONTENT' | rag add -p PROJECT -t TYPE --topic "TOPIC" --tags "tag1,tag2,tag3"
### Context
...
### Problem
...
### Solution
...
### Key Facts
- ...
CONTENT
```

Setelah Bash sukses, Claude WAJIB print SATU baris status ke user:

```
📦 Captured chunk N: [TOPIC] → ~/scripts/.rag_drafts/chunk_NNN.md
```

**Dilarang:**
- ❌ Print blok `<<<RAG_CHUNK_START>>>...<<<RAG_CHUNK_END>>>` ke chat
- ❌ Bilang "Jalankan: rag add ... [paste content]" — Claude yang jalankan, bukan user
- ❌ Pakai Write tool untuk bikin file .md — `rag merge` yang bikin

Untuk detail lengkap flow, lihat skill `.claude/commands/rag-knowledge-capture-cli.md` (mode rescue).

---

### SESSION END — sebelum /clear

Sebelum /clear, Claude WAJIB:

1. Cek apakah ada problem yang selesai tapi belum di-capture → jalankan `rag add` via Bash untuk setiap chunk yang tertinggal
2. Jalankan `rag merge --output YYYY-MM-DD-[slug].md` via Bash → rag CLI akan cetak path file merged + push command otomatis
3. Print push command yang dihasilkan rag CLI ke user (jangan duplikasi — cukup relay stdout)

User tidak perlu invoke `/rag-knowledge-capture-cli` secara manual kecuali capture inkremental terlewat untuk seluruh sesi.

---

### CONTOH FULL FLOW

**Scenario:** User fix bug SDL middleware di petrochina-eproc, confirmed working.

Claude response normal → kemudian append:

````
<<<RAG_META:project=petrochina-eproc,type=debug,topic=SDL SessionValidationMiddleware Token Slot Fix,tags=sdl|auth|middleware|token-slot|blazor|petrochina|eproc|fixed>>>
<<<RAG_CHUNK_START>>>
### Context
PetroChina Eproc uses a Single Device Login (SDL) system enforced via
SessionValidationMiddleware. The middleware checks a token slot table to ensure
only one active session per user exists across Blazor Server and WASM apps.

### Problem
SessionValidationMiddleware threw NullReferenceException intermittently when
validating token slots for concurrent requests during login. Error occurred in
HttpContext extension method when session token was missing from request headers.

### Solution
Added null guard before token slot lookup in SessionValidationMiddleware.
Token extracted via TryGetValue instead of direct indexer access. Added early
return with 401 response when token is null or empty, preventing downstream NPE.

### Key Facts
- SDL middleware must handle missing token header gracefully — use TryGetValue not indexer
- NullReferenceException in middleware is not caught by global exception handler — fails silently
- Early return with 401 is correct SDL behavior when session token absent
- Token slot table is keyed by normalized username + device fingerprint hash

### Code
\```csharp
if (!context.Request.Headers.TryGetValue("X-Session-Token", out var token)
    || string.IsNullOrEmpty(token))
{
    context.Response.StatusCode = 401;
    return;
}
\```
<<<RAG_CHUNK_END>>>

📎 RAG chunk siap. Jalankan:
   rag add -p petrochina-eproc -t debug \
     --topic "SDL SessionValidationMiddleware Token Slot Fix" \
     --tags "sdl,auth,middleware,token-slot,blazor,petrochina,eproc,fixed" \
     --branch "feature/sdl-phase1"
   [paste content di atas]
````

# ═══════════════════════════════════════════════════════════════

<!-- rtk-instructions v2 -->

# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:

```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)

```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (90-99% savings)

```bash
rtk cargo test          # Cargo test failures only (90%)
rtk vitest run          # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)

```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)

```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)

```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
```

### Files & Search (60-75% savings)

```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%)
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)

```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)

```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)

```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands

```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category         | Commands                       | Typical Savings |
| ---------------- | ------------------------------ | --------------- |
| Tests            | vitest, playwright, cargo test | 90-99%          |
| Build            | next, tsc, lint, prettier      | 70-87%          |
| Git              | status, log, diff, add, commit | 59-80%          |
| GitHub           | gh pr, gh run, gh issue        | 26-87%          |
| Package Managers | pnpm, npm, npx                 | 70-90%          |
| Files            | ls, read, grep, find           | 60-75%          |
| Infrastructure   | docker, kubectl                | 85%             |
| Network          | curl, wget                     | 65-70%          |

Overall average: **60-90% token reduction** on common development operations.

<!-- /rtk-instructions -->
