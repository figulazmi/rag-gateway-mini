---
id: 2026-04-25-qdrant-modifier-idf-covers-sparse-tf-idf-001
date: 2026-04-25
source: claude-code-cli
collection: knowledge_v2
project: homelab
chunk_type: decision
topic: Qdrant modifier idf covers sparse TF-IDF -- no client-side implementation needed
tags: [homelab, vm-b1, qdrant, sparse-vector, bm25, hybrid-search, tfidf]
related: []
session_type: 
environment: homelab
git_branch: 
status: implemented
chunk_source: code
---

## CHUNK 1: Qdrant modifier idf covers sparse TF-IDF -- no client-side implementation needed

### Context
RAG Gateway homelab uses Qdrant knowledge_v2 collection with hybrid search (dense + sparse BM25). The gateway's BuildSparseVector sends TF-only values. A planned fix (Opsi C) proposed building a client-side IDF corpus and applying TF*IDF before sending.

### Problem
RAG_BOTTLENECK_FIXES.md #7 documented a plan to implement client-side IDF in BuildSparseVector -- scroll Qdrant for all stored sparse vectors, build IDF map, apply values[i] = freq * idf[hash]. This plan was written before knowledge_v2 existed.

### Solution
Do NOT implement client-side IDF. knowledge_v2 collection was created with modifier=idf on the sparse vector config. Verified via Qdrant REST API:

GET /collections/knowledge_v2 -> config.params.sparse_vectors: { "sparse": { "modifier": "idf" } }

Qdrant applies IDF automatically at query time: score(doc,query) = sum(TF_doc(t) * TF_query(t) * IDF(t)). BuildSparseVector correctly sends raw TF_query -- Qdrant handles IDF. Implementing client-side IDF would produce TF * IDF^2, over-weighting rare terms quadratically.

### Key Facts
- knowledge_v2 sparse_vectors config has modifier=idf -- confirmed via Qdrant API GET /collections/knowledge_v2
- Client sends TF only; Qdrant multiplies by IDF(t) = log(1 + (N - df(t) + 0.5) / (df(t) + 0.5)) at search time
- Implementing values[i] = freq * idf[hash] in BuildSparseVector would double-apply IDF -- do not do this
- Opsi A+B mitigations (SparsePrefetchLimit=5, SparseScoreThreshold=0.01) remain correct and still needed
- If modifier:idf disappears after collection recreate, re-run migration with SparseVectorParams(modifier=Modifier.IDF)

## CHUNK 2: appsettings.Production.json is Docker volume mount on VM B1 -- must update separately

### Context
rag-gateway-mini runs on VM B1 via Docker Compose. Configuration is split between the repo appsettings.json (checked in) and a production override that holds secrets plus production-specific values.

### Problem
Updating appsettings.json in the repo and redeploying did not apply new config values (ResultLimit, HybridPrefetchLimit) to the running container. The production override file was silently overriding the repo file with old values.

### Solution
The production override is a read-only Docker volume mount, NOT baked into the image and NOT at the path mentioned in CLAUDE.md.

Real path on VM B1: /opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json
Defined in: src/docker-compose.yml volumes section:
  - /opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json:/app/appsettings.Production.json:ro

Update procedure: SSH to VM B1, edit the file directly, then restart container:
  ssh figulazmi@192.168.18.199
  nano /opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json
  docker restart rag-gateway

The repo appsettings.json and the volume-mounted production file must always be kept in sync for non-secret settings (ResultLimit, HybridPrefetchLimit, SparsePrefetchLimit, SparseScoreThreshold).

### Key Facts
- Production override path: /opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json (NOT /opt/rag-gateway/)
- Mount is :ro (read-only) -- container restart required after any edit to pick up changes
- Secret held only in production file: QdrantApiKey = QDRANT_API_KEY_REDACTED
- Non-secret settings in production file MUST mirror appsettings.json in repo -- they are not inherited
- ASPNETCORE_ENVIRONMENT=Production inside container causes production file to override repo file at all matching keys

## CHUNK 3: RAG Gateway RRF funnel widened and full pipeline test results 2026-04-25

### Context
RAG Gateway homelab on VM B1 with 252 points in knowledge_v2. All 7 bottleneck fixes applied (embedding asymmetry, sparse noise, feature_slug, query padding, RRF funnel, cosine gate, IDF). Full live test run performed on 2026-04-25 via /rag/debug endpoint.

### Problem
RRF funnel was too narrow: dense-20 + sparse-5 = 25 candidates -> top 5 (80% drop). If correct chunk ranked 6th, it was dropped. Also ResultLimit=5 too low for multi-chunk feature retrieval.

### Solution
Widened RRF funnel in both appsettings.json (repo) and /opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json (VM B1 volume mount):
  HybridPrefetchLimit: 20 -> 30
  ResultLimit: 5 -> 8
New funnel: dense-30 + sparse-5 = 35 candidates -> top 8 (77% drop).

### Key Facts
- ResultLimit=8 tested live: all 5 test queries returned up to 8 results confirmed
- Positions 6-8 score range: 0.11-0.27, all below threshold 0.35 -- no false positives at current KB size (252 chunks)
- Fix becomes more impactful as KB grows beyond 300-500 chunks and competition between similar docs increases
- Short 2-word queries (no padding) achieve top-1 scores 0.61-0.67 -- well above threshold
- feature_slug filter tested: query with doc_id filter returned all 8 chunks from target feature, all chunk_types present
- Top-1 scores for specific queries: 1.0000 (djb2 tokenizer query), 1.0000 (hybrid search query), 0.8333 (BM25 IDF query)
- Production override was missing SparsePrefetchLimit and SparseScoreThreshold from fix #2 -- now added to volume-mounted file

---

## SESSION METADATA

- **Total chunks**: 3
- **Qdrant collection**: knowledge_v2
- **Generated by**: rag_capture.py v2 -- Incremental Capture
- **Author**: Figur Ulul Azmi
- **Date**: 2026-04-25
- **Unresolved items**: (fill manually if needed)