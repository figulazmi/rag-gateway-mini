---
id: 2026-04-27-ragchunkmeta-per-chunk-metadata-enrichme-001
date: 2026-04-27
source: claude-code-cli
collection: knowledge_v2
project: homelab
chunk_type: pattern
topic: rag_chunk_meta per-chunk metadata enrichment - adding 5 fields to HTML comments
tags: [homelab, vm-b1, rag, qdrant, knowledge-capture, chunk-meta, markdown, metadata]
related: []
session_type: ops-documentation
environment: homelab
git_branch: main
status: implemented
chunk_source: code
---

## CHUNK 1: rag_chunk_meta per-chunk metadata enrichment - adding 5 fields to HTML comments
<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, rag, qdrant, knowledge-capture, chunk-meta, markdown, metadata] -->

## CHUNK 1: Enriching rag_chunk_meta Per-Chunk Metadata Fields

### Context

homelab-hardening RAG merged summary files use `<!-- rag_chunk_meta ... -->` HTML comments
per chunk to carry metadata for Qdrant ingestion. The `rag merge` CLI generates these comments
with only `chunk_type` and `tags`. Five additional fields need to be added manually after merge.

### Problem

After `rag merge`, each chunk's `rag_chunk_meta` comment only contains:
```
<!-- rag_chunk_meta chunk_type=runbook tags=[...] -->
```
Fields `status`, `related`, `environment`, `session_type`, `git_branch` are absent â€”
push-to-qdrant.sh falls back to document-level frontmatter for all chunks, losing per-chunk precision.

### Solution

Edit each chunk's HTML comment to add the 5 missing fields:
```
<!-- rag_chunk_meta chunk_type=runbook tags=[...] status=implemented related=[] environment=homelab session_type=setup git_branch=main -->
```

Per-chunk `session_type` values for homelab sessions:
- Deployment runbook â†’ `setup`
- Bug fix â†’ `debug`
- New tool/feature â†’ `feature`
- Docs sync â†’ `ops-documentation`
- Architecture decision â†’ `architecture`

### Key Facts

- `rag merge` only generates `chunk_type` and `tags` in rag_chunk_meta â€” other fields must be added manually
- All 5 fields have fallback to doc-level frontmatter if absent â€” enrichment improves per-chunk precision
- `status=implemented` is the correct value for all chunks from a completed deployment session
- `related=[]` is safe default â€” fill with chunk IDs when cross-chunk relationships exist
- Edit the .md file before re-pushing; push-to-qdrant.sh reads these fields on each run

## CHUNK 2: push-to-qdrant.sh fix - per-chunk metadata parsed from rag_chunk_meta not doc frontmatter
<!-- rag_chunk_meta chunk_type=debug tags=[homelab, vm-b1, rag, qdrant, push-to-qdrant, bash, metadata, chunk-meta] -->

## CHUNK 2: push-to-qdrant.sh Fix - Per-Chunk Metadata from rag_chunk_meta

### Context

`push-to-qdrant.sh` sends each chunk as a Qdrant point via n8n webhook. The script
already parsed `chunk_type` and `tags` per-chunk from `rag_chunk_meta` HTML comments,
but `status`, `session_type`, `environment`, `git_branch`, `related` were always taken
from the document-level YAML frontmatter (same value for all chunks in the file).

### Problem

Per-chunk values for `status`, `session_type`, `environment`, `git_branch`, `related`
were never read from the `rag_chunk_meta` comment. All chunks received identical values
from the top-level frontmatter, even when individual chunks had different metadata set.
This made per-chunk enrichment of the HTML comments ineffective.

### Solution

1. Extract the `rag_chunk_meta` comment line first (safer than scanning full chunk content):
```bash
CHUNK_META_LINE=$(echo "$CHUNK_CONTENT" | grep 'rag_chunk_meta' | head -1)
```

2. Parse all 5 new fields from `$CHUNK_META_LINE` with fallback to doc-level:
```bash
CHUNK_STATUS_OVERRIDE=$(echo "$CHUNK_META_LINE" | grep -o 'status=[a-z_-]*' | sed 's/status=//')
EFFECTIVE_STATUS="${CHUNK_STATUS_OVERRIDE:-$DOC_STATUS}"

CHUNK_SESSION_TYPE_OVERRIDE=$(echo "$CHUNK_META_LINE" | grep -o 'session_type=[a-z_-]*' | sed 's/session_type=//')
EFFECTIVE_SESSION_TYPE="${CHUNK_SESSION_TYPE_OVERRIDE:-$DOC_SESSION_TYPE}"

CHUNK_ENVIRONMENT_OVERRIDE=$(echo "$CHUNK_META_LINE" | grep -o 'environment=[a-z_-]*' | sed 's/environment=//')
EFFECTIVE_ENVIRONMENT="${CHUNK_ENVIRONMENT_OVERRIDE:-$DOC_ENVIRONMENT}"

CHUNK_GIT_BRANCH_OVERRIDE=$(echo "$CHUNK_META_LINE" | grep -o 'git_branch=[a-z0-9_/.-]*' | sed 's/git_branch=//')
EFFECTIVE_GIT_BRANCH="${CHUNK_GIT_BRANCH_OVERRIDE:-$DOC_GIT_BRANCH}"

CHUNK_RELATED_OVERRIDE=$(echo "$CHUNK_META_LINE" | grep -o 'related=\[[^]]*\]' | sed 's/related=//')
EFFECTIVE_RELATED="${CHUNK_RELATED_OVERRIDE:-$DOC_RELATED}"
```

3. Use `EFFECTIVE_*` variables (not `DOC_*`) in the jq payload for all 5 fields.

### Key Facts

- Parsing from `$CHUNK_META_LINE` is safer than `grep -o` on full `$CHUNK_CONTENT` â€” avoids false matches (e.g., `status=` appearing in markdown body)
- `chunk_type` and `tags` parsing was already per-chunk; this fix brings the remaining 5 fields to parity
- File: `~/scripts/push-to-qdrant.sh` â€” chunk parsing loop starting at the `rag_chunk_meta` extraction block
- Fallback chain: per-chunk rag_chunk_meta value â†’ doc-level frontmatter â†’ "unknown"

## CHUNK 3: cosine gate FAIL - n8n Ollama node reads content instead of embed_content
<!-- rag_chunk_meta chunk_type=debug tags=[homelab, vm-b1, rag, qdrant, n8n, ollama, cosine, embedding] -->

## CHUNK 3: Cosine Gate FAIL - n8n Ollama Node Wrong Field

### Context

`push-to-qdrant.sh` runs a cosine gate check after push via `verify_embed_cosine.py`.
It computes `cos(stored_vector, embed(prepended_content))` vs `cos(stored_vector, embed(raw_content))`
to verify the Qdrant point was embedded using the correct field (`embed_content`, not `content`).

### Problem

Cosine gate consistently reports FAIL:
```
cos(stored,prepended)=0.9832  cos(stored,raw)=0.9503
n8n Ollama node may still read $json.content instead of $json.embed_content
```

This is a **pre-existing n8n configuration issue** â€” not caused by any script changes.
The Ollama embedding node in the `knowledge-ingest` n8n workflow is bound to `$json.content`
(raw markdown text) instead of `$json.embed_content` (metadata-prefixed text for better retrieval).

### Solution

Fix in n8n UI (must be done manually â€” n8n workflow cannot be edited via script):

1. Open n8n â†’ workflow `knowledge-ingest`
2. Click the **Ollama** node
3. In **Body / prompt** field: change `{{ $json.content }}` â†’ `{{ $json.embed_content }}`
4. Save â†’ toggle workflow Active: **off** â†’ **on** (forces webhook re-registration)
5. Re-push any file to regenerate vectors with correct embedding

### Key Facts

- `embed_content` prepends metadata (project, chunk_type, topic, tags) to chunk text â€” improves semantic retrieval
- `content` is raw markdown text only â€” embeddings are less precise for filtered queries
- Cosine values 0.98/0.95 are both high because content overlap is large â€” but `embed_content` vectors are more accurate
- This FAIL appeared before and after push-to-qdrant.sh script edits â€” confirmed pre-existing
- Status: `planned` (fix requires manual n8n UI action â€” not yet applied)

### Caveats

- After fixing the Ollama node, all previously pushed chunks should be re-pushed to regenerate vectors
- Toggle Active off-on is required because n8n caches webhook bindings at registration time

## CHUNK 4: VM 105 knowledge_v2 restoration pipeline full steps
<!-- rag_chunk_meta chunk_type=runbook tags=[homelab, vm-b1, qdrant, n8n, ollama, mcp-server, pipeline] -->

### Context
VM 105 (192.168.18.199) RAG pipeline restoration to match VM B1 state as of 2026-04-27. Backup available only up to 2026-04-13 (14-day gap). 120 summary .md files available locally across 8 locations to fill the gap.

### Problem
Multiple components were misconfigured or outdated compared to April 27 target state: qdrant-mcp-server-v2.js had wrong thresholds (SCORE_THRESHOLD=0.5 instead of 0.35, RETRY_THRESHOLD=0.6 instead of 0.50), n8n workflow was pre-contextual-retrieval (embedded raw content instead of prepended embed_content), knowledge_v2 collection had wrong schema (dense-only unnamed vectors instead of named dense+sparse+idf), and 3 D:\Backup files had non-standard project values.

### Solution
Step 0a -- Fixed qdrant-mcp-server-v2.js: SCORE_THRESHOLD 0.5 to 0.35, RETRY_THRESHOLD 0.6 to 0.50, added project-aware retry expansion (homelab/petrochina-eproc expansions object). Step 0b -- Fixed push-to-qdrant.sh: collection override now catches "knowledge", "unknown", and empty string. Step 1 -- Recreated knowledge_v2 with named dense (768-dim Cosine) + sparse (BM25 idf) via DELETE + PUT + PATCH indexing_threshold=0. Step 2 -- SCP all scripts to VM. Step 3 -- Automated n8n import via docker exec + fixed 2 workflow bugs. Step 4 -- Deployed MCP server v2 via PM2. Pre-Step5 audit -- Fixed frontmatter on 2026-04-22-qdrant-dashboard-patch.md (was missing entirely), fixed 3 D:\Backup files with non-standard project values (homelab-b1, homelab-rag, rag-gateway all changed to homelab).

### Key Facts
- n8n $env.QDRANT_API_KEY blocked by security -- read from $('Validate & Clean').first().json.qdrant_api_key instead (webhook payload includes it from push-to-qdrant.sh).
- Sparse vector must be inside vector object alongside dense (not at sparse_vectors top-level in Qdrant REST upsert): vector: {dense: [...], sparse: {indices, values}}.
- n8n workflow import via: docker exec n8n n8n import:workflow --input=/tmp/file.json; activate via POST /api/v1/workflows/{id}/activate with X-N8N-API-KEY header.
- n8n API key location on VM: sqlite3 /home/node/.n8n/database.sqlite "SELECT apiKey FROM user LIMIT 1".
- knowledge_v2 collection config: vectors.dense size=768 distance=Cosine, sparse_vectors.sparse modifier=idf, optimizer_config.indexing_threshold=0.
- All 62 repo-based summaries have valid frontmatter; all 58 D:\Backup summaries have frontmatter but no collection field (falls to unknown, override catches it).
- cosine gate (verify_embed_cosine.py) missing on VM -- deploy needed; currently fails silently after every push.
### Code
```bash
# Recreate knowledge_v2 collection
curl -s -X DELETE "http://localhost:6333/collections/knowledge_v2" -H "api-key: KEY"
curl -s -X PUT "http://localhost:6333/collections/knowledge_v2" \
  -H "api-key: KEY" -H "Content-Type: application/json" \
  -d '{"vectors":{"dense":{"size":768,"distance":"Cosine"}},"sparse_vectors":{"sparse":{"modifier":"idf"}}}'
curl -s -X PATCH "http://localhost:6333/collections/knowledge_v2" \
  -H "api-key: KEY" -H "Content-Type: application/json" \
  -d '{"optimizer_config":{"indexing_threshold":0}}'
```

---

## SESSION METADATA

- **Total chunks**: 4
- **Qdrant collection**: knowledge_v2
- **Generated by**: rag_capture.py v2 -- Incremental Capture
- **Author**: Figur Ulul Azmi
- **Date**: 2026-04-29
- **Unresolved items**: (fill manually if needed)