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

## CHUNK 4: VM B1 infrastructure topology: services, IPs, ports

### Context
VM B1 is the homelab server hosting all AI-stack services. Two network paths exist: LAN (fast, home-only) and Tailscale (remote access). All services run as Docker containers under /opt/homelab/ai-stack/.

### Service Map

| Service | LAN URL | Tailscale URL | Notes |
|---|---|---|---|
| Qdrant | 192.168.18.199:6333 | 100.120.249.99:6333 | Vector DB; api-key required |
| n8n | 192.168.18.199:5678 | 100.120.249.99:5678 | Workflow engine; knowledge ingest webhook |
| Ollama | 192.168.18.199:11434 | 100.120.249.99:11434 | Embedding model: nomic-embed-text |
| RAG Gateway | 192.168.18.199:5200 | 100.120.249.99:5200 | ASP.NET Core 9; /rag/search endpoint |
| MCP Server | spawned per-SSH | -- | qdrant-mcp-server.js at /opt/mcp-servers/qdrant-knowledge/ |

### Key Facts
- SSH user: figulazmi; VM B1 LAN: 192.168.18.199; Tailscale: 100.120.249.99
- Qdrant collection: knowledge_v2 (named vectors: dense 768-dim + sparse BM25 djb2)
- n8n webhook for knowledge ingest: http://192.168.18.199:5678/webhook/knowledge-ingest
- MCP server spawned fresh per Claude Code session via claude-mcp-connect.ps1 -- no systemd restart needed
- Docker compose files live in /opt/homelab/ai-stack/qdrant/docker-compose*.yml
- Secrets in /opt/homelab/ai-stack/qdrant/.env (QDRANT_API_KEY, n8n creds)
- push-to-qdrant.sh network auto-detect: localhost:6333 -> LAN 192.168.18.199:6333 -> Tailscale 100.120.249.99:6333

## CHUNK 5: RAG pipeline file locations and config paths on VM B1

### Context
RAG knowledge capture pipeline on VM B1. All components have fixed paths. This reference maps every config file, script, and data directory used by the pipeline.

### File Map

| File | Location | Purpose |
|---|---|---|
| rag_capture.py | ~/scripts/rag-capture-v2/rag_capture.py | CLI entry point for rag add/merge/checkpoint |
| rag config | ~/.rag_config.json | Default project, collection, push_script path |
| push-to-qdrant.sh | ~/scripts/push-to-qdrant.sh | HTTP push to n8n webhook with network auto-detect |
| migrate-to-hybrid.py | ~/scripts/migrate-to-hybrid.py | One-time migration from dense-only to hybrid collection |
| MCP server JS | /opt/mcp-servers/qdrant-knowledge/qdrant-mcp-server.js | Hybrid search server for Claude Code |
| MCP env | ~/.qdrant-mcp.env | QDRANT_API_KEY for MCP server |
| Draft dir | ~/scripts/.rag_drafts/ | Temp storage for rag add output before merge |
| Summaries | .claude/summaries/ (repo root) | Merged knowledge files ready to push |
| Checkpoints | .claude/checkpoints/ (repo root) | In-progress session state |

### Key Facts
- ~/.rag_config.json qdrant_url must be http://localhost:6333 on VM B1 (not 192.168.18.169 which is stale)
- rag merge writes to detect_project_root/.claude/summaries/ based on CWD at invocation time
- push-to-qdrant.sh probes localhost:6333 first, then LAN, then Tailscale for Qdrant health check
- QDRANT_API_KEY=QDRANT_API_KEY_REDACTED (from ~/.qdrant-mcp.env on VM B1)
- rag add drafts accumulate in ~/.rag_drafts/; rag merge consolidates and clears them

## CHUNK 6: Pattern: RRF fusion scores require lower SCORE_THRESHOLD than cosine

### Context
Qdrant hybrid search using Reciprocal Rank Fusion (RRF) produces scores in a different range than raw cosine similarity. Any service switching from dense-only to hybrid RRF must re-tune its score thresholds.

### Pattern
When switching from cosine-only retrieval to RRF hybrid retrieval, always lower the SCORE_THRESHOLD. RRF scores reflect rank position (1 / (k + rank)), not similarity magnitude. A high-quality hybrid result may score 0.35-0.60 whereas the same result via cosine would score 0.70-0.95.

### When to Apply
- Any new Qdrant client (C#, Python, JS) implementing hybrid search
- When results drop to zero after migrating collection from unnamed to named vectors
- When configuring NOT_FOUND gate in MCP server or API gateway

### Anti-Pattern
DO NOT reuse the same SCORE_THRESHOLD from a cosine-only implementation when switching to RRF. A threshold of 0.55 that worked for cosine will filter out nearly all valid RRF results.

### Key Facts
- rag-gateway-mini: ScoreThreshold dropped from 0.55 to 0.35 after hybrid migration
- MCP server qdrant-mcp-server.js: SCORE_THRESHOLD=0.5, NOT_FOUND_THRESHOLD=0.50
- RRF formula: score = sum(1 / (k + rank_i)) where k=60 by default in Qdrant
- Qdrant /points/query with fusion:rrf always produces scores much lower than raw cosine
- Always do a live test query and log raw scores before setting final threshold

## CHUNK 7: Pattern: sparse vector tokenizer must match exactly at index-time and query-time

### Context
Qdrant sparse vector search requires that the tokenizer/hash function used when ingesting documents exactly matches the one used at query time. Any divergence produces mismatched indices and effectively breaks keyword search silently.

### Pattern
Always use the SAME sparse vector implementation (same function, same token regex, same hash algorithm) in every component that touches the Qdrant collection: ingestion script, query client, MCP server. Document the canonical implementation in one place and reference it from all others.

### When to Apply
- When adding a new client that queries or ingests into an existing sparse-indexed collection
- When migrating from Qdrant server-side BM25 model to client-side djb2 (or vice versa)
- When the collection was built using push-to-qdrant.sh / n8n JS node and you add a new .NET or Python query client

### Anti-Pattern
DO NOT switch from client-side djb2 to Qdrant server-side BM25 inference (model: Qdrant/bm25) on an existing collection indexed with djb2. The indices will not match. Server-side inference is only safe when building a new collection from scratch.

### Key Facts
- knowledge_v2 uses CLIENT-SIDE djb2 hash: h=5381; h=((h<<5)+h+charCode)&0x7FFFFFFF; tokenize with /[a-z0-9]+/
- The identical algorithm exists in: qdrant-mcp-server.js (JS), migrate-to-hybrid.py (Python), n8n JS node, QdrantVectorSearchClient.cs (C#)
- rag-gateway-mini switched to SERVER-SIDE Qdrant/bm25 inference -- works because it uses a separate search endpoint, not index-time vectors
- Verification: scroll a point with with_vector=true; inspect sparse.indices -- large integers (19522071) = client djb2, small sequential = server BM25

## CHUNK 8: Pattern: RAG knowledge base chunk_type ratio target for balanced retrieval

### Context
A RAG knowledge base skewed toward one chunk_type (e.g., 67% debug) causes retrieval bias: queries about architecture or patterns return bug-fix context instead. This pattern defines the target distribution for a balanced, high-quality knowledge base.

### Pattern
Target chunk_type distribution for optimal RAG retrieval:

| chunk_type | Target | Current (2026-04-25) | Action |
|---|---|---|---|
| debug | 35-40% | 67% | Stop over-capturing; prioritize extraction |
| pattern | 20-25% | 0.4% | CRITICAL: extract pattern from every fixed bug |
| feature | 15-20% | 9% | Capture after each feature shipped |
| runbook | 10-15% | 8% | On track; continue |
| decision | 8-10% | 4% | Capture ADRs for major choices |
| reference | 5-8% | 1% | CRITICAL: capture topology/config maps |
| implementation-spec | 3-5% | 0% | Activate for code-gen features |

### When to Apply
Every time a debug chunk is captured: ask "what is the reusable rule here?" and capture it as a companion pattern chunk.

### Anti-Pattern
DO NOT capture only debug chunks. A knowledge base of 100% bug fixes teaches the retriever to find past incidents but not prevent future ones or guide new implementation.

### Key Facts
- debug:pattern ratio should trend toward 2:1, not 67:1 as current
- pattern chunks are the highest ROI chunk type for preventing rework
- reference chunks are the most underused -- config topology, port maps, secret locations are searched constantly
- implementation-spec chunks enable code-gen via implementer model (qwen2.5-coder) without hallucination

---

## SESSION METADATA

- **Total chunks**: 8
- **Qdrant collection**: knowledge_v2
- **Generated by**: rag_capture.py v2 -- Incremental Capture
- **Author**: Figur Ulul Azmi
- **Date**: 2026-04-25
- **Unresolved items**: (fill manually if needed)