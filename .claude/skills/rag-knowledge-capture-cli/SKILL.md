---
name: rag-knowledge-capture-cli
description: >
  Generate RAG-optimized knowledge chunks from a Claude Code CLI session (VS Code).
  Integrated with CLAUDE.md Session End Protocol — auto-triggered before /clear.
  Produces chunked Markdown files with Qdrant-ready frontmatter metadata.
  Qdrant collection: "knowledge". Chunk strategy: split per problem-solution pair.
  Output language: English only (optimized for embedding quality).
  Saves to .claude/summaries/ and signals push-to-qdrant.sh.
  NEVER push to any API. ONLY output .md files.
---

# RAG KNOWLEDGE CAPTURE SKILL

## For: Claude Code CLI (VS Code)

## Integrated with: CLAUDE.md Session End Protocol

## Target: Qdrant collection "knowledge" (VM B1) via ~/scripts/push-to-qdrant.sh

## Language: English only — all output must be in English for embedding quality

---

## PURPOSE

Convert a Claude Code CLI session into RAG-optimized, independently embeddable
knowledge chunks. Designed to integrate with the CLAUDE.md Session End Protocol.

Each chunk must be semantically rich and self-contained — Qdrant embeds each
chunk independently. Poor context = poor retrieval.

---

## CLAUDE.md SESSION END PROTOCOL INTEGRATION

This skill is the implementation of Step 1 in the Session End Protocol:

```
## Session End Protocol
Before ending any session or using /clear, always:
1. ← THIS SKILL handles this step
   Run: summarize this session as a knowledge document
2. Save to: .claude/summaries/YYYY-MM-DD-[topic].md
3. Run: bash ~/scripts/push-to-qdrant.sh .claude/summaries/[file]
```

### What this skill does:

- Generates the knowledge document (Step 1)
- Suggests the exact filename for Step 2
- Prints the exact bash command for Step 3

### What the user does after:

```bash
# Step 2: Save (Claude Code CLI can do this directly)
# The skill will instruct Claude to save the file automatically

# Step 3: Push to Qdrant
bash ~/scripts/push-to-qdrant.sh .claude/summaries/YYYY-MM-DD-[topic].md
```

---

## WHEN TO TRIGGER

Trigger automatically when:

- User types `/clear` → run this BEFORE clearing
- User says "session end", "end session", "clear session"
- User says "simpan ke qdrant", "rag summary", "knowledge capture"
- Session End Protocol is invoked from CLAUDE.md

Also trigger on demand:

- "rag capture"
- "save session"
- "ringkasan qdrant"

---

## AUTO-SAVE BEHAVIOR (CLI-specific)

After generating the knowledge document, Claude Code CLI MUST:

1. Determine filename: `YYYY-MM-DD-[slug-topic].md`
   - slug-topic: lowercase, hyphenated, max 5 words
   - Example: `2026-04-06-iis-ssl-binding-fix.md`

2. Save file to: `.claude/summaries/[filename]`
   - Create directory if not exists: `mkdir -p .claude/summaries`

3. Print confirmation and push command:

```
✅ Knowledge chunk saved: .claude/summaries/2026-04-06-[topic].md
📦 Push to Qdrant (menggunakan Git Bash bukan PowerShell):
   bash ~/scripts/push-to-qdrant.sh .claude/summaries/2026-04-06-[topic].md
```

---

## OUTPUT MODE

DEFAULT: CHUNKED

- One .md file per session
- Multiple `## CHUNK` blocks inside one file
- Each chunk = one independently embeddable unit (150–400 words)
- Split strategy: **one chunk per distinct problem-solution pair** (PRIMARY RULE)
- A new problem introduced = a new chunk, always
- Iterative debugging steps for the SAME problem = merged into one chunk

---

## FRONTMATTER SCHEMA (REQUIRED)

### topic field rules

- Plain ASCII only — no em dash, no special characters
- ✅ Good : SDL Phase 2 - Blazor Client Kicked Session Detection
- ❌ Bad : SDL Phase 2 — Blazor Client-Side Kicked Session Detection

```yaml
---
id: [YYYY-MM-DD]-[slug-topic]
date: YYYY-MM-DD
source: claude-code-cli
project: [project name]               # petrochina-eproc | homelab | mit-internal | homeplate
chunk_type: [type]                     # REQUIRED: debug | feature | runbook | pattern | decision | reference
topic: [concise topic title]
tags: [tag1, tag2, tag3]              # lowercase, hyphenated, max 8 tags
related: [topic-1, topic-2]
session_type: [type]                  # debug | feature | setup | refactor | architecture | research | feature-retrospective | ops-documentation
environment: [dev|uat|prod|homelab]
git_branch: [branch name if applicable]
status: implemented                   # REQUIRED: implemented | planned | deprecated
chunk_source: code                    # REQUIRED: code | design | ops
---
```

### Tag guidelines

- Tech tags: blazor, ef-core, hangfire, n8n, qdrant, iis, gitea, mediatR, mudblazor
- Domain tags: eproc, petrochina, homelab, auth, ci-cd, vendor, employee, jde-sync
- Outcome tags: fixed, implemented, planned, failed, pending, optimized
- Max 8 tags. Avoid generic tags.

### chunk_type field rules (REQUIRED — determines template body)

- `debug` — Reactive problem-solution. Bug appeared → diagnose → fix.
- `feature` — Feature Implementation Record. Planned work, retrospective capture of built features.
- `runbook` — Step-by-step operational procedure. Not problem-solution, but procedure.
- `pattern` — Reusable code/architecture pattern. Applicable across projects.
- `decision` — Architecture Decision Record (ADR). Why A was chosen over B.
- `reference` — Cheat sheet, config template, environment map. Factual, rarely changes.

### status field rules (REQUIRED — affects RAG retrieval)

- `implemented` — code is deployed or merged; Claude retrieves this by default
- `planned` — architecture design, roadmap, future feature; Claude skips this by default (requires `include_planned=true`)
- `deprecated` — no longer relevant but kept for historical context; Claude skips by default
- When in doubt: if no code was written this session → `planned`

### chunk_source field rules (REQUIRED)

- `code` — describes actual code, configuration, or deployed infrastructure
- `design` — architecture decision, design doc, flow diagram, roadmap
- `ops` — operational procedure, deployment, infrastructure management

### session_type field

Supported values: `debug` | `feature` | `setup` | `refactor` | `architecture` | `research` | `feature-retrospective` | `ops-documentation`

### git_branch field

- Only include if the session involved code changes on a specific branch
- Example: `feature/vendor-auth-fix`, `uat`, `main`

---

## CHUNK TYPE SELECTION GUIDE

Use this guide to pick the correct `chunk_type`:

| Trigger | chunk_type | Example |
|---------|------------|---------|
| Error/bug → fix | `debug` | SSL binding error, null deserialization |
| Build/implement feature | `feature` | SDL Phase 1, JDE Sync, Vendor Registration |
| "How do I..." (procedure) | `runbook` | Deploy to IIS, Setup Gitea Actions, Configure n8n |
| Reusable approach across projects | `pattern` | BulkSyncAsync, CQRS handler template, MudBlazor patterns |
| "Why A instead of B?" | `decision` | Qdrant vs ChromaDB, Hangfire vs Quartz, Token Slot vs SignalR |
| Factual reference / config | `reference` | Server topology, port mappings, Git aliases, env variables |

### Quick Decision Tree

1. Is this fixing something broken? → `debug`
2. Is this building a new feature or capturing an existing one? → `feature`
3. Is this a step-by-step procedure someone else can follow? → `runbook`
4. Is this a pattern/approach reusable in other projects? → `pattern`
5. Is this recording an architecture decision and its reasoning? → `decision`
6. Is this factual information that rarely changes? → `reference`

---

## CHUNK STRUCTURE PER TYPE (REQUIRED)

> **LANGUAGE LOCK — ENFORCED AT TEMPLATE LEVEL**
> ALL content in every chunk field MUST be written in English.
> This includes all section headers and content within each template.
> Bahasa Indonesia is PROHIBITED. Writing in Indonesian inside a chunk: stop, translate, continue.
> If you catch yourself writing Indonesian inside a chunk: stop, translate, continue.

### Template 1: debug (Default)

````markdown
## CHUNK [N]: [Chunk Title]

### Context
[1-3 sentences. System, goal, constraint. Self-contained.]

### Problem
[Specific issue, error message, symptoms.]

### Solution
[Actual fix, decision, reasoning. This is retrieval core.]

### Key Facts
[Minimum 3. Atomic, independently searchable.]
- Fact 1
- Fact 2
- Fact 3

### Code / Commands
[ONLY if essential. Keep concise.]
\```language
code here
\```

### Caveats
[ONLY if important gotchas exist.]
````

### Template 2: feature

````markdown
## CHUNK [N]: [Feature Name — Phase/Aspect]

### Context
[1-3 sentences. What system, what business need, what constraint.]

### Requirements
[2-5 bullets. What must this feature achieve?]

### Architecture Decision
[Why this approach was chosen. What alternatives were considered and rejected.]

### Implementation
[How it was built. Key technical details, patterns used, files touched.]

### Key Facts
[Minimum 3. Atomic, independently searchable.]
- Fact 1
- Fact 2
- Fact 3

### Code / Commands
[ONLY if essential. Key code snippets showing the pattern.]

### Lessons Learned
[What would be done differently. What surprised you. Gotchas for next time.]
````

### Template 3: runbook

````markdown
## CHUNK [N]: [Procedure Name]

### Context
[1-3 sentences. When and why you need this procedure.]

### Prerequisites
[What must be ready before starting. Tools, access, configs.]

### Steps
[Numbered, sequential steps. Each step = one action.]
1. Step 1
2. Step 2
3. Step 3

### Verification
[How to confirm the procedure succeeded. Expected output/state.]

### Key Facts
[Minimum 3. Atomic, independently searchable.]
- Fact 1
- Fact 2
- Fact 3

### Troubleshooting
[Common failures during this procedure and their fixes.]
````

### Template 4: pattern

````markdown
## CHUNK [N]: [Pattern Name]

### Context
[1-3 sentences. What problem class this pattern solves.]

### When to Use
[Specific conditions where this pattern is appropriate.]

### When NOT to Use
[Conditions where this pattern is wrong. Anti-patterns.]

### Implementation
[How to implement. Step-by-step or structural description.]

### Key Facts
[Minimum 3. Atomic, independently searchable.]
- Fact 1
- Fact 2
- Fact 3

### Code / Commands
[Reference implementation. Keep concise but complete enough to be useful.]

### Variations
[Known variations or adaptations of this pattern.]
````

### Template 5: decision

````markdown
## CHUNK [N]: [Decision Title]

### Context
[1-3 sentences. What situation required a decision.]

### Decision Required
[What specific question needed to be answered.]

### Options Considered
[List each option with brief pro/con.]
- **Option A**: [description] — Pro: X, Con: Y
- **Option B**: [description] — Pro: X, Con: Y

### Decision
[Which option was chosen.]

### Rationale
[Why this option was chosen over others. Key reasoning.]

### Consequences
[Trade-offs accepted. What this decision enables and constrains.]

### Key Facts
[Minimum 3. Atomic, independently searchable.]
- Fact 1
- Fact 2
- Fact 3
````

### Template 6: reference

````markdown
## CHUNK [N]: [Reference Title]

### Context
[1-2 sentences. What this reference covers and when to use it.]

### Content
[The actual reference information. Can be structured as needed:
 table, list, key-value pairs, config block, etc.]

### Key Facts
[Minimum 3. Atomic, independently searchable.]
- Fact 1
- Fact 2
- Fact 3

### Related Commands
[ONLY if applicable. Quick-reference commands related to this content.]
````

---

## CHUNK SPLITTING RULES

PRIMARY RULE: **one distinct problem/topic = one chunk**

All chunks within a single file MUST have the same `chunk_type`.
If a session produces knowledge of different types (e.g., a debug fix AND an architecture decision),
generate SEPARATE files with different `chunk_type` values.

Split new chunk when:

- A new, separate problem/topic is introduced (even in the same session)
- A different system or layer is the subject (e.g., IIS → Gitea → Hangfire = 3 chunks)
- An independent decision or pattern is identified

Merge into one chunk when:

- Same problem, iterative debugging steps toward the same resolution
- Follow-up discovery directly caused by the same root problem
- Context is inseparable — chunk would be meaningless without the other part

---

## SESSION METADATA BLOCK (always at end)

```markdown
---

## SESSION METADATA

- **Total chunks**: [N]
- **Qdrant collection**: knowledge
- **Primary project**: [project]
- **Stack involved**: [technologies used]
- **Files modified**: [list key files if applicable]
- **Git branch**: [branch if applicable]
- **Unresolved items**: [open questions or next steps]
- **Author**: Figur Ulul Azmi
- **Generated by**: Claude Code CLI — RAG Knowledge Capture Skill
```

---

## HARD RULES

- NEVER output empty chunks
- NEVER use "as mentioned above" — every chunk is self-contained
- NEVER omit frontmatter
- NEVER call any external API or push to Notion
- NEVER skip the auto-save step (for CLI mode)
- NEVER write output in Indonesian — English only, all sections including Context and Solution
- NEVER use em dash (—) or special Unicode characters in frontmatter fields
  (topic, tags, related, etc.) — use plain hyphen (-) or remove entirely
  Reason: bash grep/sed cannot encode em dash correctly → corrupts Qdrant payload
- NEVER mix chunk_types in a single file — one file = one chunk_type
- NEVER skip chunk_type field in frontmatter — it is REQUIRED
- ALWAYS print the push-to-qdrant.sh command after saving
- ALWAYS write Key Facts as standalone searchable English sentences
- ALWAYS split at problem-solution boundary — one problem = one chunk, no exceptions
- ALWAYS suggest filename before saving — let user confirm if session is ambiguous
- ALWAYS include `collection: knowledge` note in SESSION METADATA
- ALWAYS use the correct template body for the selected chunk_type
- ALWAYS check CHUNK TYPE SELECTION GUIDE when unsure which type to use

---

## CONFLICT WITH /clear

If user types `/clear` without running Session End Protocol first:

→ STOP the clear action
→ Say: "⚠️ Session End Protocol belum dijalankan. Jalankan RAG capture dulu?"
→ Wait for user confirmation
→ If confirmed: run this skill first, then allow /clear
→ If skipped: allow /clear but warn that session knowledge will be lost

---

## EXAMPLE FULL OUTPUT

### EXAMPLE: debug chunk_type

````markdown
---
id: 2026-04-06-hangfire-jde-sync-failure
date: 2026-04-06
source: claude-code-cli
project: petrochina-eproc
chunk_type: debug
topic: Hangfire JDE Sync Intermittent Failure Debug
tags: [hangfire, jde-sync, ef-core, bulk-extensions, petrochina, eproc, debug, fixed]
related: [jde-integration, employee-sync, department-sync]
session_type: debug
environment: dev
git_branch: feature/jde-sync-fix
status: implemented
chunk_source: code
---

## CHUNK 1: Hangfire Job Completes Without Error But Data Not Updated

### Context

PetroChina Eproc uses Hangfire cron job (03:00 WIB) to sync employee and department
data from JDE via SyncJdeDataHandler. Job runs in D2 domain using MediatR dispatch
and BulkSyncAsync (TRUNCATE + BulkInsert + transaction).

### Problem

Job status shows "Succeeded" in Hangfire dashboard but target DB tables not updated.
No exceptions thrown. Issue intermittent — occurs roughly 2–3x per week in dev env.
CPU and memory normal. SQL Server connections not spiking.

### Solution

Root cause: missing [JsonPropertyName] attributes on JDE API response DTOs.
System.Text.Json silently ignores unmapped properties — deserialization returns
default/null values. BulkInsert then writes nulls, overwriting valid data.
Fix: add explicit [JsonPropertyName] on all JDE DTO properties matching API response
field names exactly (case-sensitive).

### Key Facts

- System.Text.Json default behavior: silently skips unknown JSON properties, no exception
- Missing [JsonPropertyName] causes silent null deserialization — no error thrown
- BulkSyncAsync uses TRUNCATE before insert — null data overwrites valid records
- Hangfire marks job "Succeeded" regardless of data correctness if no exception thrown
- Fix: [JsonPropertyName("employeeCode")] must match JDE API response field name exactly

### Code / Commands

```csharp
// Before (broken — silent null)
public string EmployeeCode { get; set; }

// After (fixed)
[JsonPropertyName("employeeCode")]
public string EmployeeCode { get; set; }
```

### Caveats

Null-to-empty mapping gaps also found — some nullable JDE fields mapped to
non-nullable DB columns. Add null coalescing in mapping layer, not in DTO.

---

## CHUNK 2: Domain Write Isolation Violation in Sync Handler

### Context

Same sync session. After fixing JsonPropertyName, discovered a second issue:
SyncJdeDataHandler was calling a repository from D1 (read domain) inside D2
(write domain) sync handler — violating Clean Architecture domain isolation.

### Problem

D2 SyncDepartmentDataAsync calling D1 DepartmentReadRepository to check existing
records before insert. This created a cross-domain dependency and broke CQRS
read/write separation.

### Solution

Removed cross-domain repository call. BulkSyncAsync already handles existence
check implicitly via TRUNCATE + full re-insert pattern. No pre-check needed.
If selective upsert needed in future: use BulkExtensions BulkMerge, not manual check.

### Key Facts

- CQRS write handlers must never call read repositories from another domain
- BulkSyncAsync (TRUNCATE + BulkInsert) is idempotent — no existence pre-check needed
- BulkExtensions BulkMerge available for selective upsert without cross-domain violation
- Domain isolation: D1=read, D2=write — handlers must not cross this boundary

---

## SESSION METADATA

- **Total chunks**: 2
- **Qdrant collection**: knowledge
- **Primary project**: petrochina-eproc
- **Stack involved**: .NET 9, Hangfire, EF Core BulkExtensions, MediatR, System.Text.Json, JDE API
- **Files modified**: SyncJdeDataHandler.cs, EmployeeJdeDto.cs, DepartmentJdeDto.cs
- **Git branch**: feature/jde-sync-fix
- **Unresolved items**: Monitor prod after deploy — check if intermittent issue fully resolved
- **Author**: Figur Ulul Azmi
- **Generated by**: Claude Code CLI — RAG Knowledge Capture Skill
````

---

### EXAMPLE: runbook chunk_type

````markdown
---
id: 2026-04-13-iis-blazor-deploy-procedure
date: 2026-04-13
source: claude-code-cli
project: petrochina-eproc
chunk_type: runbook
topic: IIS Blazor Server Deployment to PetroChina Dev Server
tags: [iis, blazor, deployment, petrochina, eproc, windows-server]
related: [iis-ssl-binding, gitea-cicd-pipeline]
session_type: ops-documentation
environment: dev
git_branch: main
status: implemented
chunk_source: ops
---

## CHUNK 1: Deploy Blazor Server App to IIS on PetroChina Dev

### Context
PetroChina Eproc Blazor Server apps (internal + external) are deployed to IIS
on Windows Server behind GlobalProtect VPN. This procedure covers manual deployment
when CI/CD pipeline is not available or for emergency hotfixes.

### Prerequisites
- GlobalProtect VPN connected to PetroChina network
- RDP access to dev server (credentials in team vault)
- Published build output from `dotnet publish -c Release`
- IIS Manager access on target server

### Steps
1. Connect to PetroChina VPN via GlobalProtect
2. RDP to dev server
3. Open IIS Manager → navigate to target site (eproc-internal or eproc-external)
4. Stop the application pool for the target site
5. Robocopy published output to site directory: `robocopy publish/ D:\sites\eproc-internal /MIR /XF appsettings.json appsettings.Production.json`
6. Start the application pool
7. Browse to site URL to verify startup

### Verification
- Site loads without 500 error
- Login page renders correctly
- Check Windows Event Log for ASP.NET Core startup errors
- Verify app pool is running (not stopped/crashed)

### Key Facts
- Always use /XF flag with robocopy to exclude appsettings files from overwrite
- App pool must be stopped before copy to avoid file lock errors
- appsettings.Production.json on server contains environment-specific config — never overwrite
- IIS app pool recycle alone is not sufficient — full stop/start required for .NET 9 apps

### Troubleshooting
- 502.5 error after deploy: check that .NET 9 hosting bundle is installed on server
- App pool crashes immediately: check Event Viewer → Windows Logs → Application for CLR errors
- CSS/JS not loading: clear browser cache or check if _framework path is correct

---

## SESSION METADATA

- **Total chunks**: 1
- **Qdrant collection**: knowledge
- **Primary project**: petrochina-eproc
- **Stack involved**: IIS, Blazor Server, .NET 9, Windows Server, robocopy
- **Files modified**: none (operational procedure)
- **Git branch**: main
- **Unresolved items**: Automate via Gitea Actions pipeline
- **Author**: Figur Ulul Azmi
- **Generated by**: Claude Code CLI — RAG Knowledge Capture Skill
````

```
✅ Knowledge chunk saved: .claude/summaries/2026-04-06-hangfire-jde-sync-failure.md
📦 Push to Qdrant:
   bash ~/scripts/push-to-qdrant.sh .claude/summaries/2026-04-06-hangfire-jde-sync-failure.md
```
