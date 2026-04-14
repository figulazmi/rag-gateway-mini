---
id: 2026-04-13-n8n-qdrant-sparse-upsert-errors
date: 2026-04-13
source: claude-code-cli
project: homelab
chunk_type: debug
topic: n8n Qdrant Sparse Vector Upsert Errors - Expression Bug and VectorStruct Fix
tags: [n8n, qdrant, sparse-vector, hybrid-search, homelab, fixed, rag-gateway]
related: [rag-gateway-hybrid-search, djb2-bm25-tokenizer]
session_type: debug
environment: homelab
git_branch: main
status: implemented
chunk_source: code
---

## CHUNK 1: n8n Expression Double-Prefix Bug Causing Empty Vector Name Error

### Context

RAG Gateway homelab uses n8n workflow to ingest knowledge chunks into Qdrant
collection knowledge_v2 (hybrid dense + sparse). The Qdrant Upsert Point node
uses a raw JSON body with n8n expression syntax.

### Problem

After updating the n8n workflow to support hybrid search (named vectors dense +
sparse), the Qdrant upsert node returned HTTP 400:
`Wrong input: Not existing vector name error: ""`
The error indicated Qdrant received an empty string as a vector name. The workflow
used body field value: `"=  ={{ JSON.stringify({...}) }}"` with a leading `=  =`
before the expression delimiter.

### Solution

The leading `=  =` caused n8n to evaluate the expression as template `  =` +
expression result, producing body with literal prefix `  =` before the JSON.
This broke Qdrant's request parsing and surfaced as an empty vector name error.
Fix: Change body field from `"=  ={{ ... }}"` to `"={{ ... }}"` (single `=`
only, immediately followed by `{{`). This is n8n's correct expression prefix format.

### Key Facts

- n8n raw body expression prefix must be exactly `={{ ... }}` — no extra `=` or spaces
- Leading `=  =` before `{{...}}` causes n8n to prepend literal `  =` to the body string
- A non-JSON prefix in the body causes Qdrant to return unexpected parse errors, not a JSON parse error
- Qdrant error `Not existing vector name error: ""` can indicate malformed request body, not only an actual empty vector name
- This bug appears when copy-pasting body expressions from documentation with accidental double-equals

### Caveats

The script push-to-qdrant.sh may still show HTTP 200 even when n8n workflow
fails internally, because n8n can return 200 on error depending on workflow
settings. Always verify by checking n8n execution history, not just curl exit code.

---

## CHUNK 2: Qdrant REST PUT VectorStruct Does Not Support Document Inference

### Context

After fixing the expression prefix bug, the n8n Qdrant upsert node was updated
to send sparse vectors using `{ "text": "...", "model": "Qdrant/bm25" }` format,
following Qdrant Query API documentation for server-side BM25 inference.

### Problem

Qdrant REST PUT `/collections/knowledge_v2/points` returned HTTP 400:
`Format error in JSON body: data did not match any variant of untagged enum VectorStruct`
The `document` wrapper format `{ "document": { "text": "...", "model": "Qdrant/bm25" } }`
and the direct format `{ "text": "...", "model": "..." }` both failed with the same error.

### Solution

Root cause: Qdrant REST PUT `/collections/{name}/points` uses the legacy
`VectorStruct` serde type which only accepts `float[]` (dense) or
`{"indices": [...], "values": [...]}` (sparse). The `document` inference format
is ONLY supported in the Query API (`POST /points/query`), not in the upsert endpoint.

The Python qdrant-client works with `models.Document` because fastembed tokenizes
text locally (client-side) using the `Qdrant/bm25` model and sends actual
`{indices, values}` to the REST API — it does NOT send the document format.

Fix: Replace server-side document inference with client-side djb2 hash tokenizer.
Generate `{indices, values}` in the n8n Prepare Qdrant Point Code node before
the HTTP call. Move the entire `JSON.stringify` body construction to the Code node
(not the HTTP node expression) to avoid n8n serialization issues with 768-float arrays.

Affected files:
- `My workflow.json` — Prepare Qdrant Point code + body expression simplified
- `src/Infrastructure/AI/QdrantVectorSearchClient.cs` — BuildSparseVector() with djb2
- `scripts/migrate-to-hybrid.py` — djb2_sparse() replacing models.Document

### Key Facts

- Qdrant REST PUT `/collections/{name}/points` uses `VectorStruct` (legacy type) — no document inference
- Qdrant Query API `POST /collections/{name}/points/query` supports document inference — used for search only
- Python qdrant-client `models.Document` tokenizes locally via fastembed, sends `{indices, values}` to REST
- Server-side BM25 via `document` format works ONLY for query/search, NOT for upsert/index
- Moving JSON.stringify to the Code node (not HTTP node expression) avoids n8n serialization quirks with large float arrays
- djb2 tokenizer must be implemented identically in n8n JS, C# BuildSparseVector(), and Python djb2_sparse()
- After this fix, migrate-to-hybrid.py must be re-run to rebuild sparse vectors using djb2 (old vectors used Qdrant/bm25 server-side indices which are incompatible)

### Code / Commands

```javascript
// n8n Code node: djb2 hash for BM25 sparse vector
function djb2(str) {
  let h = 5381;
  for (let i = 0; i < str.length; i++) {
    h = ((h << 5) + h) + str.charCodeAt(i);
    h = h & 0x7FFFFFFF; // keep positive 31-bit
  }
  return h;
}
const tokens = sparseText.toLowerCase().match(/[a-z0-9]+/g) || [];
// build tf map, then map each unique token → djb2(token) as index
```

```csharp
// QdrantVectorSearchClient.cs: identical algorithm in C#
int h = 5381;
foreach (var ch in term)
    h = (((h << 5) + h) + ch) & 0x7FFFFFFF;
indices[i] = h;
```

### Caveats

Re-migration with `python3 scripts/migrate-to-hybrid.py` is required after this
change to rebuild all 147 existing points' sparse vectors using djb2. Points
migrated with old Qdrant/bm25 server-side indices will NOT match djb2-based
query vectors — hybrid sparse search will produce zero matches for those points
until re-migration is done.

---

## SESSION METADATA

- **Total chunks**: 2
- **Qdrant collection**: knowledge_v2
- **Primary project**: homelab
- **Stack involved**: n8n, Qdrant 1.17.1, .NET 9 ASP.NET Core, Python qdrant-client
- **Files modified**: My workflow.json, src/Infrastructure/AI/QdrantVectorSearchClient.cs, scripts/migrate-to-hybrid.py
- **Git branch**: main
- **Unresolved items**: Re-run migrate-to-hybrid.py on VM B1 to rebuild sparse vectors with djb2; redeploy RAG Gateway Docker container; import updated My workflow.json to n8n
- **Author**: Figur Ulul Azmi
- **Generated by**: Claude Code CLI — RAG Knowledge Capture Skill
