# RAG Scripts Cleanup and Frontmatter Hook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move reusable RAG infrastructure scripts out of `rag-gateway-mini` into the separate `rag-tools` repo under `~/scripts/rag-infra/`, archive completed one-time migration scripts, update documentation, and add a versioned frontmatter pre-commit hook in `~/scripts/hooks/`.

**Architecture:** `rag-gateway-mini` keeps only project-specific scripts, fixtures, examples, and archived migration history. Reusable infrastructure tooling lives in the separate `rag-tools` checkout at `~/scripts`, grouped into `rag-infra/` for operational tools and `hooks/` for installable Git hooks. The target repo receives only an unversioned `.git/hooks/pre-commit` wrapper.

**Tech Stack:** Bash, Python 3 standard library, Git hooks, Qdrant/RAG docs.

---

## File Structure

### In `C:/Users/Clandesitine/scripts` (`rag-tools` repo)

- Create: `rag-infra/eval-retrieval-quality.py` — reusable retrieval quality evaluator.
- Create: `rag-infra/test-qdrant-retrieval.sh` — reusable Qdrant/MCP retrieval smoke script.
- Create: `rag-infra/qdrant-graph.sh` — reusable Qdrant graph/explore helper.
- Create: `rag-infra/qdrant-visualize.sh` — reusable Qdrant visualize helper.
- Create: `rag-infra/anomaly_check.py` — reusable RAG audit anomaly checker.
- Create: `rag-infra/snapshot_tamper_check.py` — reusable snapshot vector tamper checker.
- Create: `hooks/validate-rag-frontmatter.py` — versioned pre-commit frontmatter validator.
- Create: `hooks/install-rag-frontmatter-hook.sh` — versioned installer for local repo pre-commit wrapper.

### In `C:/Users/Clandesitine/source/repos/rag-gateway-mini`

- Move to archive: `scripts/archive/migrations/migrate-to-hybrid.py`
- Move to archive: `scripts/archive/migrations/add-snapshot-vector-migration.py`
- Move to archive: `scripts/archive/migrations/backfill-provenance.py`
- Move to archive: `scripts/archive/migrations/build-sparse-keyfacts-experiment.py`
- Move to archive: `scripts/archive/migrations/build-sparse-keyfacts-experiment-rest.py`
- Move to archive: `scripts/archive/migrations/redteam-probe.py`
- Delete after copy to rag-tools: reusable scripts listed above from `scripts/`.
- Keep: `scripts/smoke-p32-implementation-correctness.py` because it is project-specific.
- Keep: `scripts/init-docs-template.py` because it depends on this repo's `docs/templates/`.
- Keep: `scripts/eval-fixtures/*.json` because fixtures are repo docs/test data.
- Update: `scripts/README.md` to become an index that points reusable tools to `~/scripts/rag-infra/` and archived migrations to `scripts/archive/migrations/`.
- Update docs references from `scripts/eval-retrieval-quality.py` to `~/scripts/rag-infra/eval-retrieval-quality.py` where the evaluator is reusable.
- Keep historical reports under `.claude/reports/` unchanged.

---

### Task 1: Move Reusable RAG Infrastructure Scripts to `~/scripts/rag-infra/`

**Files:**
- Create directory: `C:/Users/Clandesitine/scripts/rag-infra/`
- Copy into rag-tools:
  - `scripts/eval-retrieval-quality.py`
  - `scripts/test-qdrant-retrieval.sh`
  - `scripts/qdrant-graph.sh`
  - `scripts/qdrant-visualize.sh`
  - `scripts/anomaly_check.py`
  - `scripts/snapshot_tamper_check.py`
- Remove same files from `rag-gateway-mini/scripts/` after successful copy.

- [ ] **Step 1: Create destination folder in rag-tools**

Run:
```bash
rtk mkdir -p "$HOME/scripts/rag-infra"
```

Expected: command exits `0`.

- [ ] **Step 2: Copy reusable scripts**

Run from `rag-gateway-mini` root:
```bash
rtk cp scripts/eval-retrieval-quality.py "$HOME/scripts/rag-infra/eval-retrieval-quality.py"
rtk cp scripts/test-qdrant-retrieval.sh "$HOME/scripts/rag-infra/test-qdrant-retrieval.sh"
rtk cp scripts/qdrant-graph.sh "$HOME/scripts/rag-infra/qdrant-graph.sh"
rtk cp scripts/qdrant-visualize.sh "$HOME/scripts/rag-infra/qdrant-visualize.sh"
rtk cp scripts/anomaly_check.py "$HOME/scripts/rag-infra/anomaly_check.py"
rtk cp scripts/snapshot_tamper_check.py "$HOME/scripts/rag-infra/snapshot_tamper_check.py"
```

Expected: all commands exit `0`.

- [ ] **Step 3: Make copied shell scripts executable**

Run:
```bash
rtk chmod +x "$HOME/scripts/rag-infra/test-qdrant-retrieval.sh" \
  "$HOME/scripts/rag-infra/qdrant-graph.sh" \
  "$HOME/scripts/rag-infra/qdrant-visualize.sh"
```

Expected: command exits `0`.

- [ ] **Step 4: Syntax-check copied Python scripts**

Run:
```bash
rtk python -m py_compile \
  "$HOME/scripts/rag-infra/eval-retrieval-quality.py" \
  "$HOME/scripts/rag-infra/anomaly_check.py" \
  "$HOME/scripts/rag-infra/snapshot_tamper_check.py"
```

Expected: command exits `0` with no syntax errors.

- [ ] **Step 5: Remove reusable scripts from rag-gateway-mini**

Run from `rag-gateway-mini` root:
```bash
rtk git rm scripts/eval-retrieval-quality.py \
  scripts/test-qdrant-retrieval.sh \
  scripts/qdrant-graph.sh \
  scripts/qdrant-visualize.sh \
  scripts/anomaly_check.py \
  scripts/snapshot_tamper_check.py
```

Expected: Git stages deletions for exactly these six files.

---

### Task 2: Archive One-Time Migration Scripts in `rag-gateway-mini`

**Files:**
- Move:
  - `scripts/migrate-to-hybrid.py` -> `scripts/archive/migrations/migrate-to-hybrid.py`
  - `scripts/add-snapshot-vector-migration.py` -> `scripts/archive/migrations/add-snapshot-vector-migration.py`
  - `scripts/backfill-provenance.py` -> `scripts/archive/migrations/backfill-provenance.py`
  - `scripts/build-sparse-keyfacts-experiment.py` -> `scripts/archive/migrations/build-sparse-keyfacts-experiment.py`
  - `scripts/build-sparse-keyfacts-experiment-rest.py` -> `scripts/archive/migrations/build-sparse-keyfacts-experiment-rest.py`
  - `scripts/redteam-probe.py` -> `scripts/archive/migrations/redteam-probe.py`

- [ ] **Step 1: Create archive folder**

Run:
```bash
rtk mkdir -p scripts/archive/migrations
```

Expected: command exits `0`.

- [ ] **Step 2: Move migration scripts with Git history-aware `git mv`**

Run:
```bash
rtk git mv scripts/migrate-to-hybrid.py scripts/archive/migrations/migrate-to-hybrid.py
rtk git mv scripts/add-snapshot-vector-migration.py scripts/archive/migrations/add-snapshot-vector-migration.py
rtk git mv scripts/backfill-provenance.py scripts/archive/migrations/backfill-provenance.py
rtk git mv scripts/build-sparse-keyfacts-experiment.py scripts/archive/migrations/build-sparse-keyfacts-experiment.py
rtk git mv scripts/build-sparse-keyfacts-experiment-rest.py scripts/archive/migrations/build-sparse-keyfacts-experiment-rest.py
rtk git mv scripts/redteam-probe.py scripts/archive/migrations/redteam-probe.py
```

Expected: Git stages renames for all six scripts.

- [ ] **Step 3: Add archive README**

Create `scripts/archive/README.md` with:
```markdown
# Archived Scripts

This folder preserves completed one-time migration and experiment scripts for audit history.

Do not use these scripts as the current operational path. Active reusable RAG infrastructure tools live in the separate rag-tools repository under `~/scripts/rag-infra/`.

## migrations/

Completed Qdrant/RAG migration scripts retained for historical reference:

- `migrate-to-hybrid.py`
- `add-snapshot-vector-migration.py`
- `backfill-provenance.py`
- `build-sparse-keyfacts-experiment.py`
- `build-sparse-keyfacts-experiment-rest.py`
- `redteam-probe.py`
```

Expected: archive README is staged later with docs updates.

---

### Task 3: Update Documentation References

**Files:**
- Modify: `scripts/README.md`
- Modify: `docs/planning/RAG_V2_ROADMAP.md`
- Modify: `docs/planning/RAG_EXTERNAL_BRAIN_PLAN.md`
- Modify: `docs/quality/RAG_EVAL_HARNESS.md`
- Modify: `docs/reference/RAG_MANUAL_BOOK.md`
- Modify: `docs/testing/TEST_STRATEGY.md`
- Modify: `docs/security/RAG_SECURITY_POSTURE.md`
- Modify: `docs/superpowers/specs/2026-05-10-p32-smoke-design.md`

- [ ] **Step 1: Replace current evaluator path in docs**

Replace operational references:
```text
scripts/eval-retrieval-quality.py
```
with:
```text
~/scripts/rag-infra/eval-retrieval-quality.py
```

Do this only in prose and command examples that tell users where to run the active evaluator. Leave historical report JSON content unchanged.

- [ ] **Step 2: Replace current reusable tool paths in docs**

Replace active operational paths:
```text
scripts/test-qdrant-retrieval.sh
scripts/qdrant-graph.sh
scripts/qdrant-visualize.sh
scripts/anomaly_check.py
scripts/snapshot_tamper_check.py
```
with:
```text
~/scripts/rag-infra/test-qdrant-retrieval.sh
~/scripts/rag-infra/qdrant-graph.sh
~/scripts/rag-infra/qdrant-visualize.sh
~/scripts/rag-infra/anomaly_check.py
~/scripts/rag-infra/snapshot_tamper_check.py
```

- [ ] **Step 3: Replace migration script paths in docs**

Replace active-looking migration paths:
```text
scripts/migrate-to-hybrid.py
scripts/add-snapshot-vector-migration.py
scripts/backfill-provenance.py
scripts/build-sparse-keyfacts-experiment.py
scripts/build-sparse-keyfacts-experiment-rest.py
scripts/redteam-probe.py
```
with archive paths:
```text
scripts/archive/migrations/migrate-to-hybrid.py
scripts/archive/migrations/add-snapshot-vector-migration.py
scripts/archive/migrations/backfill-provenance.py
scripts/archive/migrations/build-sparse-keyfacts-experiment.py
scripts/archive/migrations/build-sparse-keyfacts-experiment-rest.py
scripts/archive/migrations/redteam-probe.py
```

- [ ] **Step 4: Rewrite `scripts/README.md` as an index**

Replace `scripts/README.md` content with:
```markdown
# Project Scripts Index

This repo keeps only project-specific scripts, fixtures, examples, and archived one-time migrations.

## Active project-specific scripts

- `smoke-p32-implementation-correctness.py` — P3.2 implementation-correctness smoke harness for rag-gateway-mini.
- `init-docs-template.py` — initializes the reusable documentation template from this repo's `docs/templates/` folder.

## Fixtures and examples

- `eval-fixtures/` — retrieval and implementation smoke fixtures used by documentation and reports.
- `qdrant-knowledge.env.example` — example environment file only.

## Archived scripts

- `archive/migrations/` — completed one-time migration and experiment scripts retained for audit history.

## Reusable RAG infrastructure tools

Reusable tools are versioned in the separate rag-tools repository under `~/scripts/rag-infra/`, not in this project:

- `~/scripts/rag-infra/eval-retrieval-quality.py`
- `~/scripts/rag-infra/test-qdrant-retrieval.sh`
- `~/scripts/rag-infra/qdrant-graph.sh`
- `~/scripts/rag-infra/qdrant-visualize.sh`
- `~/scripts/rag-infra/anomaly_check.py`
- `~/scripts/rag-infra/snapshot_tamper_check.py`
```

- [ ] **Step 5: Verify no active docs point to moved root scripts**

Run:
```bash
rtk git grep -n "scripts/eval-retrieval-quality.py\|scripts/test-qdrant-retrieval.sh\|scripts/qdrant-graph.sh\|scripts/qdrant-visualize.sh\|scripts/anomaly_check.py\|scripts/snapshot_tamper_check.py\|scripts/redteam-probe.py\|scripts/backfill-provenance.py\|scripts/migrate-to-hybrid.py\|scripts/build-sparse-keyfacts" -- "*.md" "*.json"
```

Expected: remaining matches are either historical `.claude/reports/*.json`, `scripts/archive/migrations/...`, or explicitly archived paths.

---

### Task 4: Implement Versioned Frontmatter Hook in `~/scripts/hooks/`

**Files:**
- Create: `C:/Users/Clandesitine/scripts/hooks/validate-rag-frontmatter.py`
- Create: `C:/Users/Clandesitine/scripts/hooks/install-rag-frontmatter-hook.sh`

- [ ] **Step 1: Create hooks folder**

Run:
```bash
rtk mkdir -p "$HOME/scripts/hooks"
```

Expected: command exits `0`.

- [ ] **Step 2: Create validator script**

Write `~/scripts/hooks/validate-rag-frontmatter.py`:
```python
#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "id",
    "date",
    "source",
    "collection",
    "project",
    "chunk_type",
    "topic",
    "tags",
    "status",
]

ENUM_FIELDS = {
    "chunk_type": "VALID_TYPES",
    "project": "VALID_PROJECTS",
    "status": "VALID_STATUSES",
    "collection": "VALID_COLLECTIONS",
    "source": "ALLOWED_SOURCES",
}


def run_git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], text=True, stderr=subprocess.STDOUT)


def staged_summary_paths() -> list[str]:
    output = run_git(["diff", "--cached", "--name-only", "--diff-filter=ACM"])
    return [line for line in output.splitlines() if line.startswith(".claude/summaries/") and line.endswith(".md")]


def staged_file_content(path: str) -> str:
    return run_git(["show", f":{path}"])


def parse_frontmatter(content: str) -> dict[str, str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter delimiter")

    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break

    if end_index is None:
        raise ValueError("missing closing frontmatter delimiter")

    fields: dict[str, str] = {}
    for line in lines[1:end_index]:
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def load_rag_capture_constants() -> tuple[dict[str, set[str]], str | None]:
    path = Path.home() / "scripts" / "rag-capture-v2" / "rag_capture.py"
    if not path.exists():
        return {}, f"warning: {path} not found; enum validation skipped"

    spec = importlib.util.spec_from_file_location("rag_capture_constants", path)
    if spec is None or spec.loader is None:
        return {}, f"warning: cannot import {path}; enum validation skipped"

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    constants: dict[str, set[str]] = {}
    for field, constant_name in ENUM_FIELDS.items():
        value = getattr(module, constant_name, None)
        if value is not None:
            constants[field] = set(value)
    return constants, None


def validate_file(path: str, constants: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    try:
        fields = parse_frontmatter(staged_file_content(path))
    except Exception as exc:
        return [f"{path}: {exc}"]

    missing = [field for field in REQUIRED_FIELDS if field not in fields or not fields[field]]
    if missing:
        errors.append(f"{path}: missing required fields: {', '.join(missing)}")

    for field, allowed_values in constants.items():
        if field in fields and fields[field] and fields[field] not in allowed_values:
            errors.append(f"{path}: invalid {field}={fields[field]!r}; expected one of {sorted(allowed_values)}")

    return errors


def main() -> int:
    try:
        paths = staged_summary_paths()
    except subprocess.CalledProcessError as exc:
        print(exc.output, file=sys.stderr, end="")
        return 1

    if not paths:
        return 0

    constants, warning = load_rag_capture_constants()
    if warning:
        print(warning, file=sys.stderr)

    errors: list[str] = []
    for path in paths:
        errors.extend(validate_file(path, constants))

    if errors:
        print("RAG summary frontmatter validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"RAG summary frontmatter validation passed: {len(paths)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Create hook installer script**

Write `~/scripts/hooks/install-rag-frontmatter-hook.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-$(pwd)}"
REPO_ROOT="$(git -C "$TARGET_DIR" rev-parse --show-toplevel)"
HOOK_PATH="$REPO_ROOT/.git/hooks/pre-commit"
VALIDATOR="$HOME/scripts/hooks/validate-rag-frontmatter.py"

if [ ! -f "$VALIDATOR" ]; then
  echo "validator not found: $VALIDATOR" >&2
  exit 1
fi

mkdir -p "$(dirname "$HOOK_PATH")"
cat > "$HOOK_PATH" <<EOF
#!/usr/bin/env bash
set -euo pipefail
python "\$HOME/scripts/hooks/validate-rag-frontmatter.py"
EOF
chmod +x "$HOOK_PATH"
echo "installed: $HOOK_PATH"
```

- [ ] **Step 4: Make hook scripts executable**

Run:
```bash
rtk chmod +x "$HOME/scripts/hooks/validate-rag-frontmatter.py" \
  "$HOME/scripts/hooks/install-rag-frontmatter-hook.sh"
```

Expected: command exits `0`.

- [ ] **Step 5: Syntax-check validator**

Run:
```bash
rtk python -m py_compile "$HOME/scripts/hooks/validate-rag-frontmatter.py"
```

Expected: command exits `0`.

---

### Task 5: Verify Hook Behavior

**Files:**
- Install local hook in: `C:/Users/Clandesitine/source/repos/rag-gateway-mini/.git/hooks/pre-commit`
- Create and remove temporary staged file: `.claude/summaries/2099-01-01-frontmatter-hook-negative-smoke.md`

- [ ] **Step 1: Run validator with no staged summaries**

Run from `rag-gateway-mini` root:
```bash
rtk python "$HOME/scripts/hooks/validate-rag-frontmatter.py"
```

Expected: exit `0`. Output may be empty if no `.claude/summaries/*.md` files are staged.

- [ ] **Step 2: Install local hook wrapper**

Run from `rag-gateway-mini` root:
```bash
rtk bash "$HOME/scripts/hooks/install-rag-frontmatter-hook.sh"
```

Expected: prints `installed: .../.git/hooks/pre-commit`.

- [ ] **Step 3: Verify generated hook uses dynamic home path**

Run:
```bash
rtk grep -n "\$HOME/scripts/hooks/validate-rag-frontmatter.py" .git/hooks/pre-commit
```

Expected: one match. No local username appears in the generated hook.

- [ ] **Step 4: Negative smoke with missing status**

Create `.claude/summaries/2099-01-01-frontmatter-hook-negative-smoke.md` with:
```markdown
---
id: 2099-01-01-frontmatter-hook-negative-smoke-001
date: 2099-01-01
source: claude-code-cli
collection: knowledge_v2_keyfacts
project: homelab
chunk_type: debug
topic: Frontmatter hook negative smoke
tags: [homelab, smoke]
---

## CHUNK 1: Frontmatter hook negative smoke

### Context
Temporary smoke file.
### Problem
Temporary smoke file.
### Solution
Temporary smoke file.
### Key Facts
- Temporary smoke file.
- Temporary smoke file.
- Temporary smoke file.
```

Run:
```bash
rtk git add .claude/summaries/2099-01-01-frontmatter-hook-negative-smoke.md
rtk python "$HOME/scripts/hooks/validate-rag-frontmatter.py"
```

Expected: exit `1` and error includes `missing required fields: status`.

- [ ] **Step 5: Remove negative smoke file**

Run:
```bash
rtk git rm --cached .claude/summaries/2099-01-01-frontmatter-hook-negative-smoke.md
rtk rm .claude/summaries/2099-01-01-frontmatter-hook-negative-smoke.md
```

Expected: file is removed from index and working tree.

- [ ] **Step 6: Positive smoke with an existing summary**

Run:
```bash
rtk git add .claude/summaries/2026-05-07-9router-custom-model-validation.md
rtk python "$HOME/scripts/hooks/validate-rag-frontmatter.py"
rtk git restore --staged .claude/summaries/2026-05-07-9router-custom-model-validation.md
```

Expected: validator exits `0` and prints validation passed for 1 file.

---

### Task 6: Commit and Push in `rag-tools` Repo

**Files:**
- `~/scripts/rag-infra/*`
- `~/scripts/hooks/*`

- [ ] **Step 1: Check rag-tools status**

Run:
```bash
cd "$HOME/scripts" && rtk git status --short
```

Expected: new files under `rag-infra/` and `hooks/` are visible.

- [ ] **Step 2: Commit rag-tools changes**

Run:
```bash
cd "$HOME/scripts" && rtk git add rag-infra hooks && rtk git commit -m "$(cat <<'EOF'
feat: add RAG infrastructure tools and frontmatter hook

Move reusable RAG operational tooling into rag-infra and add
versioned hook scripts for validating RAG summary frontmatter
from project repositories.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: new commit created in rag-tools.

- [ ] **Step 3: Push rag-tools changes only after user approval**

Ask the user before running:
```bash
cd "$HOME/scripts" && rtk git push
```

Expected: remote rag-tools repo receives the tooling changes.

---

### Task 7: Commit `rag-gateway-mini` Cleanup

**Files:**
- Removed reusable scripts from `scripts/`
- Archived migration scripts under `scripts/archive/migrations/`
- Updated docs references
- Updated local hook design plan/spec if changed

- [ ] **Step 1: Verify no hardcoded local username exists**

Run:
```bash
rtk git grep -n -i "Clandesitine" -- "*.md" "*.json" "*.sh" "*.py" "*.txt" "*.cs" "*.yml" "*.yaml"
```

Expected: exit `1` with no output.

- [ ] **Step 2: Verify no active references to moved scripts remain**

Run:
```bash
rtk git grep -n "scripts/eval-retrieval-quality.py\|scripts/test-qdrant-retrieval.sh\|scripts/qdrant-graph.sh\|scripts/qdrant-visualize.sh\|scripts/anomaly_check.py\|scripts/snapshot_tamper_check.py" -- "*.md"
```

Expected: no active operational references; archive/history references are acceptable only if clearly historical.

- [ ] **Step 3: Check project status**

Run:
```bash
rtk git status --short
```

Expected: deletions for reusable scripts, renames for archive scripts, docs updates, and plan file.

- [ ] **Step 4: Commit project cleanup**

Run:
```bash
rtk git add scripts docs .claude/settings.json CLAUDE.md README.md
rtk git commit -m "$(cat <<'EOF'
refactor: centralize RAG tools and archive migrations

Move reusable RAG infrastructure scripts to the separate rag-tools
repo under ~/scripts/rag-infra, archive completed one-time migration
scripts, and update documentation references to the new structure.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: cleanup commit created in rag-gateway-mini.

---

## Self-Review

- Spec coverage: plan covers user corrections: `rag-infra/` is used instead of `rag-tools/`; one-time migrations are archived, not deleted; frontmatter hook scripts live under `~/scripts/hooks/`; docs references are updated; local username is checked.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type/path consistency: reusable tool folder is consistently `~/scripts/rag-infra/`; hook folder is consistently `~/scripts/hooks/`; archive folder is consistently `scripts/archive/migrations/`.
