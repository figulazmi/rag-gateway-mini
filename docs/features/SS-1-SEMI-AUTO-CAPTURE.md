# SS-1: Semi-Auto Knowledge Capture

> **Feature Type:** Workflow Improvement  
> **Status:** Planned  
> **Owner:** Figur Ulul Azmi  
> **Created:** 2026-05-10  
> **Target:** Reduce manual RAG capture effort by 90% while preserving corpus quality

---

## Design

### Goal

Reduce manual capture effort while preserving user control and Qdrant corpus quality. The workflow should detect when a task appears solved, propose a draft capture, ask for approval, then run the existing local `rag add` → `rag merge` → auto-push pipeline only after confirmation.

### Why This Is Next

P1-P4 roadmap items are closed, and future ROI now depends on keeping `knowledge_v2_keyfacts` current without polluting it. Full auto-capture has higher false-positive risk. Semi-auto capture gives most of the effort reduction (90%+) while keeping a review gate.

**Current pain:**
- Manual capture takes 2-3 minutes per chunk
- Easy to forget capturing after solving a problem
- Context fades if capture is delayed

**Expected improvement:**
- Semi-auto capture takes 2 seconds (confirm) + 30 seconds (review)
- Auto-detection prevents "forgot to capture"
- Immediate proposal while context is fresh

### Scope

- Add a semi-auto capture workflow around the existing local capture toolchain.
- Reuse `~/scripts/rag-capture-v2/rag_capture.py` and existing `rag merge` auto-push behavior.
- Keep all persistence local until the user approves capture.
- Do not change n8n, Qdrant schema, vector search, or eval scoring for this task.

### Non-Goals

- No silent full-auto capture.
- No background writes to Qdrant without explicit user approval.
- No new chunk schema unless required by existing validators.
- No reranker, sparse IDF tuning, or retrieval algorithm changes.

---

## Implementation Plan

### Step 1: Define Solved-Task Detection Rules

**Trigger candidates when:**
- User says signals such as `works`, `berhasil`, `fixed`, `oke sudah`, or asks to save/capture.
- A verified build/test/smoke passes after a fix.
- User explicitly requests capture via command or phrase.

**Do NOT trigger on:**
- Intermediate debugging steps (failed attempts, hypothesis testing).
- Pure discussion or clarifying questions.
- Typo-only edits or trivial changes.
- Ongoing work without verification.

**Implementation approach:**
- Pattern matching on user messages for solved-task signals.
- State tracking: was there a problem → solution → verification cycle?
- Confidence threshold: only propose if confidence >= 80%.

### Step 2: Create Capture Proposal Object

**Fields:**
- `topic` (string, ASCII, max 60 chars)
- `chunk_type` (debug | feature | runbook | pattern | decision | reference | implementation-spec)
- `project` (default: `homelab`)
- `tags` (array, first tag must be: homelab | dotnet | python)
- `environment` (default: `homelab`)
- `status` (default: `implemented`)
- `source_summary` (1-2 sentences: what was the problem and solution)
- `target_files` (array of file paths touched)
- `verification_evidence` (test pass, build success, smoke result)
- `proposed_key_facts` (array of 3-5 atomic facts)

**Validation before showing proposal:**
- `topic.length <= 60`
- `topic.isascii() == True`
- `chunk_type in VALID_TYPES`
- `tags[0] in ['homelab', 'dotnet', 'python']`

### Step 3: Add User Approval Gate

**Presentation format (card, not table):**

```
🤖 Detected solved task

Topic: [proposed topic]
Type: [chunk_type]
Tags: [tag1, tag2, tag3]

Summary: [1-2 sentence source_summary]

Target Files:
- [file1]
- [file2]

Key Facts:
- [fact1]
- [fact2]
- [fact3]

Choices:
[Approve] [Edit] [Skip]
```

**User actions:**
- **Approve:** Run capture immediately with proposed values.
- **Edit:** Let user modify topic, type, tags, or key facts before running.
- **Skip:** Record nothing, create no drafts, no Qdrant write.

**Implementation:**
- Use `AskUserQuestion` tool with 3 options.
- If Edit chosen, follow up with text input prompts for each field.
- If Skip chosen, log the skip decision (for future detection tuning) but take no other action.

### Step 4: Generate Chunk Body After Approval

**Standard sections (all chunk types):**
```markdown
### Context
[1-2 sentences: system, goal, constraint]

### Problem
[Specific issue, error, requirement]

### Solution
[Actual fix/decision/implementation - be specific]

### Key Facts
- [Atomic fact 1]
- [Atomic fact 2]
- [Atomic fact 3]

### Code
[Optional: snippet only, not full file]
```

**Additional sections for `implementation-spec`:**
```markdown
### Target Files
- [repo-relative path 1]
- [repo-relative path 2]

### Interfaces
[Function signatures, class names, DTO shapes]

### Dependencies
[Import statements, package versions]

### Contract
[Input types, output types, error cases]

### Anti-Patterns
- DO NOT [X] because [Y]

### Verification
[Test snippet or manual check step]
```

**Content generation rules:**
- Extract from conversation history (last 10-20 turns).
- Avoid em dash, non-ASCII characters, placeholder values.
- Avoid angle brackets in examples (breaks shell heredoc).
- Keep total word count 150-250 (up to 400 for implementation-spec).

### Step 5: Execute Existing Pipeline Locally

**Commands:**

```bash
# Step 5.1: rag add
rtk python ~/scripts/rag-capture-v2/rag_capture.py add \
  -p homelab \
  -t [chunk_type] \
  --topic "[topic]" \
  --tags "[tag1,tag2,tag3]" \
  --environment homelab \
  --status implemented \
  --content "$CHUNK_BODY"

# Step 5.2: rag merge
rtk python ~/scripts/rag-capture-v2/rag_capture.py merge \
  -p homelab \
  --output 2026-05-10-[short-slug].md

# Step 5.3: auto-push (triggered by rag merge)
# push-to-qdrant.sh is called automatically by rag merge
```

**Verification:**
- Check `rag add` exit code (0 = success).
- Check `rag merge` output for "Auto-pushed to Qdrant" message.
- Parse Qdrant point delta from output (e.g., "609 → 610 (+1 new)").
- Confirm HTTP 200 from n8n webhook.

### Step 6: Add Validation and Failure Handling

**Pre-flight validation:**
- Before `rag add`, validate `topic.length <= 60` and `topic.isascii()`.
- If validation fails, sanitize and retry once:
  - Shorten topic by removing filler words.
  - Replace non-ASCII with ASCII equivalents.
  - Show user the sanitized version before retry.

**Failure handling:**
- If `rag add` rejects content (exit code != 0):
  - Parse error message for specific validation failure.
  - Sanitize content based on error (e.g., remove em dash if detected).
  - Retry once with sanitized content.
  - If second attempt fails, show error to user and skip capture.

- If `rag merge` push partially fails (some chunks HTTP 500):
  - Inspect failed chunk title and frontmatter topic.
  - Check for length >60 or non-ASCII in chunk title (not just frontmatter).
  - Offer to fix and retry, or skip failed chunk.

**Never use `Write` tool:**
- Only `rag_capture.py merge` may create `.claude/summaries/*.md`.
- If `rag merge` fails, do not fall back to `Write`.

### Step 7: Document Operator Usage

**Add runbook section to CLAUDE.md or skill:**

```markdown
## Semi-Auto Capture Workflow

When you see a capture proposal:

**Approve when:**
- Bug fixed and verified working
- Feature implemented and tested
- Runbook completed with verification
- Implementation-spec written for code-gen
- Architecture decision made with reasoning

**Edit when:**
- Topic is too long or unclear
- Chunk type is wrong (debug vs feature)
- Tags are missing or incorrect
- Key facts need refinement

**Skip when:**
- Typo fix or trivial change
- Failed hypothesis or wrong approach
- Intermediate debugging step
- Pure discussion without solution
- Temporary logging or exploration
```

### Step 8: Verification Checklist

**Dry-run test:**
1. Create a safe test scenario (e.g., fix a typo, verify it works).
2. Trigger semi-auto capture proposal.
3. Approve with a topic under 60 chars.
4. Verify draft created in `~/.rag_drafts/`.
5. Verify merge creates `.claude/summaries/2026-05-10-*.md`.
6. Verify auto-push returns HTTP 200.
7. Verify Qdrant point count increases (e.g., 610 → 611).
8. Query `search_knowledge` for the topic.
9. Confirm new chunk is retrievable with correct content.
10. Update `docs/TASKS.md` and this file status from `Planned` to `Done`.

---

## Canonical Task Tracker

| Task ID | Description | Status | Evidence |
|---------|-------------|--------|----------|
| SS-1.1 | Define solved-task detection rules | Planned | - |
| SS-1.2 | Create capture proposal object | Planned | - |
| SS-1.3 | Add user approval gate (Approve/Edit/Skip) | Planned | - |
| SS-1.4 | Generate chunk body after approval | Planned | - |
| SS-1.5 | Execute existing pipeline locally | Planned | - |
| SS-1.6 | Add validation and failure handling | Planned | - |
| SS-1.7 | Document operator usage | Planned | - |
| SS-1.8 | Verification checklist | Planned | - |

---

## Acceptance Criteria

- ✅ User is prompted before any new knowledge chunk is persisted or pushed.
- ✅ Approved capture completes with `rag add`, `rag merge`, and Qdrant push using existing tooling.
- ✅ Skipped capture creates no draft and no Qdrant point.
- ✅ Topic validation prevents the known n8n `must be ASCII and 1-60 chars` error.
- ✅ The final operator workflow is documented enough to resume in a new Claude Code session.

---

## Parallelization

- Can run independently from P2.2-B reranker and Pipeline #2C.
- Should not run in parallel with edits to `rag_capture.py` or `push-to-qdrant.sh` unless using separate worktrees.

---

## Next Action for Tomorrow

Start from SS-1.1: decide whether the semi-auto workflow should live as:
1. A Claude Code instruction/skill update (recommended for MVP)
2. A wrapper script around `rag_capture.py`
3. Both (skill orchestrates, script provides CLI interface)

**Recommended first implementation:** Instruction/skill-level orchestration that reuses the existing CLI unchanged. This allows rapid iteration without touching Python code.

---

*Last updated: 2026-05-10 · Owner: Figur Ulul Azmi*
