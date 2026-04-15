---
id: 2026-04-15-n8n-ingest-workflow-status-field-whiteli-002
date: 2026-04-15
source: claude-code-cli
project: homelab
chunk_type: feature
topic: n8n Ingest Workflow Status Field Whitelist
tags: [homelab, vm-b1, n8n, qdrant, knowledge-v2, status-field, workflow]
related: []
session_type: 
environment: homelab
git_branch: 
status: implemented
chunk_source: code
---

## CHUNK 2: n8n Ingest Workflow Status Field Whitelist

### Context
The n8n workflow knowledge_v2 ingests chunks from rag merge push into Qdrant collection knowledge_v2 on VM B1. MCP server qdrant-mcp-server-v2 filters results by payload.status equals implemented by default. Before this change the workflow had no status field in the upserted payload, so MCP v2 silently dropped every chunk from default search.

### Problem
The Prepare Qdrant Point code node built the upsert payload with string_id, topic, tags, chunk_type but omitted status entirely. Any point written through webhook knowledge-ingest was invisible to default MCP queries. The fix also had to be robust against bad input since webhook body is untrusted.

### Solution
Added ALLOWED_STATUS array containing implemented, planned, deprecated in the Prepare Qdrant Point node. Raw input from payload.status is lowercased, trimmed, and checked against the whitelist; anything outside falls back to implemented. Sanitized value is injected into payload.status of the upsert body and also propagated to Build Response node output so callers can confirm via the webhook response without a separate Qdrant scroll.

### Key Facts
- Whitelist is implemented, planned, deprecated with implemented as fallback for missing or unrecognized input
- Sanitization is (payload.status or empty string).toString().trim().toLowerCase() before ALLOWED_STATUS.includes check
- Webhook response adds payload_status field so smoke tests can assert without querying Qdrant directly
- Workflow export at scripts/n8n-workflows/ingest-knowledge-v2.json in rag-gateway-mini repo with api-key replaced by placeholder
- Webhook contract unchanged: POST http://host:5678/webhook/knowledge-ingest, optional status field in body

## CHUNK 2: Qdrant Backfill Missing Payload Field Idempotent

### Context
After adding a new payload field to the n8n ingest workflow, legacy points written before the change still lack the field. Qdrant collection knowledge_v2 had 94 of 171 points without payload.status, and MCP v2 default filter status equals implemented would silently hide all of them.

### Problem
A naive bulk update risks overwriting correctly tagged chunks. Five points already had status equals planned (SDL Phase 3 plan series, External Brain audit plan, SDL Phase 1 plan). Backfill must skip these and only touch the truly missing points.

### Solution
Use the Qdrant set_payload endpoint with an is_empty filter on the missing key. The filter auto-excludes both already-backfilled points and points that already have a different value. Before running, inspect via scroll with the same filter, grouped by session_type or chunk_type, to confirm no design-only chunks are among the missing. After running, verify with two counts: is_empty status should be zero and match value implemented should equal total minus existing planned.

### Key Facts
- Endpoint is POST collections/NAME/points/payload with body containing payload object and filter object
- Filter must have must array with is_empty object keyed on the missing field
- Set_payload only adds or updates named fields, never removes other payload keys
- Is_empty filter is idempotent so re-running the same request is safe
- Pre-backfill inspection uses points/scroll with with_payload list limited to classification fields for fast grouping
- Post-backfill verification uses points/count with exact true on both is_empty and match filters

## CHUNK 3: RTK Cannot Exec Bash Shebang Scripts on Windows

### Context
The rag CLI is installed at C:/Users/USER/.local/bin/rag as a small bash shebang wrapper that execs python against rag_capture.py. Under global CLAUDE.md rules every shell command must be prefixed with rtk. Running rtk rag add inside git-bash on Windows fails with exit code 127 and the message Binary rag not found on PATH, even though rtk which rag resolves to the correct path.

### Problem
RTK on Windows is a native exe that does its own PATH resolution and CreateProcess-style exec. It can locate the wrapper file by PATH lookup but cannot follow a POSIX shebang line to launch python. The fallback path inside rtk also fails because CreateProcess on a text file with no .exe or .cmd extension returns a not-found error rather than inspecting the first line.

### Solution
Bypass the wrapper and invoke the underlying python script directly under rtk. Use rtk python followed by the absolute path to rag_capture.py plus the original args. RTK passes through python invocations unchanged so token filtering still applies and the global prefix rule is honored. The same workaround applies to any shebang wrapper authored in bash and placed on PATH.

### Key Facts
- Rtk can resolve the shebang wrapper via PATH lookup but cannot exec it because Windows CreateProcess does not parse POSIX shebang
- Symptom is exit 127 with both Binary not found on PATH and rtk program not found in the same message
- Workaround pattern is rtk python ABSOLUTE_PATH_TO_SCRIPT original_args, which runs fine because python.exe is a real native executable
- Applies to any bash-shebang wrapper, not only rag. Similar fixes needed for pip-installed CLIs whose shim is a bash script
- Rtk which succeeds because which only does PATH lookup and stat, no exec, so it does not hit the shebang problem

## CHUNK 4: n8n Workflow Export Credential Scrub Placeholder

### Context
Exported n8n workflow JSON destined for a public GitHub repo must not carry literal credentials. In the ingest-knowledge-v2 workflow the node Qdrant Upsert Point holds an HTTP header api-key whose value is the real Qdrant token. A prior incident already scrubbed six other files in the same repo by replacing literals with env-var reads; the workflow JSON needs a different approach because an n8n import consumes the JSON directly without a shell env.

### Problem
Env-var substitution does not work for n8n workflow JSON because n8n reads the JSON as-is on import. The scrub must survive git commit yet allow a human to restore the real key after import, ideally without altering the node shape so typeVersion remains stable and diff stays small.

### Solution
Replace the credential literal with the placeholder string wrapped in angle brackets, for example QDRANT_API_KEY in angle brackets. Keep the surrounding node parameters and typeVersion intact. Ship a sibling README in the same folder that documents the replace-on-import step and links back to the past leak incident so future contributors have context. Grep for the literal hex before commit to prove the working tree is clean.

### Key Facts
- Placeholder value in the JSON is a plain string inside angle brackets, not an n8n expression, so import does not attempt to evaluate it
- Node shape and typeVersion stay unchanged versus using genericCredentialType, which means diff is one line and schema migrations are unaffected
- Pre-commit verification is a grep for the literal hex across the repo scripts folder, expecting zero matches
- Sibling README at scripts/n8n-workflows/README.md documents the import procedure and the security policy
- Works for any n8n header-parameter credential, not only Qdrant api-key

---

## SESSION METADATA

- **Total chunks**: 4
- **Qdrant collection**: knowledge_v2
- **Generated by**: rag_capture.py v2 — Incremental Capture
- **Author**: Figur Ulul Azmi
- **Date**: 2026-04-15
- **Unresolved items**: (fill manually if needed)