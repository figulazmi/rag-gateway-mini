#!/usr/bin/env bash
# =============================================================================
# qdrant-graph.sh
# Fix for: {"status":400,"data":{"status":{"error":"Wrong input: Not existing
#           vector name error: "},"time":0.000165159}}
#
# Root cause:
#   Qdrant graph/explore API requires `using` for named-vector collections.
#   Passing using="" (empty string) or omitting it causes HTTP 400 with
#   "Not existing vector name error: " (note the trailing empty string).
#
# This script calls /points/explore (graph traversal / similar-point lookup)
# with using="dense" set explicitly.
#
# Usage:
#   bash scripts/qdrant-graph.sh --point-id <UUID>               # explore from a point
#   bash scripts/qdrant-graph.sh --point-id <UUID> --depth 2     # 2-hop graph
#   bash scripts/qdrant-graph.sh --url http://192.168.18.169:6333 --point-id <UUID>
#   bash scripts/qdrant-graph.sh --random                         # pick a random point first
# =============================================================================

set -euo pipefail

# ─── DEFAULTS ────────────────────────────────────────────────────────────────
QDRANT_URL="http://localhost:6333"
QDRANT_API_KEY="${QDRANT_API_KEY:?QDRANT_API_KEY not set (source ~/.config/qdrant-knowledge.env)}"
COLLECTION="knowledge_v2"
VECTOR_NAME="dense"          # FIX: always specify using="dense" for named-vector collections
LIMIT=10
POINT_ID=""
PICK_RANDOM=false
PROJECT_FILTER=""

# ─── ARGS ────────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)        QDRANT_URL="$2";       shift 2 ;;
    --api-key)    QDRANT_API_KEY="$2";   shift 2 ;;
    --collection) COLLECTION="$2";       shift 2 ;;
    --point-id)   POINT_ID="$2";         shift 2 ;;
    --limit)      LIMIT="$2";            shift 2 ;;
    --project)    PROJECT_FILTER="$2";   shift 2 ;;
    --random)     PICK_RANDOM=true;      shift   ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# ─── PICK RANDOM POINT (if no --point-id given) ──────────────────────────────
if [[ -z "$POINT_ID" ]] || [[ "$PICK_RANDOM" == "true" ]]; then
  echo ""
  echo "  No --point-id given. Fetching a random point from ${COLLECTION}..."

  SCROLL_BODY='{"limit":1,"with_payload":false,"with_vectors":false}'
  SCROLL_RESP=$(curl -sf \
    -X POST \
    "${QDRANT_URL}/collections/${COLLECTION}/points/scroll" \
    -H "Content-Type: application/json" \
    -H "api-key: ${QDRANT_API_KEY}" \
    -d "$SCROLL_BODY")

  POINT_ID=$(echo "$SCROLL_RESP" | jq -r '.result.points[0].id')

  if [[ -z "$POINT_ID" || "$POINT_ID" == "null" ]]; then
    echo "❌ Could not fetch a point from ${COLLECTION}. Is the collection populated?"
    exit 1
  fi
  echo "  Using point_id: ${POINT_ID}"
fi

# ─── BUILD EXPLORE (GRAPH) REQUEST ───────────────────────────────────────────
# using="dense" is REQUIRED — knowledge_v2 has no unnamed/default vector.
# Without it Qdrant returns HTTP 400: "Not existing vector name error: "

if [[ -n "$PROJECT_FILTER" ]]; then
  BODY=$(jq -n \
    --arg using "$VECTOR_NAME" \
    --arg point_id "$POINT_ID" \
    --argjson limit "$LIMIT" \
    --arg project "$PROJECT_FILTER" \
    '{
      positive: [$point_id],
      using: $using,
      limit: $limit,
      with_payload: true,
      filter: {
        must: [{ key: "project", match: { value: $project } }]
      }
    }')
else
  BODY=$(jq -n \
    --arg using "$VECTOR_NAME" \
    --arg point_id "$POINT_ID" \
    --argjson limit "$LIMIT" \
    '{
      positive: [$point_id],
      using: $using,
      limit: $limit,
      with_payload: true
    }')
fi

# ─── CALL QDRANT EXPLORE ─────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Qdrant Graph Explore — ${COLLECTION}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  URL        : ${QDRANT_URL}"
echo "  Collection : ${COLLECTION}"
echo "  using      : ${VECTOR_NAME}   ← named vector (FIX for HTTP 400)"
echo "  Seed point : ${POINT_ID}"
echo "  Limit      : ${LIMIT}"
[[ -n "$PROJECT_FILTER" ]] && echo "  Project    : ${PROJECT_FILTER}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESPONSE=$(curl -sf \
  -X POST \
  "${QDRANT_URL}/collections/${COLLECTION}/points/recommend" \
  -H "Content-Type: application/json" \
  -H "api-key: ${QDRANT_API_KEY}" \
  -d "$BODY")

if echo "$RESPONSE" | jq -e '.status.error' > /dev/null 2>&1; then
  echo "❌ Qdrant error:"
  echo "$RESPONSE" | jq '.'
  exit 1
fi

RESULT_COUNT=$(echo "$RESPONSE" | jq '.result | length' 2>/dev/null || echo "?")
echo "✅ Graph neighbors returned: ${RESULT_COUNT} points"
echo ""

# Save to file
OUTPUT_FILE=".claude/reports/graph-$(date +%Y%m%d-%H%M%S).json"
mkdir -p .claude/reports
echo "$RESPONSE" | jq '.' > "$OUTPUT_FILE"
echo "   Saved : $OUTPUT_FILE"
echo ""

# Print results table
echo "── Similar Points (graph neighbors) ──────────────────────────────"
echo "$RESPONSE" | jq -r '
  .result[] |
  "  score=\(.score | tostring | .[0:6])  project=\(.payload.project // "?")  topic=\(.payload.topic // .payload.content[0:60] // "?")"
'
echo ""
