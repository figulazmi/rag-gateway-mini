import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const QDRANT_URL = "http://localhost:6333";
const QDRANT_API_KEY = process.env.QDRANT_API_KEY;
if (!QDRANT_API_KEY) {
  console.error("QDRANT_API_KEY env var not set");
  process.exit(1);
}
const OLLAMA_URL = "http://localhost:11434";
const COLLECTION = "knowledge_v2";
const SCORE_THRESHOLD = 0.5;
const RETRY_THRESHOLD = 0.6;
const NOT_FOUND_THRESHOLD = 0.65;   // top score below this → NOT FOUND IN RAG
const QUERY_MIN_WORDS = 8;
const QUERY_EXPANSION = "implementation details system behavior architecture";

// Session state — tracks whether search_knowledge was called this session
let sessionState = {
  hasSearched: false,
};

// RAG-FIRST enforcer — call this at the top of any tool that requires prior search
function enforceRagFirst(toolName) {
  if (!sessionState.hasSearched) {
    throw new Error(
      `RAG-FIRST VIOLATION: search_knowledge must be called before "${toolName}". ` +
      `Call search_knowledge with a descriptive query first.`
    );
  }
}

async function embedQuery(text) {
  const res = await fetch(`${OLLAMA_URL}/api/embeddings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: "nomic-embed-text", prompt: text }),
  });
  const data = await res.json();
  return data.embedding;
}

/**
 * Build sparse BM25 vector using djb2 hash.
 * Must match n8n JS, migrate-to-hybrid.py, and QdrantVectorSearchClient.cs BuildSparseVector().
 * Algorithm: h = 5381; for each char: h = ((h << 5) + h + charCode) & 0x7FFFFFFF
 */
function djb2Sparse(text) {
  const tokens = text.toLowerCase().match(/[a-z0-9]+/g) || [];
  const tf = {};
  for (const token of tokens) {
    let h = 5381;
    for (const ch of token) {
      h = (((h << 5) + h) + ch.charCodeAt(0)) & 0x7FFFFFFF;
    }
    tf[h] = (tf[h] || 0) + 1;
  }
  const indices = Object.keys(tf).map(Number);
  const values = indices.map(i => tf[i]);
  return { indices, values };
}

async function searchQdrant(denseVector, sparseVector, limit = 5, project = null, includePlanned = false) {
  const mustFilters = [];
  if (project) mustFilters.push({ key: "project", match: { value: project } });
  if (!includePlanned) mustFilters.push({ key: "status", match: { value: "implemented" } });

  const filterClause = mustFilters.length > 0 ? { must: mustFilters } : undefined;

  // Hybrid search using Qdrant Query API with RRF fusion
  const body = {
    prefetch: [
      {
        query: denseVector,
        using: "dense",
        limit: limit * 4,
        ...(filterClause && { filter: filterClause }),
      },
      {
        query: sparseVector,
        using: "sparse",
        limit: limit * 4,
        ...(filterClause && { filter: filterClause }),
      },
    ],
    query: { fusion: "rrf" },
    limit,
    with_payload: true,
  };

  const res = await fetch(`${QDRANT_URL}/collections/${COLLECTION}/points/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "api-key": QDRANT_API_KEY,
    },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return data.result?.points || [];
}

const server = new Server(
  { name: "qdrant-knowledge", version: "2.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "search_knowledge",
      description:
        "Search Qdrant knowledge base for context from previous Claude Code sessions about PetroChina.Eproc (.NET 9, Blazor, Clean Architecture, CQRS, MediatR, EF Core, Hangfire, LoginType auth). Returns IMPLEMENTED features only by default (status=implemented). Set include_planned=true to also retrieve PLANNED/design chunks.",
      inputSchema: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "Natural language query — minimum 8 words for quality retrieval",
          },
          project: {
            type: "string",
            description: "Project filter: 'petrochina-eproc' or 'homelab'. Required unless cross-project search.",
            enum: ["petrochina-eproc", "homelab"],
          },
          limit: {
            type: "number",
            description: "Max results (default 5)",
            default: 5,
          },
          include_planned: {
            type: "boolean",
            description: "Set true to include PLANNED/design chunks. Default false — only returns implemented features.",
            default: false,
          },
        },
        required: ["query", "project"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const toolName = request.params.name;

  if (toolName !== "search_knowledge") {
    enforceRagFirst(toolName);
    throw new Error(`Unknown tool: ${toolName}`);
  }

  const { query, project, limit = 5, include_planned = false } = request.params.arguments;

  // GUARD 1: Query presence
  if (!query || typeof query !== "string") {
    throw new Error("Query is required.");
  }

  // GUARD 2: Project required
  if (!project) {
    throw new Error(
      `RAG-FILTER REJECTED: project parameter is required. ` +
      `Use project="petrochina-eproc" or project="homelab".`
    );
  }

  // NORMALIZATION: Auto-expand short queries instead of rejecting them.
  const wordCount = query.trim().split(/\s+/).length;
  let effectiveQuery = query.trim();
  if (wordCount < QUERY_MIN_WORDS) {
    effectiveQuery = `${effectiveQuery} ${QUERY_EXPANSION}`;
    console.error(JSON.stringify({
      event: "rag_normalized",
      original: query,
      normalized: effectiveQuery,
      originalWordCount: wordCount,
      expandedWordCount: effectiveQuery.split(/\s+/).length,
      timestamp: new Date().toISOString(),
    }));
  }

  // SESSION STATE: mark search as performed
  sessionState.hasSearched = true;

  try {
    const denseVector = await embedQuery(effectiveQuery);
    const sparseVector = djb2Sparse(effectiveQuery);
    const results = await searchQdrant(denseVector, sparseVector, limit, project, include_planned);
    const filteredResults = results.filter(r => r.score >= SCORE_THRESHOLD);

    const scores = filteredResults.map((r) => r.score);
    const avgScore = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
    const topScore = scores.length > 0 ? Math.max(...scores) : 0;

    console.error(JSON.stringify({
      event: "rag_search",
      collection: COLLECTION,
      searchMode: "hybrid-rrf",
      query,
      effectiveQuery,
      wordCount,
      project,
      rawCount: results.length,
      filteredCount: filteredResults.length,
      avgScore,
      topScore,
      timestamp: new Date().toISOString(),
    }));

    // ONE-TIME RETRY — triggered when quality is low or no results
    let finalResults = filteredResults;
    let finalTopScore = topScore;

    if (avgScore < RETRY_THRESHOLD || filteredResults.length === 0) {
      const rewrittenQuery = effectiveQuery + " with detailed implementation context in system design";
      const retryDense = await embedQuery(rewrittenQuery);
      const retrySparse = djb2Sparse(rewrittenQuery);
      const retryRaw = await searchQdrant(retryDense, retrySparse, limit, project, include_planned);
      const retryFiltered = retryRaw.filter(r => r.score >= SCORE_THRESHOLD);
      const retryScores = retryFiltered.map(r => r.score);
      const retryAvgScore = retryScores.length > 0 ? retryScores.reduce((a, b) => a + b, 0) / retryScores.length : 0;
      const retryTopScore = retryScores.length > 0 ? Math.max(...retryScores) : 0;
      const improved = retryAvgScore > avgScore || retryFiltered.length > filteredResults.length;

      console.error(JSON.stringify({
        event: "rag_retry",
        originalQuery: effectiveQuery,
        rewrittenQuery,
        originalAvgScore: avgScore,
        retryAvgScore,
        improved,
      }));

      if (improved) {
        finalResults = retryFiltered;
        finalTopScore = retryTopScore;
      }
    }

    // NOT FOUND GATE
    if (finalResults.length === 0 || finalTopScore < NOT_FOUND_THRESHOLD) {
      const reason = finalResults.length === 0
        ? "no results after retry"
        : `top score ${finalTopScore.toFixed(3)} below threshold ${NOT_FOUND_THRESHOLD}`;
      console.error(JSON.stringify({
        event: "rag_not_found",
        query,
        effectiveQuery,
        reason,
        finalTopScore,
        timestamp: new Date().toISOString(),
      }));
      return {
        content: [{ type: "text", text: "NOT FOUND IN RAG\nrag_status: not_found" }],
      };
    }

    const formatted = finalResults
      .map((r, i) => {
        const p = r.payload;
        return `--- [${i + 1}] score: ${r.score.toFixed(3)} ---\nSource: ${p.source || "unknown"}\nTags: ${Array.isArray(p.tags) ? p.tags.join(", ") : (p.tags ? String(p.tags).replace(/[\[\]]/g, "").split(",").map(t => t.trim()).filter(Boolean).join(", ") : "")}\n\n${p.content}`;
      })
      .join("\n\n");

    return {
      content: [{ type: "text", text: `rag_status: found\n\n${formatted}` }],
    };
  } catch (err) {
    return {
      content: [{ type: "text", text: `Error querying Qdrant: ${err.message}` }],
      isError: true,
    };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
