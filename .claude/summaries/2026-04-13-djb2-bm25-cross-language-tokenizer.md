---
id: 2026-04-13-djb2-bm25-cross-language-tokenizer
date: 2026-04-13
source: claude-code-cli
project: homelab
chunk_type: pattern
topic: djb2 Hash BM25 Sparse Tokenizer - Consistent Across JavaScript C# Python
tags: [qdrant, sparse-vector, bm25, djb2, n8n, dotnet, python, homelab]
related: [rag-gateway-hybrid-search, n8n-qdrant-sparse-upsert-errors]
session_type: architecture
environment: homelab
git_branch: main
status: implemented
chunk_source: code
---

## CHUNK 1: djb2 BM25 Sparse Tokenizer Pattern for Cross-Language Consistency

### Context

RAG Gateway homelab uses Qdrant hybrid search (dense + sparse BM25). Sparse
vectors must be generated at both index time (n8n ingestion) and query time
(RAG Gateway .NET). When using Qdrant REST API directly (not Python client),
server-side BM25 document inference is not available for upsert — only for
Query API. A client-side tokenizer must be implemented identically across all
environments that produce or consume sparse vectors.

### When to Use

- Any system where Qdrant REST PUT upsert is used directly (not via Python qdrant-client)
- When sparse vectors must be generated in multiple languages (JS, C#, Python)
- When Qdrant Query API document inference is unavailable or inconsistent with upsert side
- When fastembed / qdrant-client Python dependency is not available in the indexing environment

### When NOT to Use

- If all indexing goes through Python qdrant-client with fastembed — use `models.Document` instead (more accurate BM25)
- If only search (not indexing) needs sparse vectors — Qdrant Query API handles document inference natively
- Do not use this pattern as a replacement for fastembed in Python environments that already have it

### Implementation

Algorithm: djb2 hash (polynomial, seed 5381) applied to lowercased alphanumeric tokens.
Tokenizer: `[a-z0-9]+` regex on lowercased text. Term frequency (TF) as sparse values.
The `& 0x7FFFFFFF` mask keeps indices as positive 31-bit integers.

Steps:
1. Lowercase input text
2. Extract tokens via regex `[a-z0-9]+`
3. Build term frequency map (token → count)
4. For each unique token: index = djb2(token), value = frequency
5. Return `{indices: [...], values: [...]}`

All three environments (n8n JS, RAG Gateway C#, migrate-to-hybrid.py Python)
use the SAME algorithm to ensure sparse indices match at search time.

### Key Facts

- djb2 seed is 5381; formula per character: `h = ((h << 5) + h) + char_code`
- Bitmask `& 0x7FFFFFFF` applied per character to keep value positive 31-bit
- Tokenizer regex `[a-z0-9]+` must be identical across all language implementations
- Term frequency (raw count, not normalized) is used as sparse vector values
- IDF weighting is applied server-side by Qdrant at search time via collection `modifier: idf`
- If djb2 implementation drifts between languages, sparse search returns zero matches
- Re-migration required whenever the tokenizer algorithm changes

### Code / Commands

```javascript
// JavaScript (n8n Code node)
function djb2(str) {
  let h = 5381;
  for (let i = 0; i < str.length; i++) {
    h = ((h << 5) + h) + str.charCodeAt(i);
    h = h & 0x7FFFFFFF;
  }
  return h;
}
function buildSparse(text) {
  const tokens = text.toLowerCase().match(/[a-z0-9]+/g) || [];
  const tf = {};
  for (const t of tokens) tf[t] = (tf[t] || 0) + 1;
  const indices = [], values = [];
  for (const [term, freq] of Object.entries(tf)) {
    indices.push(djb2(term)); values.push(freq);
  }
  return { indices, values };
}
```

```csharp
// C# (QdrantVectorSearchClient.cs — BuildSparseVector)
var tokens = Regex.Matches(text.ToLowerInvariant(), @"[a-z0-9]+").Select(m => m.Value);
var tf = new Dictionary<string, int>();
foreach (var t in tokens) tf[t] = tf.TryGetValue(t, out var c) ? c + 1 : 1;
foreach (var (term, freq) in tf) {
    int h = 5381;
    foreach (var ch in term)
        h = (((h << 5) + h) + ch) & 0x7FFFFFFF;
    indices[i] = h; values[i] = freq; i++;
}
```

```python
# Python (migrate-to-hybrid.py — djb2_sparse)
import re
def djb2_sparse(text: str):
    tokens = re.findall(r'[a-z0-9]+', text.lower())
    tf = {}
    for t in tokens:
        h = 5381
        for ch in t:
            h = (((h << 5) + h) + ord(ch)) & 0x7FFFFFFF
        tf[h] = tf.get(h, 0) + 1
    return SparseVector(indices=list(tf.keys()), values=[float(v) for v in tf.values()])
```

### Variations

- **With normalization**: divide values by `len(tokens)` for normalized TF. Improves cross-document scoring fairness but changes magnitude — choose consistently.
- **With stopword removal**: filter common words (the, is, at) before hashing to reduce noise. Add to tokenizer step before the tf loop.
- **Higher modulo**: if 31-bit indices cause hash collisions, use raw 32-bit (`& 0xFFFFFFFF`) or add `% some_prime` for tighter distribution.

---

## SESSION METADATA

- **Total chunks**: 1
- **Qdrant collection**: knowledge_v2
- **Primary project**: homelab
- **Stack involved**: Qdrant 1.17.1, n8n, .NET 9 ASP.NET Core, Python qdrant-client
- **Files modified**: My workflow.json, src/Infrastructure/AI/QdrantVectorSearchClient.cs, scripts/migrate-to-hybrid.py
- **Git branch**: main
- **Unresolved items**: Verify djb2 produces consistent indices across all three implementations by testing with a known input string
- **Author**: Figur Ulul Azmi
- **Generated by**: Claude Code CLI — RAG Knowledge Capture Skill
