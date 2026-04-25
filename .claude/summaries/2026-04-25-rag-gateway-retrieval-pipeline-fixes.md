---
id: 2026-04-25-rag-gateway-retrieval-pipeline-bottlenec-001
date: 2026-04-25
source: claude-code-cli
collection: knowledge_v2
project: homelab
chunk_type: decision
topic: RAG Gateway retrieval pipeline bottleneck fixes session 2026-04-25
tags: [homelab, vm-b1, rag-gateway, dotnet, embedding, hybrid-search, retrieval]
related: []
session_type: 
environment: homelab
git_branch: 
status: implemented
chunk_source: code
---

## CHUNK 1: RAG Gateway retrieval pipeline bottleneck fixes session 2026-04-25

### Context
rag-gateway-mini (ASP.NET Core 9, port 5200 VM B1) had 5 retrieval bottlenecks identified and fixed in one session. Stack: Ollama nomic-embed-text 768-dim, Qdrant knowledge_v2 hybrid dense+sparse, RRF fusion.

### Problem
Five concurrent retrieval quality issues: (1) dense vector space mismatch between ingest and query, (2) sparse BM25 noise on small KB, (3) QueryNormalizer adding generic pad tokens, (4) no post-ingest cosine verification, (5) no way to retrieve all chunks of one feature.

### Solution
Five targeted fixes, all in RagSearchService or config -- no architectural change.

Fix 1 (Critical): In RagSearchService.SearchAsync and DebugAsync, build queryEmbedContent before calling GenerateEmbeddingAsync. Format: "This chunk is from project {project}. Content: {normalized}". Ingest side (n8n) embeds "This chunk is from project {p}, type {t}, topic {topic}, tagged {tags}. Session date {d}. Content: {body}". Query vectors now live in same 768-dim region as stored vectors.

Fix 2 (High): Added SparsePrefetchLimit=5 and SparseScoreThreshold=0.01 to RagGatewayOptions. Sparse prefetch leg uses these instead of sharing HybridPrefetchLimit=20. Score threshold filters flat-IDF results before RRF. Re-enabled EnableHybridSearch=true. Opsi C (TF-IDF weighting) deferred to KB > 300 docs.

Fix 4 (Medium): Removed QueryNormalizer entirely -- kept only null guard + trim + collapse spaces. The 8-word padding was a human-writing guideline, not a retrieval constraint. Generic pad tokens ("implementation", "details") shifted dense embeddings and inflated BM25 scores.

Fix 6 (Low): Created ~/scripts/verify_embed_cosine.py on VM B1. After push-to-qdrant.sh upserts, it scrolls Qdrant for chunk-1, embeds raw vs prepended via Ollama, computes cosine. Pass when cos(stored,prepended) >= 0.95 AND cos(stored,raw) < 0.95. Runs via SSH from laptop or directly on B1.

Fix 3 (Medium): Added feature_slug field to RagSearchRequest. Maps to doc_id filter in QdrantVectorSearchClient (Qdrant payload already has doc_id). Enables "give me all chunks about X feature" query without multiple round trips.

### Key Facts
- Query embed_content prefix format must mirror ingest format -- token alignment in 768-dim space is critical; cos(stored,raw) = 0.728 vs cos(stored,prepended) = 1.000
- BuildSparseVector in QdrantVectorSearchClient uses TF-only (no IDF) -- root cause of sparse noise, deferred fix documented as #7 in docs/RAG_BOTTLENECK_FIXES.md
- feature_slug maps to Qdrant payload field doc_id (already stored by n8n) -- no n8n changes needed, verified via Qdrant scroll
- All fixes tracked in docs/RAG_BOTTLENECK_FIXES.md with FIXED/OPEN status and Opsi C documented for future
- cosine gate in push-to-qdrant.sh uses || true so it is warning-only, does not abort push on fail

## CHUNK 2: rag-gateway-mini feature_slug filter via doc_id for cross-chunk retrieval

### Context
rag-gateway-mini retrieves up to ResultLimit=5 mixed chunks per query. A full feature flow spans multiple chunk types (feature + decision + runbook + debug + pattern) -- one query cannot guarantee all aspects are returned. Qdrant knowledge_v2 already stores doc_id in every point payload (set by n8n from push-to-qdrant.sh id field).

### Problem
No way to retrieve all chunks belonging to one session/feature without issuing separate queries per chunk_type. Users cannot ask "give me everything about X" in one call.

### Solution
Added feature_slug optional field to RagSearchRequest. Maps to Qdrant must filter on doc_id payload field. No n8n or push-to-qdrant.sh changes needed since doc_id already exists in all stored points.

Files changed: RagSearchRequest.cs (+FeatureSlug), RagDebugResponse.cs (+FeatureSlugFilter), IVectorSearchClient.cs (+featureSlug param), RagSearchService.cs (pass through + log), QdrantVectorSearchClient.cs (add doc_id must filter in ExecuteQueryAsync).

doc_id value format in Qdrant: "2026-04-11-rag-gateway-namespace-cleanup-build-fix" -- date prefix + hyphenated topic slug, derived from frontmatter id field in summary .md files.

### Key Facts
- feature_slug in request body maps to {"key": "doc_id", "match": {"value": feature_slug}} in Qdrant must filter
- doc_id is already in every knowledge_v2 point payload -- verified via Qdrant scroll before implementing
- feature_slug is additive with project and chunk_type filters -- all three can be combined
- To discover valid feature_slug values: check metadata.doc_id in any /rag/search or /rag/debug response
- Example call: POST /rag/search {"query":"how does embedding work","project":"homelab","feature_slug":"2026-04-11-rag-gateway-namespace-cleanup-build-fix"}

---

## SESSION METADATA

- **Total chunks**: 2
- **Qdrant collection**: knowledge_v2
- **Generated by**: rag_capture.py v2 -- Incremental Capture
- **Author**: Figur Ulul Azmi
- **Date**: 2026-04-25
- **Unresolved items**: (fill manually if needed)