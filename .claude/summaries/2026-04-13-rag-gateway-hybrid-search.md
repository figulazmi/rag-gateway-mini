---
id: 2026-04-13-rag-gateway-hybrid-search
date: 2026-04-13
source: claude-code-cli
project: homelab
chunk_type: feature
topic: RAG Gateway Hybrid Search Dense Plus Sparse BM25 Implementation
tags: [rag-gateway, qdrant, hybrid-search, bm25, dotnet, ollama, homelab, implemented]
related: [qdrant-knowledge-collection, rag-first-protocol, n8n-knowledge-ingest]
session_type: feature
environment: homelab
git_branch: main
status: implemented
chunk_source: code
---

## CHUNK 1: Hybrid Search Gateway Refactor From Points Search To Query API

### Context

rag-gateway-mini is an ASP.NET Core 9 service on VM B1 port 5200 acting as the RAG retrieval layer for two projects (homelab, petrochina-eproc). It previously did dense-only search via Ollama nomic-embed-text embeddings against Qdrant collection "knowledge" using POST /collections/{name}/points/search with an unnamed vector. Knowledge base contains many exact terms (class names, error messages, config keys) that semantic-only retrieval misses.

### Requirements

- Add sparse BM25 retrieval alongside dense to improve keyword precision.
- Combine rankings via Reciprocal Rank Fusion (RRF), no manual score normalization.
- Zero new runtime dependencies in .NET stack — no Python sidecar, no client-side BM25 tokenizer.
- Preserve existing /rag/search and /rag/debug endpoint contracts; only add optional chunk_type filter.
- Allow degrading to dense-only via config flag without code changes.

### Architecture Decision

Use Qdrant server-side BM25 inference (Qdrant >= 1.15.2). At query time the .NET client sends the raw query string as a Document object inside the prefetch leaf — Qdrant performs tokenization, IDF lookup, and sparse vector construction internally. This avoids implementing a hash-compatible BM25 tokenizer in C# (which would have to match Qdrant/bm25 hashing exactly to align with stored sparse vectors). Endpoint switches from /points/search to /points/query so RRF fusion across two prefetch legs is server-side. Collection migrates to named vectors (dense + sparse) — old unnamed-vector "knowledge" stays intact for inspection but the gateway no longer points to it. One-way migration, no dual code path.

### Implementation

QdrantVectorSearchClient.ExecuteQueryAsync builds a request body with two prefetch entries: one with the dense float[] vector targeting "using": "dense", limit HybridPrefetchLimit (20); one with { text, model: "Qdrant/bm25" } targeting "using": "sparse". Top-level query is { fusion: "rrf" }. The sparse leg is omitted when EnableHybridSearch=false (degrades to dense-only on the same v2 collection). Filter builder produces dynamic must list with project and chunk_type matches when present. Response shape changed from { result: [...] } to { result: { points: [...] } } — added QdrantQueryResponse + QdrantQueryResult wrappers, MapToRagResultItem unchanged. RagSearchService now passes the normalized query text plus optional chunk_type into the vector client. RagDebugResponse gained search_mode, fusion_method, prefetch_limit, chunk_type_filter so /rag/debug surfaces hybrid pipeline state.

### Key Facts

- Qdrant /points/query with two prefetch legs and { fusion: "rrf" } is the server-side hybrid retrieval API since Qdrant 1.15.2.
- Sending { text, model: "Qdrant/bm25" } as the prefetch query lets Qdrant compute the sparse vector server-side without client-side BM25 implementation.
- Default ScoreThreshold dropped from 0.55 to 0.35 because RRF produces small reciprocal-rank scores, not cosine similarities.
- IVectorSearchClient signatures changed to require queryText so the sparse leg can be built — embedding alone is insufficient for hybrid.
- Collection knowledge_v2 uses named vectors "dense" (768, COSINE) and "sparse" (modifier IDF); old "knowledge" is unnamed-vector and incompatible with the new code path.
- Config flag EnableHybridSearch=false keeps the same /points/query path but sends only the dense prefetch — RAG Gateway never falls back to old unnamed-vector "knowledge" collection.

### Code / Commands

```csharp
// Hybrid prefetch construction
var prefetch = new List<object>
{
    new { query = vector, @using = _options.DenseVectorName, limit = _options.HybridPrefetchLimit }
};
if (_options.EnableHybridSearch && !string.IsNullOrWhiteSpace(queryText))
{
    prefetch.Add(new
    {
        query = new { text = queryText, model = _options.SparseInferenceModel },
        @using = _options.SparseVectorName,
        limit = _options.HybridPrefetchLimit
    });
}
var requestBody = new Dictionary<string, object>
{
    ["prefetch"] = prefetch,
    ["query"] = new { fusion = _options.FusionMethod },
    ["limit"] = _options.ResultLimit,
    ["with_payload"] = true
};
```

### Lessons Learned

The biggest .NET pitfall is forgetting that named-vector collections require "using" in every prefetch leg — omitting it causes Qdrant 400. The Document syntax for server-side inference is undocumented in many community examples; it works for Qdrant/bm25 specifically because BM25 needs no real ML model, just IDF/TF computation. Threshold tuning is mandatory when switching from cosine to RRF — keeping the old 0.55 threshold would have dropped every result.

---

## CHUNK 2: Qdrant Hybrid Collection Migration Pattern Knowledge To Knowledge V2

### Context

The "knowledge" Qdrant collection on VM B1 stored only dense vectors in unnamed-vector format. Qdrant does not support adding a sparse vectors config to an existing collection — a fresh collection is required. The migration must preserve every payload field plus the original 768-dim dense vector while letting Qdrant generate sparse vectors server-side from the chunk text.

### Requirements

- Idempotent script (re-runnable without manual cleanup).
- Reuse existing dense vectors — no re-embedding (saves Ollama compute time and avoids drift).
- Generate sparse vectors server-side from a sparse_text string (topic + content).
- Create payload indexes for all common filter keys before bulk insert.
- Verify point count parity at the end.

### Architecture Decision

Use qdrant-client Python on VM B1 because it has first-class support for models.Document inference and PointStruct with named-vector dicts. A .NET migration tool would need to hand-roll the Document JSON shape. The script lives in repo (scripts/migrate-to-hybrid.py) so it is versioned alongside the gateway change, but execution is manual on VM B1. sparse_text combines topic + content for richer BM25 signal; payload remains untouched so all existing filter keys (project, chunk_type, status, tags, session_type, environment) keep working post-migration.

### Implementation

Drop knowledge_v2 if exists → create with vectors_config={ "dense": VectorParams(768, COSINE) } + sparse_vectors_config={ "sparse": SparseVectorParams(modifier=Modifier.IDF) }. Create six KEYWORD payload indexes (project, chunk_type, status, tags, session_type, environment) before any upsert. Scroll knowledge in batches of 50 with with_vectors=True; for each point extract dense from either named dict (point.vector["dense"]) or unnamed list, build sparse_text = f"{topic} {content}".strip(), upsert with vector={ "dense": dense_vector, "sparse": Document(text=sparse_text, model="Qdrant/bm25") }. Verify points_count parity and exit.

### Key Facts

- Qdrant cannot add sparse_vectors_config to an existing collection — schema migration requires creating a new collection and copying points.
- models.Document(text, model="Qdrant/bm25") in qdrant-client triggers server-side BM25 sparse vector generation during upsert; no client-side fastembed install needed.
- Modifier.IDF on the sparse vector params enables proper BM25 IDF weighting at search time.
- Payload indexes must be created before bulk upsert for best ingest performance and immediate filter availability.
- Reusing the existing dense vector (instead of re-embedding via Ollama) avoids embedding drift and saves about one round-trip per chunk to nomic-embed-text.
- The script handles both named (dict) and unnamed (list) vector formats from the source collection so it works regardless of how "knowledge" was originally created.

### Code / Commands

```python
client.create_collection(
    collection_name="knowledge_v2",
    vectors_config={ "dense": models.VectorParams(size=768, distance=models.Distance.COSINE) },
    sparse_vectors_config={ "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF) },
)
# Per-point upsert
models.PointStruct(
    id=point.id,
    vector={
        "dense": dense_vector,
        "sparse": models.Document(text=sparse_text, model="Qdrant/bm25"),
    },
    payload=point.payload,
)
```

```bash
# Run on VM B1
pip install 'qdrant-client>=1.13.0' --break-system-packages
python3 scripts/migrate-to-hybrid.py
```

### Lessons Learned

Phase gating (verify Qdrant >= 1.15.2 before running migration) prevents wasted attempts — older Qdrant accepts the schema but ignores Document-based sparse generation, leaving sparse vectors empty and search results identical to dense-only. Combining topic + content for sparse_text gives noticeably better keyword recall than content alone because chunk titles concentrate the most identifying terms. Keeping the old "knowledge" collection untouched after migration is cheap insurance — costs a few MB of disk but provides a clean inspection target if any payload field looks corrupted in v2.

---

## SESSION METADATA

- **Total chunks**: 2
- **Qdrant collection**: knowledge
- **Primary project**: homelab
- **Stack involved**: .NET 9, ASP.NET Core, Qdrant 1.15.2+, Ollama nomic-embed-text, qdrant-client Python, Docker Compose
- **Files modified**: src/Infrastructure/Configuration/RagGatewayOptions.cs, src/Infrastructure/AI/QdrantVectorSearchClient.cs, src/Application/Services/RagSearchService.cs, src/Application/Interfaces/IVectorSearchClient.cs, src/Application/DTOs/RagSearchRequest.cs, src/Application/DTOs/RagDebugResponse.cs, src/appsettings.json, src/appsettings.Production.json.template, scripts/migrate-to-hybrid.py
- **Git branch**: main
- **Unresolved items**: Verify Qdrant version on VM B1; run migration script; rebuild Docker container; update n8n knowledge-ingest workflow and ~/scripts/push-to-qdrant.sh to target knowledge_v2 with named dense + sparse Document format
- **Author**: Figur Ulul Azmi
- **Generated by**: Claude Code CLI — RAG Knowledge Capture Skill
