#!/usr/bin/env bash
# =============================================================================
# qdrant-visualize.sh
# Fix for: "Please select a valid vector name (by `using`), default vector is
#           not defined"
#
# Root cause:
#   knowledge_v2 uses NAMED vectors ("dense" / "sparse").
#   Qdrant's /points/visualize endpoint requires `using` to be set explicitly.
#   Omitting it (or leaving it empty) causes the error above.
#
# Usage:
#   bash scripts/qdrant-visualize.sh                          # 100 points, localhost
#   bash scripts/qdrant-visualize.sh --limit 200
#   bash scripts/qdrant-visualize.sh --url http://192.168.18.169:6333
#   bash scripts/qdrant-visualize.sh --project homelab --limit 50
# =============================================================================

set -euo pipefail

# ─── DEFAULTS ────────────────────────────────────────────────────────────────
QDRANT_URL="http://localhost:6333"
QDRANT_API_KEY="${QDRANT_API_KEY:?QDRANT_API_KEY not set (source ~/.config/qdrant-knowledge.env)}"
COLLECTION="knowledge_v2"
VECTOR_NAME="dense"          # FIX: always specify using="dense" for named-vector collections
LIMIT=100
PROJECT_FILTER=""

# ─── ARGS ────────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)        QDRANT_URL="$2";       shift 2 ;;
    --api-key)    QDRANT_API_KEY="$2";   shift 2 ;;
    --collection) COLLECTION="$2";       shift 2 ;;
    --limit)      LIMIT="$2";            shift 2 ;;
    --project)    PROJECT_FILTER="$2";   shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# ─── BUILD REQUEST ───────────────────────────────────────────────────────────
# using="dense" is REQUIRED — knowledge_v2 has no unnamed/default vector.
# Without it Qdrant returns: "Please select a valid vector name (by `using`)"

if [[ -n "$PROJECT_FILTER" ]]; then
  BODY=$(jq -n \
    --arg using "$VECTOR_NAME" \
    --argjson limit "$LIMIT" \
    --arg project "$PROJECT_FILTER" \
    '{
      using: $using,
      limit: $limit,
      filter: {
        must: [{ key: "project", match: { value: $project } }]
      }
    }')
else
  BODY=$(jq -n \
    --arg using "$VECTOR_NAME" \
    --argjson limit "$LIMIT" \
    '{
      using: $using,
      limit: $limit
    }')
fi

# ─── CALL QDRANT ─────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Qdrant Visualize — ${COLLECTION}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  URL        : ${QDRANT_URL}"
echo "  Collection : ${COLLECTION}"
echo "  using      : ${VECTOR_NAME}   ← named vector (FIX for the error)"
echo "  Limit      : ${LIMIT}"
[[ -n "$PROJECT_FILTER" ]] && echo "  Project    : ${PROJECT_FILTER}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESPONSE=$(curl -sf \
  -X POST \
  "${QDRANT_URL}/collections/${COLLECTION}/points/visualize" \
  -H "Content-Type: application/json" \
  -H "api-key: ${QDRANT_API_KEY}" \
  -d "$BODY")

STATUS=$(echo "$RESPONSE" | jq -r '.status // "unknown"' 2>/dev/null)

if echo "$RESPONSE" | jq -e '.status.error' > /dev/null 2>&1; then
  echo "❌ Qdrant error:"
  echo "$RESPONSE" | jq '.'
  exit 1
fi

POINT_COUNT=$(echo "$RESPONSE" | jq '.result | length' 2>/dev/null || echo "?")
echo "✅ Visualize data returned: ${POINT_COUNT} points"
echo ""

# Save to file for inspection
OUTPUT_FILE=".claude/reports/visualize-$(date +%Y%m%d-%H%M%S).json"
mkdir -p .claude/reports
echo "$RESPONSE" | jq '.' > "$OUTPUT_FILE"
echo "   Saved : $OUTPUT_FILE"
echo ""

# Print first 3 points as preview
echo "── Preview (first 3 vectors) ──────────────────"
echo "$RESPONSE" | jq '.result[:3][] | {vector_preview: .vector[:5], payload_keys: (.payload | keys)}'
echo ""
