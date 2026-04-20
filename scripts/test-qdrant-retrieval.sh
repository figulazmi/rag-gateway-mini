#!/usr/bin/env bash
# =============================================================================
# test-qdrant-retrieval.sh
# Author  : Figur Ulul Azmi
# Target  : Qdrant MCP server on VM B1 via SSH
# Usage   : bash scripts/test-qdrant-retrieval.sh "query string" [limit]
# Example : bash scripts/test-qdrant-retrieval.sh "single device login" 5
# Output  : Formatted results + log saved to .claude/retrieval-tests/
# =============================================================================

set -euo pipefail

# =============================================================================
# ─── CONFIG ──────────────────────────────────────────────────────────────────
# =============================================================================

B1_LOCAL_IP="192.168.18.199"
B1_LOCAL_PORT="5678"
B1_TAILSCALE_IP="100.120.249.99"
B1_TAILSCALE_PORT="5678"
B1_SSH_USER="figulazmi"
B1_MCP_CMD="node /opt/mcp-servers/qdrant-knowledge/qdrant-mcp-server.js"
LOG_DIR=".claude/retrieval-tests"
DEFAULT_LIMIT=5

# =============================================================================
# ─── VALIDATION ──────────────────────────────────────────────────────────────
# =============================================================================

if [ $# -eq 0 ]; then
  echo ""
  echo "Usage  : bash scripts/test-qdrant-retrieval.sh \"query string\" [limit]"
  echo "Example: bash scripts/test-qdrant-retrieval.sh \"single device login\" 5"
  echo ""
  exit 1
fi

QUERY="$1"
LIMIT="${2:-$DEFAULT_LIMIT}"

# =============================================================================
# ─── NETWORK DETECTION ───────────────────────────────────────────────────────
# =============================================================================

detect_network() {
  if hostname 2>/dev/null | grep -qi "figulazmi"; then
    echo "local-b1"; return
  fi
  if curl -s --connect-timeout 2 "http://${B1_LOCAL_IP}:${B1_LOCAL_PORT}" \
     -o /dev/null 2>/dev/null; then
    echo "lan"; return
  fi
  if curl -s --connect-timeout 3 "http://${B1_TAILSCALE_IP}:${B1_TAILSCALE_PORT}" \
     -o /dev/null 2>/dev/null; then
    echo "tailscale"; return
  fi
  echo "unreachable"
}

NETWORK=$(detect_network)

case "$NETWORK" in
  "local-b1")
    SSH_TARGET=""
    NETWORK_LABEL="VM B1 (localhost)"
    ;;
  "lan")
    SSH_TARGET="${B1_SSH_USER}@${B1_LOCAL_IP}"
    NETWORK_LABEL="LAN (${B1_LOCAL_IP})"
    ;;
  "tailscale")
    SSH_TARGET="${B1_SSH_USER}@${B1_TAILSCALE_IP}"
    NETWORK_LABEL="Tailscale (${B1_TAILSCALE_IP})"
    ;;
  "unreachable")
    echo ""
    echo "❌ Cannot reach VM B1 via any network path"
    echo "   LAN       : $B1_LOCAL_IP"
    echo "   Tailscale : $B1_TAILSCALE_IP"
    echo ""
    exit 1
    ;;
esac

# =============================================================================
# ─── BUILD JSON-RPC PAYLOAD ──────────────────────────────────────────────────
# =============================================================================

JSONRPC_PAYLOAD=$(jq -n \
  --arg query "$QUERY" \
  --argjson limit "$LIMIT" \
  '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "search_knowledge",
      "arguments": {
        "query": $query,
        "limit": $limit
      }
    }
  }'
)

# =============================================================================
# ─── RUN QUERY ───────────────────────────────────────────────────────────────
# =============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Qdrant Retrieval Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Query   : $QUERY"
echo "  Limit   : $LIMIT"
echo "  Network : $NETWORK_LABEL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$NETWORK" = "local-b1" ]; then
  RAW_RESULT=$(echo "$JSONRPC_PAYLOAD" | $B1_MCP_CMD 2>/dev/null)
else
  RAW_RESULT=$(echo "$JSONRPC_PAYLOAD" \
    | ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$SSH_TARGET" "$B1_MCP_CMD" 2>/dev/null)
fi

# =============================================================================
# ─── DISPLAY RESULTS ─────────────────────────────────────────────────────────
# =============================================================================

echo "$RAW_RESULT" | jq '.' 2>/dev/null || echo "$RAW_RESULT"

# =============================================================================
# ─── SAVE LOG ────────────────────────────────────────────────────────────────
# =============================================================================

mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y-%m-%d-%H%M%S")
LOG_FILE="${LOG_DIR}/${TIMESTAMP}-retrieval.log"

{
  echo "========================================================"
  echo "Qdrant Retrieval Test Log"
  echo "========================================================"
  echo "Query   : $QUERY"
  echo "Limit   : $LIMIT"
  echo "Network : $NETWORK_LABEL"
  echo "Time    : $(date)"
  echo "========================================================"
  echo ""
  echo "$RAW_RESULT" | jq '.' 2>/dev/null || echo "$RAW_RESULT"
} > "$LOG_FILE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Log saved: $LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
