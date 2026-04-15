---
id: 2026-04-15-n8n-contextual-retrieval-prepend-deploym-001
date: 2026-04-15
source: claude-code-cli
project: homelab
chunk_type: debug
topic: n8n Contextual Retrieval Prepend Deployment Verification
tags: [homelab, vm-b1, n8n, qdrant, contextual-retrieval, ollama, embedding, verification]
related: []
session_type: 
environment: homelab
git_branch: 
status: implemented
chunk_source: code
---

## CHUNK 1: n8n Contextual Retrieval Prepend Deployment Verification

### Context
Deploying P1.2 contextual retrieval prepend for knowledge_v2: Validate & Clean node builds embed_content, Ollama node embeds embed_content, payload keeps raw content. After user imported and published the new workflow, stored dense vectors still matched raw-content embeddings rather than prepended embeddings.

### Problem
Cosine similarity check: cos(stored_vector, embed(raw_content)) = 1.000000 while cos(stored_vector, embed(prepended_content)) = 0.951857. This indicates the active webhook is still routing to a workflow that feeds content (not embed_content) to Ollama, even though the updated Validate and Clean node code was confirmed present.

### Solution
Verification script (Python plus Qdrant scroll plus Ollama embeddings API) isolates the issue to the Ollama node binding. Fix path: in n8n UI, open Ollama nomic-embed-text node, ensure prompt Body Parameter equals the expression ={{ $json.embed_content }}, then Save workflow and toggle Active off then on to force webhook re-registration. Duplicate workflows owning the same webhook path knowledge-ingest can also shadow the new one.

### Key Facts
- Stored dense vector exactly equaling embed(raw_content) proves the Ollama node received raw content, not embed_content
- n8n does not always re-register webhook on Save alone; toggle Active off then on is required
- Qdrant scroll with with_vector=["dense"] retrieves stored named vector for offline comparison
- n8n REST /rest/workflows requires auth; without n8n API key or docker sudo access, verification must be done via UI
- Idempotent upsert by deterministic chunk ID means re-pushing the same file overwrites; delta=0 does not prove the new workflow ran

### Code
```python
scroll = post(f"{QDRANT}/collections/knowledge_v2/points/scroll",
    {"filter":{"must":[{"key":"string_id","match":{"value":SID}}]},
     "limit":1,"with_payload":True,"with_vector":["dense"]},
    {"api-key":KEY})
stored = scroll["result"]["points"][0]["vector"]["dense"]
```

## CHUNK 2: n8n Env Var Access Fix for Qdrant Auth in Expressions

### Context
n8n workflow knowledge_v2 on VM B1 ai-stack uses `={{ $env.QDRANT_API_KEY }}` in the api-key header of the Qdrant upsert HTTP node. The variable was exported to the container via docker compose environment block reading from /opt/homelab/ai-stack/qdrant/.env.

### Problem
Qdrant upsert returned "Authorization failed - Invalid API key or JWT". `docker exec n8n printenv QDRANT_API_KEY` showed the value correctly, yet n8n expression still produced an empty header. Reason: n8n v1.x blocks `$env.*` access inside node expressions by default as a hardening measure.

### Solution
Add `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` to the n8n service environment in docker-compose.stage2.yml, then `docker compose up -d n8n`. After restart, `{{ $env.QDRANT_API_KEY }}` resolves correctly and Qdrant upserts succeed. Workflow JSON committed with the expression instead of a hardcoded placeholder, so the secret never enters git.

### Key Facts
- n8n default behavior hides process env from expression engine; a single flag lifts the block
- `docker exec n8n printenv` proves the env var reaches the container but does NOT prove expressions can read it
- Qdrant returns "Invalid API key" for an empty header, indistinguishable from a truly wrong key
- Verification command from inside container: `docker exec n8n wget -qO- --header="api-key: $QDRANT_API_KEY" http://qdrant:6333/collections/knowledge_v2`

### Code
```yaml
n8n:
  environment:
    - QDRANT_API_KEY=${QDRANT_API_KEY}
    - N8N_BLOCK_ENV_ACCESS_IN_NODE=false
```

## CHUNK 3: P1.2 Contextual Retrieval Verification via Cosine Similarity

### Context
P1.2 of the knowledge_v2 roadmap adds a document-context prepend to the embedding input so Ollama nomic-embed-text receives `embed_content` instead of raw `content`. The prepend happens in the n8n Validate & Clean code node; raw content remains in the Qdrant payload. This test proves the active workflow actually feeds `embed_content` to Ollama and measures impact on retrieval quality.

### Problem
A previous deployment attempt left the Ollama node still reading `{{ $json.content }}`. Stored dense vectors matched `embed(raw_content)` at cosine 1.000. Without a ground-truth check, n8n Save alone can look successful while the active webhook still shadows an old binding.

### Solution
Three-gate procedure. Gate 1: push a probe summary via push-to-qdrant.sh, expect 200 OK. Gate 2: run a Python script that scrolls the stored dense vector by string_id, rebuilds the same prepend string that n8n Validate & Clean produces, embeds both raw and prepended via Ollama, compares cosine. Pass when `cos(stored, prepended) > 0.99` AND `cos(stored, raw) < 0.99`. Gate 3: re-ingest `.claude/summaries/*.md` to rewrite all dense vectors; deterministic chunk IDs keep the upsert idempotent. Gate 4: run eval-retrieval-quality.py and compare aggregate against baseline.

### Key Facts
- Retest result: cos(stored,prepended)=1.000000, cos(stored,raw)=0.728482 on probe point
- Hybrid Hit@1 jumped 0.60 to 1.00 and MRR 0.65 to 1.00 after full corpus re-ingest
- Dense NDCG@5 +0.023, Sparse NDCG@5 +0.083; Hybrid NDCG@5 slight -0.008 within noise
- Qdrant scroll with `with_vector=["dense"]` returns the stored named vector for offline comparison
- Re-ingest over deterministic IDs is idempotent; delta in points_count only reflects genuinely new chunks

### Code
```python
scroll = post(f"{QDRANT}/collections/knowledge_v2/points/scroll",
  {"filter":{"must":[{"key":"string_id","match":{"value":SID}}]},
   "limit":1,"with_payload":True,"with_vector":["dense"]},
  {"api-key":KEY})
stored = scroll["result"]["points"][0]["vector"]["dense"]
prepended = (f"This chunk is from project {project}, type {chunk_type}, "
             f"topic \"{topic}\", tagged {tags}. Session date {date}. "
             f"Content: {raw_content}")
```

---

## SESSION METADATA

- **Total chunks**: 3
- **Qdrant collection**: knowledge_v2
- **Generated by**: rag_capture.py v2 — Incremental Capture
- **Author**: Figur Ulul Azmi
- **Date**: 2026-04-15
- **Unresolved items**: (fill manually if needed)