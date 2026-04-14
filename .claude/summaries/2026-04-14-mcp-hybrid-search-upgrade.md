---
id: 2026-04-14-mcp-hybrid-search-upgrade
date: 2026-04-14
source: claude-code-cli
project: homelab
chunk_type: feature
topic: MCP Server Upgrade to Hybrid Search with knowledge_v2 Collection
tags: [mcp, qdrant, hybrid-search, knowledge-v2, djb2, rrf, homelab, implemented]
related: [rag-gateway-hybrid-search, djb2-bm25-sparse-tokenizer]
session_type: feature
environment: homelab
git_branch: main
status: implemented
chunk_source: code
---

## CHUNK 1: MCP Server Collection Switch From knowledge to knowledge_v2

### Context

The `qdrant-knowledge` MCP tool (`mcp__qdrant-knowledge__search_knowledge`) on VM B1
serves as the RAG retrieval layer for Claude Code sessions. It was previously consuming
the `knowledge` collection (dense-only, unnamed vector, `/points/search` endpoint).
The `knowledge_v2` collection was already populated with 150 points using hybrid search
(named dense 768-dim + sparse BM25 djb2) via `migrate-to-hybrid.py`.

### Requirements

- Switch MCP server to target `knowledge_v2` instead of `knowledge`.
- Implement hybrid search (dense + sparse RRF) at query time to match index-time vectors.
- Sparse vector algorithm must match index-time djb2 hash exactly (same as `migrate-to-hybrid.py` and n8n JS node).
- Preserve all existing logic: RAG-FIRST enforcement, score thresholds, retry logic, NOT FOUND gate.

### Architecture Decision

Use client-side djb2 hash in the MCP server JS for sparse vector generation, identical to
the Python implementation in `migrate-to-hybrid.py`. This is required because `knowledge_v2`
was indexed using client-side djb2 (not Qdrant server-side BM25 model inference). Using
the wrong tokenizer at query time would produce mismatched sparse indices and degrade retrieval.
Hybrid fusion uses Qdrant RRF (Reciprocal Rank Fusion) via the `/points/query` endpoint with
two prefetch legs: dense (limit * 4) and sparse (limit * 4), fused server-side.

### Implementation

File updated: `/opt/mcp-servers/qdrant-knowledge/qdrant-mcp-server.js` on VM B1.

Key changes from v1.0.0 to v2.0.0:
- `COLLECTION` constant changed from `"knowledge"` to `"knowledge_v2"`.
- Added `djb2Sparse(text)` function: tokenize lowercase alphanumeric, hash with djb2, return `{ indices, values }`.
- `searchQdrant()` function now uses `/collections/${COLLECTION}/points/query` (hybrid) instead of `/points/search` (dense-only).
- Request body uses two `prefetch` legs with `using: "dense"` and `using: "sparse"`, fused with `{ fusion: "rrf" }`.
- Filters applied per-leg inside each prefetch entry.
- `searchMode: "hybrid-rrf"` added to log events for observability.

### Key Facts

- `knowledge_v2` schema: dense vector named `"dense"` (768-dim, Cosine) + sparse vector named `"sparse"` (IDF modifier).
- Sparse vectors in `knowledge_v2` were built using client-side djb2 hash, NOT Qdrant server-side BM25 model.
- djb2 algorithm: `h = 5381; for each char: h = (((h << 5) + h) + charCode) & 0x7FFFFFFF` — must match exactly.
- Hybrid query endpoint is `/collections/{name}/points/query` with `prefetch` array + `{ fusion: "rrf" }`.
- MCP process is spawned per-connection via `claude-mcp-connect.ps1` — no manual restart needed after file update.
- Backup of original file saved at `~/qdrant-mcp-server.js.bak` on VM B1.
- Local copy of new server saved at `scripts/qdrant-mcp-server-v2.js` in repo.

### Code / Commands

```javascript
// djb2 sparse vector generation — must match migrate-to-hybrid.py exactly
function djb2Sparse(text) {
  const tokens = text.toLowerCase().match(/[a-z0-9]+/g) || [];
  const tf = {};
  for (const token of tokens) {
    let h = 5381;
    for (const ch of token) {
      h = (((h << 5) + h) + ch.charCodeAt(0)) & 0x7FFFFFFF;
    }
    tf[h] = (tf[h] || 0) + 1;
  }
  const indices = Object.keys(tf).map(Number);
  const values = indices.map(i => tf[i]);
  return { indices, values };
}

// Hybrid search body
const body = {
  prefetch: [
    { query: denseVector, using: "dense", limit: limit * 4, filter: filterClause },
    { query: sparseVector, using: "sparse", limit: limit * 4, filter: filterClause },
  ],
  query: { fusion: "rrf" },
  limit,
  with_payload: true,
};
```

### Lessons Learned

- Always inspect the actual point vectors in Qdrant (via scroll with `with_vectors: true`) to determine
  which sparse tokenizer was used at index time before implementing query-time sparse generation.
- The djb2 hash produces large integer indices (e.g., 19522071, 52308031) — visually identifiable
  as client-side hashes vs. Qdrant BM25 model output.
- MCP tool schema is deferred — `ToolSearch` with `select:mcp__qdrant-knowledge__search_knowledge`
  must be called at session start before the tool can be invoked.

---

## SESSION METADATA

- **Total chunks**: 1
- **Qdrant collection**: knowledge_v2
- **Primary project**: homelab
- **Stack involved**: Node.js, Qdrant, Ollama (nomic-embed-text), MCP SDK, PowerShell
- **Files modified**: /opt/mcp-servers/qdrant-knowledge/qdrant-mcp-server.js (VM B1), scripts/qdrant-mcp-server-v2.js (local)
- **Git branch**: main
- **Unresolved items**: MCP tool unavailable in current session — reconnects automatically next session
- **Author**: Figur Ulul Azmi
- **Generated by**: Claude Code CLI — RAG Knowledge Capture Skill
