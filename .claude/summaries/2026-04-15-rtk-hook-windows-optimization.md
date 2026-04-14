---
id: 2026-04-15-claude-code-rtk-auto-prefix-pretooluse-h-001
date: 2026-04-15
source: claude-code-cli
project: homelab
chunk_type: runbook
topic: Claude Code RTK Auto Prefix PreToolUse Hook Windows
tags: [homelab, vm-b1, rtk, claude-code, hook, pretooluse, windows, bash]
related: []
session_type: 
environment: homelab
git_branch: 
status: implemented
chunk_source: code
---

## CHUNK 1: Claude Code RTK Auto Prefix PreToolUse Hook Windows

### Context
On Windows, `rtk init -g` (Rust Token Killer) cannot install its native Claude
Code hook because hook-based mode requires Unix. Without a hook, Claude must
remember to prefix every Bash command with `rtk`, which proves unreliable and
leaves `rtk gain` history mostly empty. A custom PreToolUse hook closes that
gap by rewriting Bash tool inputs before execution.

### Problem
Claude Code on Windows has no automatic mechanism to force the `rtk` prefix on
Bash commands. Disciplined prefixing fails in practice, so token savings stay
far below RTK's documented 60 to 90 percent range and history tracking is
incomplete.

### Solution
Install a custom PreToolUse hook written in pure Python stdlib at
`~/.claude/hooks/rtk-prefix.py` and wire it into `~/.claude/settings.json`
under `hooks.PreToolUse` with `matcher: "Bash"`. The hook reads the PreToolUse
JSON payload on stdin, splits compound commands on `&&`, `||`, `;` while
respecting single and double quotes plus heredoc bodies, and prefixes each
simple command with `rtk` unless the first token is a shell builtin or
keyword, an env assignment like `FOO=bar`, a subshell opener, already `rtk`,
or the escape sentinel `NORTK`. It emits `hookSpecificOutput.updatedInput`
with the rewritten command and always exits 0 so Bash is never blocked.

### Key Facts
- Claude Code PreToolUse hooks rewrite tool input via `hookSpecificOutput.updatedInput` with `permissionDecision: "allow"` and exit code 0
- RTK hook-based mode is Unix only. On Windows `rtk init -g` falls back to CLAUDE.md injection which relies on model discipline
- Pipes must not be treated as compound separators. Prefix only the first command in a pipe so rtk filters output then pipes downstream normally
- Heredoc bodies after `<<WORD` or `<<'WORD'` must be skipped during separator scanning to avoid splitting on `;` or `&&` inside the body
- Shell builtins and keywords like `cd`, `export`, `if`, `for`, `(`, `{` must not be rtk-wrapped to preserve shell semantics
- Env assignment pattern `VAR=value cmd` should be skipped to avoid ambiguous semantics when inserting rtk between assignment and command
- Escape hatch: prefixing any Bash command with `NORTK ` strips the sentinel and runs without rtk, useful when debugging rtk itself
- Hook activates only on new Claude Code sessions. `/clear` or restart required after editing `settings.json`
- Set env `RTK_HOOK_DEBUG=1` to append rewrite decisions to `~/.claude/hooks/rtk-prefix.log` for troubleshooting
- settings.json command string on Windows must escape backslashes: `python "C:\Users\Clandesitine\.claude\hooks\rtk-prefix.py"`

### Code
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "python \"C:\Users\Clandesitine\.claude\hooks\rtk-prefix.py\"" }
        ]
      }
    ]
  }
}
```

## CHUNK 2: RTK Hook Windows Warning Suppression and Nested Substitution Fix

### Context
The custom PreToolUse hook at ~/.claude/hooks/rtk-prefix.py auto-prefixes Bash
commands with rtk on Windows where RTK 0.36.0 refuses to install its native
hook. Two follow-up improvements were applied after the initial runbook.

### Problem
Two issues surfaced after the initial hook install. First, `rtk gain` kept
printing `[warn] No hook installed run rtk init -g for automatic token
savings` because RTK detects its own signature in settings.json, and the
custom hook uses a different signature. Running `rtk init -g` or `rtk init -g
--auto-patch` still fails on Windows with "Hook install requires Unix" despite
`rtk init --show` suggesting otherwise. Second, the hook rewriter wrongly
split commands of the form `out=$(python -c "import json,sys;print(x)")` on
the semicolon inside the Python string because the inner double quote closed
the outer quote state, leaving `print(...)` treated as a new command and
rtk-prefixed, producing SyntaxError.

### Solution
Warning suppression: define a bash function in ~/.bashrc that wraps
`command rtk` and pipes stderr through `grep -vF "No hook installed"`, then
`export -f rtk` so Claude Code Bash tool inherits it. Preserves every other
stderr byte. Nested substitution fix: add a `sub_stack` list in _split_compound
that saves (in_single, in_double) when entering `$(` and restores on matching
`)`. Add a separate `in_backtick` flag for backticks. Inside any substitution
(sub_stack non-empty or in_backtick true) suppress top-level separator
detection. Skip list extended with which, type, command, hash, help, test,
bracket, double-bracket to stop diagnostic builtins from appearing as
`rtk fallback:` rows in history.

### Key Facts
- RTK 0.36.0 on Windows native rejects hook install even though `rtk init --show` suggests `rtk init -g --auto-patch`
- `rtk init --show` reports "settings.json: exists but RTK hook not configured" whenever RTK own signature is absent, regardless of whether a Bash PreToolUse hook exists
- Bash function shadows only for interactive shells that source .bashrc; use `export -f rtk` so non-interactive subshells inherit it
- `command rtk` inside the function avoids recursion into the function itself
- `grep -vF` (fixed string, inverted) is safer than regex for a known literal warning string
- Inner quotes inside `$(...)` must be tracked in a fresh frame; otherwise an inner double-quote string accidentally toggles the outer quote state
- Regression test suite at ~/.claude/hooks/test-rtk-prefix.py runs 27 cases covering simple, compound, quoted, heredoc, nested substitution, skip list, sentinel
- Run the test suite via `python ~/.claude/hooks/test-rtk-prefix.py` after any hook change
- Claude Code hot-reloads ~/.claude/settings.json; no /clear required to pick up new PreToolUse matcher
- Verify with `bash -ic 'rtk gain'` and confirm the warning line is absent

### Code
```bash
rtk() {
  command rtk "$@" 2> >(grep -vF "No hook installed" >&2)
}
export -f rtk
```

---

## SESSION METADATA

- **Total chunks**: 2
- **Qdrant collection**: knowledge_v2
- **Generated by**: rag_capture.py v2 — Incremental Capture
- **Author**: Figur Ulul Azmi
- **Date**: 2026-04-15
- **Unresolved items**: (fill manually if needed)