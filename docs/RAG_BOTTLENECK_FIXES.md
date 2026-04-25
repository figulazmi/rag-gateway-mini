# RAG Pipeline Bottleneck Fixes

Analysis of Pipeline A (Write/Ingest) and Pipeline B (Read/Retrieve) bottlenecks.
Sorted by severity. Status updated as fixes land.

---

## Status Legend

- `[x] FIXED` — merged & deployed
- `[ ] OPEN` — not yet started
- `[~] IN PROGRESS` — work started but not deployed

---

## #1 — Dense Embedding Asymmetry `[x] FIXED`

**Severity**: Critical  
**File**: `src/Application/Services/RagSearchService.cs:38-40, 82-84`  
**Commit**: `fix: mirror ingest embed_content prefix in query embedding for vector space alignment`

### Problem

Ingest (n8n) builds `embed_content`:
```
"This chunk is from project {p}, type {t}, topic "{topic}", tagged {tags}. Session date {d}. Content: {body}"
```
Retrieval (gateway) embedded the bare normalized query with no prepend.
Result: cosine(stored_vector, embed(raw_query)) ≈ **0.728** — query vectors were
~27% off from where stored document vectors live in the 768-dim space.

### Fix Applied

Before calling `GenerateEmbeddingAsync`, `RagSearchService` now builds a matching
`queryEmbedContent`:
```csharp
var queryEmbedContent = request.Project is { Length: > 0 } p
    ? $"This chunk is from project {p}. Content: {normalized}"
    : normalized;
```

Only the dense embedding gets this prepend. The sparse (BM25) leg and filters
still receive the raw `normalized` query — correct, because BM25 must tokenize
real query terms, not the synthetic prefix.

### Expected Impact

cosine(stored_vector, embed(queryEmbedContent)) should approach ~1.000 for
on-topic queries (verified on P1.2 probe: cos = 1.000000 vs 0.728482 for raw).

---

## #2 — Sparse BM25 Noise on Small KB `[x] FIXED (Opsi A+B)`

**Severity**: High  
**Files**: `src/Infrastructure/Configuration/RagGatewayOptions.cs`, `src/Infrastructure/AI/QdrantVectorSearchClient.cs`, `src/appsettings.json`  
**Commit**: `fix: hybrid search noise reduction via asymmetric prefetch and sparse score threshold`

### Problem

Dua root cause:
1. KB kecil (<200 docs) → IDF discrimination flat → semua dokumen dapat skor sparse mirip
2. `BuildSparseVector` menggunakan TF-only (bukan TF-IDF) → token umum dan langka bobot sama

Sparse top-1 returned the wrong document karena generic homelab terms mendapat bobot
sama dengan rare discriminative terms. RRF mencampur hasil dense yang benar dengan
sparse yang noisy → correct chunk terdepak dari top-5.

> Root cause TF-only belum di-fix. Lihat **#7 (Opsi C)** untuk fix permanen.

### Fix Applied (Opsi A + B)

**Opsi A** — Asymmetric prefetch: sparse leg fetch hanya 5 kandidat (bukan 20).
Sparse memiliki pengaruh lebih kecil di RRF tanpa dimatikan total.

**Opsi B** — Score threshold: hanya sparse results dengan score > 0.01 masuk ke RRF.
Hasil flat (semua dokumen dapat skor mirip) ter-filter sebelum fusion.

```csharp
// QdrantVectorSearchClient — sparse prefetch
prefetch.Add(new {
    query = new { indices = sparse.Indices, values = sparse.Values },
    @using = _options.SparseVectorName,
    limit = _options.SparsePrefetchLimit,        // 5 (bukan 20)
    score_threshold = _options.SparseScoreThreshold  // 0.01
});
```

```json
// appsettings.json
"EnableHybridSearch": true,
"SparsePrefetchLimit": 5,
"SparseScoreThreshold": 0.01
```

### Keterbatasan

Fix ini mengurangi noise tapi tidak menghilangkan root cause (TF-only weighting).
Ketika KB > 300 docs, eksekusi **#7 (Opsi C)** untuk fix permanen.

---

## #3 — No Cross-Chunk Linking for Full Feature Flow `[x] FIXED`

**Severity**: Medium  
**Files**: ingest pipeline (n8n payload), `src/Infrastructure/AI/QdrantVectorSearchClient.cs`,
`src/Controllers/RagController.cs`  
**Effort**: Medium — requires schema change + n8n node update + gateway filter support

### Problem

A single feature spans multiple chunk types (feature + decision + runbook + debug + pattern).
One call to `/rag/search` returns at most `ResultLimit=5` mixed results. No mechanism
to say "give me everything about X feature" — you'd need separate queries per chunk type.

### Fix Needed

1. Add `feature_slug` field to ingest payload in `push-to-qdrant.sh` and n8n
   Validate & Clean node.
2. Add `feature_slug` to `RagSearchRequest` DTO.
3. Add Qdrant `must` filter for `feature_slug` in `QdrantVectorSearchClient`.
4. Expose `?feature_slug=` query param in `RagController`.

This allows: `POST /rag/search { "feature_slug": "hybrid-search-refactor" }` to
pull all 5 chunk types for that feature in one call.

---

## #4 — QueryNormalizer Padding Adds Semantic Noise `[x] FIXED`

**Severity**: Medium  
**File**: `src/Infrastructure/Helpers/QueryNormalizer.cs`  
**Effort**: Small — remove or rethink padding logic

### Problem

Queries shorter than 8 words get padded with generic terms. Two failure modes:
- Generic pad tokens have high frequency in the KB → high BM25 score for wrong docs
- Pad tokens shift the dense embedding away from the true query intent

With Fix #2 (disable hybrid), the BM25 failure mode disappears, but dense shift remains.

### Fix Needed

Option A (recommended): Remove padding entirely. The 8-word minimum is a RAG capture
guideline for *humans writing knowledge*, not a retrieval constraint. Short precise
queries ("Qdrant named vectors syntax") outperform padded long queries.

Option B: Keep padding but use domain-specific terms drawn from a curated list
(project names, technology names) that don't inflate BM25 scores.

---

## #5 — RRF Funnel Too Aggressive `[x] FIXED`

**Severity**: Low  
**File**: `src/appsettings.json` → `HybridPrefetchLimit`, `ResultLimit`  
**Commit**: `fix: widen RRF funnel — HybridPrefetchLimit 20→30, ResultLimit 5→8`

### Problem

```
prefetch: dense-20 + sparse-5 = 25 candidates → RRF → top 5 returned (80% drop)
```

If the correct chunk ranks 6th in dense but is noisy in sparse, RRF can drop it
entirely. The gap between prefetch and result limits was too wide.

### Fix Applied

```json
"HybridPrefetchLimit": 30,
"ResultLimit": 8
```

Unblocked by #7: `knowledge_v2` collection has `modifier: idf` on the sparse config —
Qdrant applies IDF server-side at query time, making sparse quality sufficient to
re-enable with a wider funnel without introducing noise regressions.

---

## #6 — n8n Webhook Shadow Risk (Ingest Reliability) `[x] FIXED`

**Severity**: Low  
**Scope**: n8n workflow + `push-to-qdrant.sh`  
**Effort**: Small — add cosine gate to ingest script

### Problem

n8n does not always re-register a webhook on workflow Save alone. A duplicate workflow
owning the same `/webhook/knowledge-ingest` path silently shadows the updated one.
Result: Ollama node reads `$json.content` (raw) instead of `$json.embed_content`
(prepended), stored vectors become embed(raw) — Fix #1 is undermined without detection.

Symptom: `cos(stored, embed(prepended))` drops from ~1.000 to ~0.728 after
a workflow re-import/re-save.

### Fix Needed

Add a cosine gate at the end of `push-to-qdrant.sh`:

```bash
# After upsert, verify stored vector matches embed_content, not raw content
python scripts/rag-capture-v2/verify_embed_cosine.py --string-id "$CHUNK_ID"
```

Pass threshold: `cos(stored, prepended) > 0.99 AND cos(stored, raw) < 0.99`.
Fail fast with non-zero exit code if gate fails — prevents silent bad ingests.

Also: after any n8n workflow import/update, always toggle Active off → on to
force webhook re-registration.

---

---

## #7 — Sparse TF-only Weighting (Opsi C) `[x] FIXED`

**Severity**: Medium  
**File**: `src/Infrastructure/AI/QdrantVectorSearchClient.cs` — `BuildSparseVector`  
**Resolution**: Covered by server-side `modifier: idf` on `knowledge_v2` collection

### Problem

`BuildSparseVector` sends TF-only sparse values. Token umum ("docker", "qdrant") dan
token langka ("IVectorSearchClient") mendapat bobot sama jika frekuensi kemunculannya sama.

### Why It's Already Fixed

`knowledge_v2` collection was created with `modifier: idf` on the sparse vector config:
```python
sparse_vectors_config={ "sparse": SparseVectorParams(modifier=Modifier.IDF) }
```
Qdrant computes `IDF(t) = log(1 + (N - df(t) + 0.5) / (df(t) + 0.5))` at query time and
multiplies it into each sparse query term automatically. Effective scoring:
```
score(doc, query) = Σ TF_doc(t) × TF_query(t) × IDF(t)
```
`BuildSparseVector` correctly sends raw `TF_query` — Qdrant applies IDF. Implementing
client-side IDF would double-apply it (`IDF²`) and over-weight rare terms.

### Why Opsi C (client-side IDF map) Would Be Wrong Now

`values[i] = freq * idf[hash]` in `BuildSparseVector` would produce `TF × IDF` on the
client; Qdrant's `modifier: idf` would then apply `IDF` again → `TF × IDF²`. Do not
implement. The Opsi A+B mitigations (`SparsePrefetchLimit=5`, `SparseScoreThreshold=0.01`)
remain in place and are still correct.

---

## Fix Sequence (Recommended Order)

| Priority | Fix | Effort | Status |
|----------|-----|--------|--------|
| 1 | #1 Embedding asymmetry | Done | `[x] FIXED` |
| 2 | #2 Sparse noise (Opsi A+B) | Done | `[x] FIXED` |
| 3 | #4 Remove QueryNormalizer padding | Done | `[x] FIXED` |
| 4 | #6 Cosine gate in push-to-qdrant.sh | Done | `[x] FIXED` |
| 5 | #3 Cross-chunk feature_slug linking | Done | `[x] FIXED` |
| 6 | #5 Widen RRF funnel | Done | `[x] FIXED` |
| 7 | #7 Sparse TF-IDF (Opsi C) | N/A | `[x] FIXED` — covered by modifier: idf server-side |
