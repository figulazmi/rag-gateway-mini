# RAG Gateway

A lightweight ASP.NET Core API that acts as a retrieval gateway between your LLM application and a Qdrant vector database. It embeds queries via Ollama and returns the most relevant knowledge chunks — no generation, pure deterministic retrieval.

---

## Architecture

```
Client → POST /rag/search → Ollama (embed query) → Qdrant (vector search) → filtered results
```

**Dependencies:**
- [Ollama](https://ollama.com) — embedding model server (default: `nomic-embed-text`)
- [Qdrant](https://qdrant.tech) — vector database

---

## Configuration

Edit `appsettings.json` (development) or `appsettings.Production.json` (production):

```json
{
  "RagGateway": {
    "OllamaBaseUrl": "http://localhost:11434",
    "QdrantBaseUrl": "http://localhost:6333",
    "OllamaModel": "nomic-embed-text",
    "QdrantCollection": "knowledge_v2",
    "QdrantApiKey": "",
    "ScoreThreshold": 0.55,
    "ResultLimit": 5
  }
}
```

| Key | Description | Default |
|-----|-------------|---------|
| `OllamaBaseUrl` | Ollama server URL | `http://localhost:11434` |
| `QdrantBaseUrl` | Qdrant server URL | `http://localhost:6333` |
| `OllamaModel` | Embedding model name | `nomic-embed-text` |
| `QdrantCollection` | Qdrant collection to search | `knowledge_v2` |
| `QdrantApiKey` | Qdrant API key (leave empty if none) | `""` |
| `ScoreThreshold` | Minimum similarity score to include a result | `0.55` |
| `ResultLimit` | Maximum number of results returned from Qdrant | `5` |

---

## Running locally

**Prerequisites:** .NET 9 SDK, Ollama running, Qdrant running.

```bash
dotnet run --project RagGateway.csproj
```

The API will be available at:
- HTTP: `http://localhost:5200`
- HTTPS: `https://localhost:7200`

Interactive API docs (Scalar UI): `http://localhost:5200/scalar/v1`

---

## Running with Docker

```bash
# Build and start
docker compose up -d

# View logs
docker compose logs -f rag-gateway
```

The service listens on port `5200`. Mount your production config:

```bash
# Create production config from template
cp appsettings.Production.json.template /opt/rag-gateway/appsettings.Production.json
# Edit the file with your real values, then start the container
```

---

## Endpoints

### `POST /rag/search`

Search the knowledge base. Returns results that pass the score threshold.

**Request body:**
```json
{
  "query": "how do I configure retry policy?",
  "project": "my-project"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | yes | Natural language question or search text |
| `project` | string | no | Filter results to a specific project/namespace stored in Qdrant payload |

**Response — found (`200 OK`):**
```json
{
  "status": "found",
  "query": "how do I configure retry policy?",
  "normalized_query": "how do I configure retry policy implementation details best practice",
  "results": [
    {
      "score": 0.82,
      "content": "To configure a retry policy...",
      "metadata": {
        "project": "my-project",
        "source": "docs/retry.md"
      }
    }
  ]
}
```

**Response — not found (`200 OK`):**
```json
{
  "status": "not_found",
  "message": "NOT FOUND IN RAG"
}
```

**Response — bad request (`400`):**
```json
{ "error": "Query is required." }
```

---

### `POST /rag/debug`

Returns ALL raw Qdrant results **before** threshold filtering. Use this to diagnose score values and tune `ScoreThreshold`.

**Request body:** same as `/rag/search`

**Response (`200 OK`):**
```json
{
  "normalized_query": "how do I configure retry policy implementation details best practice",
  "project_filter": "my-project",
  "threshold": 0.55,
  "total_raw_results": 5,
  "results_above_threshold": 2,
  "results": [
    {
      "score": 0.82,
      "content": "To configure a retry policy...",
      "metadata": { "project": "my-project" }
    },
    {
      "score": 0.41,
      "content": "Unrelated chunk...",
      "metadata": { "project": "my-project" }
    }
  ]
}
```

---

## curl examples

```bash
# Search
curl -s -X POST http://localhost:5200/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how to set up authentication", "project": "my-project"}' | jq

# Search without project filter
curl -s -X POST http://localhost:5200/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query": "database connection timeout"}' | jq

# Debug — see all raw scores
curl -s -X POST http://localhost:5200/rag/debug \
  -H "Content-Type: application/json" \
  -d '{"query": "retry policy configuration"}' | jq
```

---

## Query normalization

Short queries (fewer than 8 words) are automatically padded with neutral technical words (`implementation`, `details`, `best`, `practice`, ...) to produce a semantically richer embedding. The `normalized_query` field in the response always shows what was actually sent to Ollama.
