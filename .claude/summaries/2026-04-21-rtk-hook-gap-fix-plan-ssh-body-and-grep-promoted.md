---
id: 2026-04-21-rtk-hook-gap-fix-plan-ssh-body-and-grep-promoted
date: 2026-04-21
source: claude-code-cli
collection: knowledge_v2
project: homelab
chunk_type: checkpoint
topic: RTK hook gap fix plan SSH body and Grep redirect
tags: [homelab, vm-b1]
related: []
session_type: checkpoint
environment: homelab
git_branch: 
status: solved
chunk_source: code
supersedes: 
superseded_by: 
hypothesis: SSH body commands unreachable by PreToolUse hook; Grep deny redirect loses params; both fixable
next_step: implement rtk-ssh-warn.py PostToolUse hook + rewrite rtk-enforce.py to use updatedInput instead of deny
blocking_question: 
token_trigger: 85%
session_number: 1
files_modified: []
decisions_made: [fca30f9 feat: add multi-device installation support with network auto-detection for RAG pipeline; 72f54f3 Add installation script and Makefile for RAG Gateway Mini setup; a915ab1 feat: add SDL stale token infinite loop fix and enhance TokenService for session management; c6c0579 fix: add chunk_type/status to push payload, fix MCP thresholds and prefetch; bde13f8 fix: n8n chunk_type mapping and expand ALLOWED_STATUS]
parent_id: 2026-04-21-rtk-hook-gap-fix-plan-ssh-body-and-grep-001

## CHECKPOINT: RTK hook gap fix plan SSH body and Grep redirect

### Problem
RTK enforcement on all projects has two remaining gaps after rtk-prefix.py and rtk-enforce.py were installed:
1. SSH body commands: hook rewrites outer `ssh user@vm 'cmd'` to `rtk ssh ...` (passthrough) but inner body string is never rewritten. VM B1 commands like `ssh figulazmi@192.168.18.199 'cat file'` run raw without RTK on the remote.
2. Grep tool deny redirect is incomplete: rtk-enforce.py blocks Grep and emits a simplified `rtk grep 'pattern' path` command, but loses output_mode, -A/-B/-C, multiline, head_limit, offset, -n parameters. Claude must manually reconstruct -- still relies on model discipline.

### Progress
- Audit complete. rtk-prefix.py 27/27 tests pass. rtk-enforce.py wired for Grep + Glob.
- Confirmed global hooks apply to all projects via ~/.claude/settings.json.
- token-monitor and dotnet-skills CLAUDE.md have no RTK section (low priority, hooks still apply globally).
- Two fixes identified and scoped.

### Key Facts
- Fix 1 (SSH warn): Add PostToolUse Bash hook. File to create: ~/.claude/hooks/rtk-ssh-warn.py. Scans if command contains "ssh" and output line count exceeds threshold, prints stderr warning. Wire in ~/.claude/settings.json PostToolUse with matcher "Bash".
- Fix 2 (Grep rewrite): Change rtk-enforce.py from deny+denyReason to updatedInput rewrite -- construct full bash command preserving all Grep tool params (output_mode, -A/-B/-C, multiline, head_limit). File: ~/.claude/hooks/rtk-enforce.py
- settings.json PostToolUse section already has Write matcher -- add Bash matcher alongside it for SSH warn
