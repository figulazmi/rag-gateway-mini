# RAG Summary Frontmatter Pre-commit Hook Design

## Goal

Add a versioned pre-commit validation path for `.claude/summaries/*.md` files so malformed RAG summary frontmatter is caught before commit.

## Scope

The hook runs during `git commit` and checks only staged files matching `.claude/summaries/*.md`. If no matching files are staged, it exits successfully without output.

For each staged summary file, the validator must:

1. Parse YAML-style frontmatter delimited by leading `---` and closing `---`.
2. Fail if frontmatter is missing or malformed.
3. Fail if required summary metadata fields are missing.
4. Print concise per-file errors and exit non-zero when validation fails.

Content validation is out of scope for this hook. `rag_capture.py` already validates chunk body quality during `rag add`, and merged summary files may contain multiple chunks plus session metadata, which does not map cleanly to single-chunk `validate_content()` rules.

## Required Fields

The hook validates that each summary frontmatter contains these fields:

- `id`
- `date`
- `source`
- `collection`
- `project`
- `chunk_type`
- `topic`
- `tags`
- `status`

These fields match the metadata used by the current RAG capture and Qdrant push workflow.

## Files

All versioned hook tooling lives in the separate `rag-tools` repository at `~/scripts` (Windows: `%USERPROFILE%\scripts`, Unix: `$HOME/scripts`). No reusable hook scripts are added to this `rag-gateway-mini` repository.

### `~/scripts/hooks/validate-rag-frontmatter.py`

Versioned Python validator in the `rag-tools` repository. Responsibilities:

- Discover staged `.claude/summaries/*.md` files using `git diff --cached --name-only --diff-filter=ACM`.
- Read staged content with `git show :<path>` so validation matches what will be committed, not unstaged working-tree content.
- Parse frontmatter with lightweight inline regex — no YAML library dependency needed.
- Import `rag_capture.py` from `~/scripts/rag-capture-v2/rag_capture.py` using `importlib.util` to reuse its validation enum constants: `VALID_TYPES`, `VALID_PROJECTS`, `VALID_STATUSES`, `VALID_COLLECTIONS`, `ALLOWED_SOURCES`.
- Validate required fields are present AND that enumerated fields (`chunk_type`, `project`, `status`, `collection`, `source`) carry values that match the canonical constants.
- If `rag_capture.py` is not found, warn and fall back to presence-only validation.
- Exit `1` if any file fails validation.

The script should not modify files.

### `~/scripts/hooks/install-rag-frontmatter-hook.sh`

Versioned installer in the `rag-tools` repository. Responsibilities:

- Accept a target repository path, defaulting to the current working directory.
- Resolve the target repository root with `git rev-parse --show-toplevel`.
- Detect the user's home directory dynamically using `$HOME` (Unix) or `%USERPROFILE%` (Windows).
- Create or overwrite the target repository's `.git/hooks/pre-commit` with a small wrapper that calls `~/scripts/hooks/validate-rag-frontmatter.py` using the resolved home path.
- Mark the local hook executable.

The generated `.git/hooks/pre-commit` file remains unversioned in the target project repository.

## Generated Local Hook

The installer writes this local hook to the target repository's `.git/hooks/pre-commit`:

```bash
#!/usr/bin/env bash
set -euo pipefail
python "$HOME/scripts/hooks/validate-rag-frontmatter.py"
```

## Error Handling

- Missing or malformed frontmatter: fail with file path and reason.
- Missing required fields: fail with file path and comma-separated missing field list.
- Missing `rag_capture.py`: warn only, then continue with presence-only field validation (no enum-value checks).
- Git command failure: fail closed, because hook validation cannot determine the staged state.

## Verification

Manual verification after implementation:

1. From the `rag-tools` repo, run the validator directly against `rag-gateway-mini` with no staged summaries and confirm exit `0`.
2. In `rag-gateway-mini`, stage a valid `.claude/summaries/*.md` file and confirm exit `0`.
3. In `rag-gateway-mini`, stage a temporary malformed summary missing `status` and confirm exit `1` with a clear error.
4. Run `~/scripts/hooks/install-rag-frontmatter-hook.sh` from the `rag-gateway-mini` directory and confirm `.git/hooks/pre-commit` calls the versioned validator via `$HOME/scripts/hooks/validate-rag-frontmatter.py`.
