---
id: 2026-04-25-decision-hybrid-rrf-dense-plus-sparse-se-001
date: 2026-04-25
source: claude-code-cli
collection: knowledge_v2
project: homelab
chunk_type: decision
topic: Decision: hybrid RRF dense plus sparse search over cosine-only for knowledge_v2
tags: [homelab, vm-b1, qdrant, hybrid-search, rrf, decision, adr]
related: []
session_type: 
environment: homelab
git_branch: 
status: implemented
chunk_source: code
---

## CHUNK 1: Decision: hybrid RRF dense plus sparse search over cosine-only for knowledge_v2
<!-- rag_chunk_meta chunk_type=decision tags=[homelab, vm-b1, qdrant, hybrid-search, rrf, decision, adr] -->

### Context
knowledge_v2 Qdrant collection on VM B1 uses hybrid retrieval combining dense semantic vectors (nomic-embed-text, 768d) and sparse BM25 vectors (djb2 tokenizer). Results are fused via Reciprocal Rank Fusion (RRF).
### Problem
Cosine-only semantic search misses exact keyword matches for error codes, Docker command names, config keys, and port numbers that appear verbatim in knowledge chunks.
### Decision
Hybrid RRF chosen over cosine-only. Dense excels at conceptual queries ("why did X fail"); sparse BM25 excels at exact-match queries ("error 422 Qdrant", "SCORE_THRESHOLD 0.002"). RRF fusion combines both signals without tuning weights manually.
### Alternatives Rejected
- Cosine-only: misses exact keyword matches for error codes and command names.
- Qdrant server-side BM25 inference: not supported in Qdrant v1.x for custom embedding models.
- Full-text search only: misses semantic similarity for conceptual queries.
### Key Facts
- Dense vector: nomic-embed-text 768d cosine, named "dense" in collection config.
- Sparse vector: djb2 tokenizer computed client-side in push-to-qdrant.sh, named "sparse".
- RRF formula: score = sum(1 / (rank + 60)) across dense and sparse result legs.
- SCORE_THRESHOLD for RRF results must be lower (around 0.002) vs cosine-only (around 0.3).
- Hybrid query uses Qdrant prefetch: two legs (dense and sparse), then fusion=rrf at top level.

## CHUNK 2: Decision: Qdrant over other vector databases for homelab knowledge base
<!-- rag_chunk_meta chunk_type=decision tags=[homelab, vm-b1, qdrant, decision, adr, vector-db] -->

### Context
homelab RAG knowledge base required a vector database that supports hybrid search (dense plus sparse), is self-hostable on VM B1, and has low operational overhead for a single-person homelab.
### Problem
Multiple vector database options exist (pgvector, Chroma, Weaviate, Pinecone, Milvus). Choosing the wrong one means rebuilding the collection if sparse vector support is added later.
### Decision
Qdrant chosen. It natively supports named vectors (multiple vector types per point in a single collection) and sparse vectors (SparseVectorConfig) required for client-side BM25 hybrid search. Fully self-hostable as Docker container with persistent volume. REST API is clean and well-documented.
### Alternatives Rejected
- pgvector: no sparse vector support, requires PostgreSQL overhead.
- Chroma: no sparse vector support in v0.x.
- Weaviate: heavier operationally, module system adds complexity.
- Pinecone: cloud-only, per-operation billing, data leaves homelab.
- Milvus: more complex deployment (requires etcd and MinIO).
### Key Facts
- Qdrant container: qdrant/qdrant:v1.13.4 on VM B1 port 6333.
- REST API base: http://192.168.18.199:6333, api-key header required on all requests.
- Named vector config enables dense (768d cosine) and sparse (dot product) in one collection.
- Cannot add sparse vector config to existing collection -- must create new collection (critical constraint).
- Data persisted in Docker named volume, survives container restart and upgrade.

## CHUNK 3: Decision: Ollama for local model inference over cloud API providers
<!-- rag_chunk_meta chunk_type=decision tags=[homelab, vm-b1, ollama, decision, adr, embedding, llm] -->

### Context
homelab RAG pipeline requires an embedding model to vectorize knowledge chunks and an LLM for answer generation (Pipeline B). Choice between local inference (Ollama) and cloud API (OpenAI, Cohere, HuggingFace Inference API).
### Problem
Cloud API for embeddings creates privacy risk (knowledge chunks leave homelab), per-token billing, latency over internet vs LAN, and dependency on external availability.
### Decision
Ollama chosen for local inference. All embedding and LLM calls stay on VM B1 (LAN, no internet egress). No per-token billing. LAN inference latency is ~50ms vs ~200-500ms for external API. Models available via simple pull command. nomic-embed-text and llama3.2 both available via Ollama.
### Alternatives Rejected
- OpenAI API: data leaves homelab, per-token billing, internet dependency.
- Cohere: same issues as OpenAI.
- HuggingFace Inference API: same issues.
- Raw PyTorch / vLLM: higher operational complexity vs Ollama's simple HTTP API.
### Key Facts
- Ollama endpoint: http://192.168.18.199:11434 (Docker container on VM B1, LAN only).
- Embedding call: POST /api/embeddings with JSON body {"model": "nomic-embed-text", "prompt": "..."}.
- No authentication required on Ollama endpoint (LAN-only, not exposed externally).
- Model must be pre-pulled inside Ollama container: ollama pull nomic-embed-text.
- GPU not available on VM B1 -- inference runs on CPU, acceptable for embedding workloads.

## CHUNK 4: Decision: nomic-embed-text as embedding model for knowledge_v2 collection
<!-- rag_chunk_meta chunk_type=decision tags=[homelab, vm-b1, ollama, embedding, nomic-embed-text, decision, adr] -->

### Context
knowledge_v2 Qdrant collection indexes all homelab knowledge chunks using a single embedding model. Changing the model after indexing requires recreating the collection and re-embedding all points.
### Problem
Embedding model choice determines vector dimension (which locks the collection schema), retrieval quality, inference speed on CPU, and availability via Ollama.
### Decision
nomic-embed-text chosen. Produces 768-dimensional embeddings, benchmarks well on retrieval tasks (MTEB leaderboard), available via Ollama pull (no internet from VM B1 needed after initial pull), Apache 2.0 licensed. Dimension 768 is a standard BERT-family size -- well-supported across tooling.
### Alternatives Rejected
- mxbai-embed-large (1024d): larger dimension increases storage and latency without proportional quality gain for homelab chunk sizes.
- all-minilm (384d): lower dimension reduces quality for longer chunks.
- OpenAI text-embedding-3-small: cloud dependency, data leaves homelab.
- bge-m3: heavier model, slower CPU inference on VM B1.
### Key Facts
- Model name: nomic-embed-text, output dimension: 768, distance: Cosine.
- Qdrant vector config: {"size": 768, "distance": "Cosine"} for the "dense" named vector.
- The model uses its own tokenizer -- djb2 is NOT the tokenizer (djb2 is only for sparse BM25 vectors).
- Changing embedding model is a breaking change -- requires collection recreation and full re-embed.
- Model size: ~274MB, pulled once into Ollama container and persisted in Ollama volume.

## CHUNK 5: Decision: n8n as orchestrator for RAG knowledge ingest pipeline
<!-- rag_chunk_meta chunk_type=decision tags=[homelab, vm-b1, n8n, decision, adr, rag-pipeline, orchestrator] -->

### Context
RAG knowledge chunks captured on laptop (via rag add CLI) must be embedded and upserted into Qdrant knowledge_v2 on VM B1. An orchestrator is needed to handle the embed-then-upsert workflow reliably.
### Problem
Need an orchestrator that: runs on VM B1 without cloud dependency, provides visibility into each workflow step, handles Ollama and Qdrant HTTP calls, supports webhook trigger from laptop push script, and is maintainable long-term.
### Decision
n8n chosen. Visual workflow editor enables rapid iteration without code changes. HTTP Request nodes handle Ollama /api/embeddings and Qdrant upsert calls natively. Webhook trigger allows push-to-qdrant.sh on laptop to POST chunks and receive result. Runs in Docker on VM B1. Retry logic and error visibility built-in.
### Alternatives Rejected
- Apache Airflow: heavy deployment (requires PostgreSQL, Celery), overkill for single workflow.
- Custom Python script: would work but no visibility, no retry logic, requires manual maintenance.
- Prefect: cloud-managed control plane by default, adds external dependency.
- GitHub Actions: requires internet access from VM B1 for runner, VM B1 has no internet egress.
### Key Facts
- n8n runs in Docker on VM B1 port 5678, data persisted in Docker named volume.
- Webhook endpoint receives POST from push-to-qdrant.sh with chunk body and metadata.
- n8n blocks env vars in expressions by default -- use explicit $env() or Code node.
- n8n Code node sandbox blocks fetch and axios -- use HTTP Request node for outbound calls.
- Workflow JSON exported and version-controlled for reproducibility.

## CHUNK 6: Feature: rag-gateway-mini ASP.NET Core 9 RAG query gateway architecture
<!-- rag_chunk_meta chunk_type=feature tags=[homelab, vm-b1, dotnet, rag-gateway, aspnetcore, feature] -->

### Context
rag-gateway-mini is an ASP.NET Core 9 REST API on VM B1 that provides a RAG query endpoint for the homelab knowledge base. Repo: github.com/figulazmi/rag-gateway-mini, deployed at http://192.168.18.199:5200.
### Feature
Accepts a query string, embeds it via Ollama (nomic-embed-text), performs hybrid RRF search on Qdrant knowledge_v2, and returns ranked chunks with metadata. Architecture follows Clean Architecture: Controllers/ (RagController handles HTTP), Application/ (Services, Interfaces, DTOs), Infrastructure/ (AI for Ollama embed, Configuration for Qdrant settings, Helpers). Uses Serilog for structured logging (outputs to Seq at port 5341) and Scalar for interactive API docs at /scalar/.
### Files Modified
- src/Controllers/RagController.cs -- query endpoint
- src/Application/Services/ -- query orchestration
- src/Infrastructure/AI/ -- OllamaEmbeddingService
- src/Infrastructure/Configuration/ -- Qdrant and Ollama settings
- src/Program.cs -- DI registration, health check, Scalar, Serilog
- src/docker-compose.yml -- container definition
### Key Facts
- Health endpoint: GET /health, registered via MapHealthChecks (not auto-registered).
- Scalar UI: /scalar/ for interactive API testing in browser.
- Build context is repo root (not src/) so Directory.Packages.props is included in Docker build.
- Secrets (QdrantApiKey) loaded from /opt/rag-gateway/appsettings.Production.json volume mount.
- Deployed port: 5200 on VM B1 LAN (192.168.18.199:5200).

## CHUNK 7: Feature: Qdrant knowledge_v2 collection named vectors dense and sparse hybrid config
<!-- rag_chunk_meta chunk_type=feature tags=[homelab, vm-b1, qdrant, hybrid-search, named-vectors, feature, knowledge-base] -->

### Context
knowledge_v2 is the primary Qdrant collection on VM B1 storing all homelab RAG chunks. Uses named vectors to support both dense semantic search and sparse BM25 keyword search in a single collection.
### Feature
Each Qdrant point has two named vectors: "dense" (nomic-embed-text 768d float, cosine distance) and "sparse" (djb2 BM25 sparse vector, dot product). Payload fields per point: chunk_type, topic, project, tags, source, body, date, status. Hybrid queries use two prefetch legs (dense and sparse with limit 20 each), fused at top level via RRF. Project filter applied as payload must-match filter to scope per project namespace.
### Key Facts
- Collection name: knowledge_v2 (legacy "knowledge" collection deprecated, do not use).
- Dense vector: {"size": 768, "distance": "Cosine"}, named "dense".
- Sparse vector: SparseVectorConfig dot product, named "sparse", client-side djb2 tokenizer.
- Cannot add sparse vector config to an existing Qdrant collection -- collection must be recreated.
- Hybrid prefetch query: [{"query": dense_vec, "using": "dense", "limit": 20}, {"query": sparse_vec, "using": "sparse", "limit": 20}] with top-level {"fusion": "rrf"}.
- Project namespace filter: {"must": [{"key": "project", "match": {"value": "homelab"}}]}.
- api-key header required on every Qdrant REST request (value in ~/.rag_config.json on VM B1).

## CHUNK 8: Feature: RAG auto-capture toolchain rag_capture.py rag CLI and push-to-qdrant.sh
<!-- rag_chunk_meta chunk_type=feature tags=[homelab, vm-b1, python, rag-capture, push-to-qdrant, feature, toolchain] -->

### Context
homelab knowledge capture pipeline runs on Windows laptop (Claude Code) and VM B1. Python CLI (rag_capture.py accessed via rag alias) captures knowledge chunks from Claude Code sessions and pushes them to Qdrant via n8n webhook.
### Feature
rag_capture.py provides: rag add (write draft chunk to ~/scripts/.rag_drafts/), rag merge (combine all drafts into dated .md file with per-chunk metadata comments embedded), rag checkpoint (save in-progress session state to .claude/checkpoints/), rag resume (load latest open checkpoint), rag promote (convert checkpoint to permanent knowledge chunk). push-to-qdrant.sh reads merged .md, splits on ## CHUNK N: headers, extracts per-chunk metadata from comment markers, embeds via Ollama, upserts to Qdrant via n8n webhook.
### Key Facts
- Draft storage: ~/scripts/.rag_drafts/ (one .md file per rag add call, numbered chunk_NNN.md).
- Merged output: ~/scripts/YYYY-MM-DD-[slug].md (input to push-to-qdrant.sh).
- Per-chunk metadata comment format: inside chunk body AFTER ## CHUNK N: header line.
  Format: comment rag_chunk_meta chunk_type=X tags=[a,b,c] (HTML comment syntax).
- Comment must appear AFTER the header line (inside chunk), not before it (off-by-one bug fixed 2026-04-25).
- push-to-qdrant.sh splits on regex ^##[space]CHUNK to isolate each chunk.
- n8n webhook URL and Qdrant api-key stored in ~/.rag_config.json on VM B1 -- must use localhost not external IP inside Docker network.
- Angle brackets in chunk content will cause bash redirect errors in push script -- avoid them.

## CHUNK 9: Feature: MCP qdrant-knowledge server for Claude Code session context injection
<!-- rag_chunk_meta chunk_type=feature tags=[homelab, vm-b1, mcp, qdrant, claude-code, feature, knowledge-base] -->

### Context
Claude Code sessions on Windows laptop need access to homelab knowledge base (stored in Qdrant on VM B1) without reading source files. A custom MCP server bridges Claude Code and Qdrant.
### Feature
qdrant-mcp-server-v2.js is a Node.js MCP server running on VM B1. It exposes the search_knowledge tool with required params: query (string, min 8 words) and project (enum: homelab or petrochina-eproc). Claude Code connects via SSH stdio transport: Claude Code spawns an SSH process to VM B1 and communicates over stdin/stdout. Server performs hybrid RRF query on knowledge_v2, applies project payload filter, returns top-limit scored chunks. Tool schema is deferred by default in Claude Code -- must call ToolSearch with select:mcp__qdrant-knowledge__search_knowledge at every session start before the tool can be called.
### Key Facts
- MCP server path on VM B1: ~/scripts/qdrant-mcp-server-v2.js (or configured path).
- Transport: SSH stdio via Tailscale (100.120.249.99) -- no open ports needed beyond SSH.
- Claude Code settings.json MCP entry: mcpServers.qdrant-knowledge with command=ssh, args pointing to Node.js server on VM B1.
- Tool is deferred: ToolSearch must be called at session start to load schema before search_knowledge can be invoked.
- Query minimum 8 words for quality hybrid retrieval -- shorter queries degrade sparse BM25 signal.
- Project filter scopes results to homelab or petrochina-eproc namespace in knowledge_v2 payload.

## CHUNK 10: Feature: n8n Pipeline A pure retrieval vs Pipeline B RAG with LLM answer synthesis
<!-- rag_chunk_meta chunk_type=feature tags=[homelab, vm-b1, n8n, rag-pipeline, llm, feature, architecture] -->

### Context
rag-gateway-mini supports two query modes via n8n workflows on VM B1: Pipeline A returns raw retrieved chunks, Pipeline B uses an LLM to synthesize a natural language answer from retrieved context.
### Feature
Pipeline A: webhook receives query -> Ollama embed -> Qdrant hybrid RRF search -> return top-K chunks as JSON array (no LLM call). Low latency, deterministic output. Used by MCP server (search_knowledge tool calls Pipeline A). Pipeline B: same as A but adds LLM call (Ollama llama3.2) with retrieved chunks as context, returns synthesized answer string plus source chunks. Higher latency due to LLM generation step. Used when end-user wants a direct answer rather than raw chunks. Both pipelines share the same Qdrant query logic; they diverge only at the final response step.
### Key Facts
- Pipeline A: returns chunks array, no LLM, MCP qdrant-knowledge server uses this path.
- Pipeline B: returns answer string plus source chunks, calls POST http://192.168.18.199:11434/api/generate.
- Both pipelines query knowledge_v2 with hybrid RRF and project payload filter.
- LLM for Pipeline B: llama3.2 via Ollama on VM B1 (CPU inference, no GPU).
- Choosing between pipelines: use A when caller processes chunks further; use B when end-user wants a direct answer.
- Pipeline A/B diagrams documented in docs/RAG_PIPELINE_A_B_DIAGRAMS.md in rag-gateway-mini repo.

## CHUNK 11: Runbook: force Qdrant HNSW indexing by patching indexing_threshold to 0
<!-- rag_chunk_meta chunk_type=runbook tags=[homelab, vm-b1, qdrant, indexing, runbook, hnsw] -->

### Context
Qdrant knowledge_v2 collection on VM B1 showed 199/295 indexed_vectors_count. Background optimizer had not converted recent appendable segments to HNSW-indexed immutable segments.
### Problem
New points (from recent rag add batches) land in appendable segments that are not HNSW-indexed. Qdrant's default indexing_threshold (typically 20,000) is too high for a small collection to auto-trigger HNSW build.
### Solution
Patch the collection's indexing_threshold to 0 via REST API. This tells the optimizer to HNSW-index all segments regardless of size. The optimizer runs asynchronously and may take 30-120s to complete a pass.
```bash
ssh figulazmi@192.168.18.199 'curl -s -X PATCH \
  "http://localhost:6333/collections/knowledge_v2" \
  -H "api-key: <KEY>" \
  -H "Content-Type: application/json" \
  -d "{\"optimizers_config\": {\"indexing_threshold\": 0}}"'
```
Verify after: indexed_vectors_count should approach points_count.
### Key Facts
- indexed_vectors_count tracks HNSW-indexed dense vectors only -- sparse BM25 inverted index is separate and covers ALL points regardless of this count.
- At under 1000 points, brute-force fallback for unindexed segments has zero practical impact on search quality or speed.
- indexing_threshold=0 is a permanent collection setting; it persists across restarts and applies to all future inserts.
- optimizer_status "ok" means the optimizer finished its current pass, not that all segments are indexed -- appendable segments may remain unindexed until next pass.
- To re-check: GET /collections/knowledge_v2 and read points_count vs indexed_vectors_count.

---

## SESSION METADATA

- **Total chunks**: 11
- **Qdrant collection**: knowledge_v2
- **Generated by**: rag_capture.py v2 -- Incremental Capture
- **Author**: Figur Ulul Azmi
- **Date**: 2026-04-25
- **Unresolved items**: (fill manually if needed)