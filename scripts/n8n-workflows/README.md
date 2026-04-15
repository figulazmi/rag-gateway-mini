# n8n Workflows

Exported n8n workflow definitions for the RAG knowledge pipeline.

## Files

- `ingest-knowledge-v2.json` — ingest chunks into Qdrant collection `knowledge_v2`. Hashes string_id to numeric point id, generates dense vector via Ollama `nomic-embed-text`, computes sparse BM25 via djb2 tokenizer, and upserts with payload including `status` field (default `implemented`, whitelist `implemented | planned | deprecated`).

## Import

1. Open n8n UI → Workflows → Import from File → select the JSON.
2. In node `Qdrant: Upsert Point`, replace the `api-key` header placeholder `<QDRANT_API_KEY>` with the actual key.
3. Activate the workflow. Webhook becomes available at `http://<n8n-host>:5678/webhook/knowledge-ingest`.

## Security

**Never commit the real api-key.** The JSON in this folder must always use the `<QDRANT_API_KEY>` placeholder. Past incident: `2026-04-14-qdrant-api-key-leak-scrub`. Rotate the key immediately if a literal value slips into a commit.

## Status Field

Every upserted point carries `payload.status`:
- `implemented` — default; code/feature is shipped and running.
- `planned` — design, roadmap, or ADR for work not yet built. Must be set explicitly in the webhook body.
- `deprecated` — retained for history but superseded.

The MCP server `qdrant-mcp-server-v2` filters `status=implemented` by default. Set `include_planned=true` to include planned chunks.
