#!/usr/bin/env bash
# =============================================================================
# push-to-qdrant.sh
# Author  : Figur Ulul Azmi
# Target  : Qdrant collection "knowledge_v2" (hybrid dense + sparse BM25) via n8n webhook (VM B1 Proxmox)
# Usage   : bash ~/scripts/push-to-qdrant.sh <file.md>
# Example : bash ~/scripts/push-to-qdrant.sh .claude/summaries/2026-04-07-sdl.md
# =============================================================================

set -euo pipefail

# =============================================================================
# ─── CONFIG — isi sesuai setup Azmi ──────────────────────────────────────────
# =============================================================================

# IP lokal VM B1 di jaringan kantor Bandung (LAN)
B1_LOCAL_IP="192.168.18.169"          # ← ganti dengan IP lokal B1 di kantor
B1_LOCAL_PORT="5678"

# IP Tailscale VM B1 (untuk akses dari luar kantor)
B1_TAILSCALE_IP="100.120.249.99"        # ← ganti dengan: tailscale ip -4 (di B1)
B1_TAILSCALE_PORT="5678"

# Jika script dijalankan langsung dari dalam VM B1
B1_LOCALHOST_URL="http://localhost:5678/webhook/knowledge-ingest"

# Webhook path — n8n 2.15.0 sudah bersih tanpa UUID
N8N_WEBHOOK_PATH="webhook/knowledge-ingest"

# Timeout (n8n + Ollama bisa lambat)
CURL_TIMEOUT=120

# Qdrant API key — read from env var or ~/.config/qdrant-knowledge.env
# NEVER hardcode this value here — file is tracked by git
if [ -z "${QDRANT_API_KEY:-}" ]; then
  ENV_FILE="$HOME/.config/qdrant-knowledge.env"
  if [ -f "$ENV_FILE" ]; then
    # shellcheck source=/dev/null
    source "$ENV_FILE"
  fi
fi

if [ -z "${QDRANT_API_KEY:-}" ]; then
  echo ""
  echo "❌ Error: QDRANT_API_KEY not set."
  echo ""
  echo "Create the file: ~/.config/qdrant-knowledge.env"
  echo "Content:"
  echo "  QDRANT_API_KEY=your-api-key-here"
  echo ""
  echo "Then re-run this script."
  echo ""
  exit 1
fi


# =============================================================================
# ─── NETWORK DETECTION ───────────────────────────────────────────────────────
# Priority: (1) VM B1 itself → (2) LAN Bandung → (3) Tailscale
# =============================================================================

detect_network() {
  # ── Priority 1: Apakah script jalan DI DALAM VM B1? ──
  if hostname 2>/dev/null | grep -qi "figulazmi"; then
    echo "local-b1"
    return
  fi

  # ── Priority 2: Coba reach B1 via LAN (kantor Bandung) ──
  # Pakai curl instead of ping — compatible Windows Git Bash + Linux
  if curl -s --connect-timeout 2 "http://${B1_LOCAL_IP}:${B1_LOCAL_PORT}" \
     -o /dev/null 2>/dev/null; then
    echo "lan"
    return
  fi

  # ── Priority 3: Coba reach B1 via Tailscale ──
  if curl -s --connect-timeout 3 "http://${B1_TAILSCALE_IP}:${B1_TAILSCALE_PORT}" \
     -o /dev/null 2>/dev/null; then
    echo "tailscale"
    return
  fi

  # ── Tidak ada yang reachable ──
  echo "unreachable"
}

NETWORK=$(detect_network)

case "$NETWORK" in
  "local-b1")
    N8N_WEBHOOK_URL="$B1_LOCALHOST_URL"
    QDRANT_BASE_URL="http://localhost:6333"
    NETWORK_LABEL="VM B1 (localhost)"
    ;;
  "lan")
    N8N_WEBHOOK_URL="http://${B1_LOCAL_IP}:${B1_LOCAL_PORT}/${N8N_WEBHOOK_PATH}"
    QDRANT_BASE_URL="http://${B1_LOCAL_IP}:6333"
    NETWORK_LABEL="LAN Kantor Bandung (${B1_LOCAL_IP})"
    ;;
  "tailscale")
    N8N_WEBHOOK_URL="http://${B1_TAILSCALE_IP}:${B1_TAILSCALE_PORT}/${N8N_WEBHOOK_PATH}"
    QDRANT_BASE_URL="http://${B1_TAILSCALE_IP}:6333"
    NETWORK_LABEL="Tailscale VPN (${B1_TAILSCALE_IP})"
    ;;
  "unreachable")
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "❌ Cannot reach VM B1 via any network path"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Tried:"
    echo "  LAN       : $B1_LOCAL_IP (ping failed)"
    echo "  Tailscale : $B1_TAILSCALE_IP (ping failed)"
    echo ""
    echo "Fix options:"
    echo "  → Connect to kantor Bandung WiFi/LAN, OR"
    echo "  → Start Tailscale: tailscale up"
    echo "  → Check B1 VM status in Proxmox dashboard"
    echo ""
    exit 1
    ;;
esac

# ──────────────────────────────────────────────────────────────────────────────

# ─── VALIDATION ───────────────────────────────────────────────────────────────
if [ $# -eq 0 ]; then
  echo ""
  echo "❌ Error: No file specified."
  echo ""
  echo "Usage  : bash push-to-qdrant.sh <file.md>"
  echo "Example: bash push-to-qdrant.sh .claude/summaries/2026-04-07-sdl-phase1.md"
  echo ""
  exit 1
fi

FILE="$1"

if [ ! -f "$FILE" ]; then
  echo ""
  echo "❌ Error: File not found: $FILE"
  echo ""
  exit 1
fi

if [[ "$FILE" != *.md ]]; then
  echo ""
  echo "⚠️  Warning: File does not have .md extension: $FILE"
  echo "   Proceeding anyway..."
  echo ""
fi
# ──────────────────────────────────────────────────────────────────────────────

# ─── PARSE FRONTMATTER ────────────────────────────────────────────────────────
# Extract key fields from YAML frontmatter for logging
extract_field() {
  grep -m1 "^$1:" "$FILE" \
    | sed "s/^$1:[[:space:]]*//" \
    | tr -d '"' \
    | sed 's/[—–]/-/g' \
    | iconv -f UTF-8 -t ASCII//TRANSLIT 2>/dev/null \
    || echo "unknown"
}

extract_tags_json() {
  local raw
  raw=$(grep -m1 "^tags:" "$FILE" \
    | sed "s/^tags:[[:space:]]*//" \
    | tr -d '"' \
    | sed 's/^\[//;s/\]$//')
  if [ -n "$raw" ]; then
    echo "$raw" \
      | tr ',' '\n' \
      | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' \
      | grep -v '^$' \
      | jq -R . \
      | jq -s .
  else
    echo "[]"
  fi
}

DOC_ID=$(extract_field "id")
DOC_DATE=$(extract_field "date")
DOC_PROJECT=$(extract_field "project")
DOC_TOPIC=$(extract_field "topic")
DOC_SOURCE=$(extract_field "source")
DOC_TAGS_JSON=$(extract_tags_json)
DOC_SESSION_TYPE=$(extract_field "session_type")
DOC_ENVIRONMENT=$(extract_field "environment")
DOC_GIT_BRANCH=$(extract_field "git_branch")
DOC_RELATED=$(extract_field "related")
DOC_COLLECTION=$(extract_field "collection")
FILENAME=$(basename "$FILE")
# ──────────────────────────────────────────────────────────────────────────────

# ─── CHUNK SPLITTING ──────────────────────────────────────────────────────────
# Split file into chunks based on ## CHUNK markers
# Each chunk is sent as a separate vector point to Qdrant
CHUNKS=()
CURRENT_CHUNK=""
IN_FRONTMATTER=0
FRONTMATTER_DONE=0
CHUNK_COUNT=0

while IFS= read -r line; do
  # Handle frontmatter boundaries
  if [ "$line" = "---" ] && [ "$FRONTMATTER_DONE" -eq 0 ]; then
    if [ "$IN_FRONTMATTER" -eq 0 ]; then
      IN_FRONTMATTER=1
    else
      FRONTMATTER_DONE=1
      IN_FRONTMATTER=0
    fi
    continue
  fi

  # Skip frontmatter content
  if [ "$IN_FRONTMATTER" -eq 1 ]; then
    continue
  fi

  # Detect chunk boundary
  if [[ "$line" =~ ^##[[:space:]]CHUNK ]]; then
    # Save previous chunk if not empty
    if [ -n "$CURRENT_CHUNK" ] && [ "$CHUNK_COUNT" -gt 0 ]; then
      CHUNKS+=("$CURRENT_CHUNK")
    fi
    CURRENT_CHUNK="$line"$'\n'
    CHUNK_COUNT=$((CHUNK_COUNT + 1))
  # Skip SESSION METADATA block — not a knowledge chunk
  elif [[ "$line" =~ ^##[[:space:]]SESSION[[:space:]]METADATA ]]; then
    if [ -n "$CURRENT_CHUNK" ]; then
      CHUNKS+=("$CURRENT_CHUNK")
      CURRENT_CHUNK=""
    fi
    break
  else
    CURRENT_CHUNK+="$line"$'\n'
  fi
done < "$FILE"

# Catch last chunk if file didn't end with SESSION METADATA
if [ -n "$CURRENT_CHUNK" ]; then
  CHUNKS+=("$CURRENT_CHUNK")
fi

TOTAL_CHUNKS=${#CHUNKS[@]}

if [ "$TOTAL_CHUNKS" -eq 0 ]; then
  echo ""
  echo "❌ Error: No ## CHUNK blocks found in $FILE"
  echo "   Make sure the file follows RAG Knowledge Capture format."
  echo ""
  exit 1
fi
# ──────────────────────────────────────────────────────────────────────────────

# ─── PUSH ─────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Push to Qdrant — RAG Knowledge Capture"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  File     : $FILENAME"
echo "  ID       : $DOC_ID"
echo "  Project  : $DOC_PROJECT"
echo "  Topic    : $DOC_TOPIC"
echo "  Chunks   : $TOTAL_CHUNKS"
echo "  Network  : $NETWORK_LABEL"
echo "  Webhook  : $N8N_WEBHOOK_URL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ─── VERIFY HELPER ────────────────────────────────────────────────────────────
get_point_count() {
  local collection="${DOC_COLLECTION:-knowledge_v2}"
  curl -s --max-time 5 \
    -H "api-key: ${QDRANT_API_KEY}" \
    "${QDRANT_BASE_URL}/collections/${collection}" \
    | grep -o '"points_count":[0-9]*' | grep -o '[0-9]*$'
}

COUNT_BEFORE=$(get_point_count 2>/dev/null || echo "?")
# ──────────────────────────────────────────────────────────────────────────────

SUCCESS_COUNT=0
FAIL_COUNT=0

for i in "${!CHUNKS[@]}"; do
  CHUNK_NUM=$((i + 1))
  CHUNK_CONTENT="${CHUNKS[$i]}"

  # Extract chunk title from first line
  CHUNK_TITLE=$(echo "$CHUNK_CONTENT" | head -1 | sed 's/^## //')

  echo -n "  [$CHUNK_NUM/$TOTAL_CHUNKS] Sending: $CHUNK_TITLE ... "

  # Build JSON payload
  PAYLOAD=$(jq -n \
    --arg id           "${DOC_ID}-chunk-${CHUNK_NUM}" \
    --arg doc_id       "$DOC_ID" \
    --arg date         "$DOC_DATE" \
    --arg source       "$DOC_SOURCE" \
    --arg project      "$DOC_PROJECT" \
    --arg topic        "$DOC_TOPIC" \
    --argjson tags     "$DOC_TAGS_JSON" \
    --arg session_type "$DOC_SESSION_TYPE" \
    --arg environment  "$DOC_ENVIRONMENT" \
    --arg git_branch   "$DOC_GIT_BRANCH" \
    --arg related      "$DOC_RELATED" \
    --arg filename     "$FILENAME" \
    --arg chunk_num    "$CHUNK_NUM" \
    --arg content      "$CHUNK_CONTENT" \
    --arg collection   "${DOC_COLLECTION:-knowledge_v2}" \
    --arg api_key      "$QDRANT_API_KEY" \
    '{
      id:             $id,
      doc_id:         $doc_id,
      date:           $date,
      source:         $source,
      project:        $project,
      topic:          $topic,
      tags:           $tags,
      session_type:   $session_type,
      environment:    $environment,
      git_branch:     $git_branch,
      related:        $related,
      filename:       $filename,
      chunk_num:      ($chunk_num | tonumber),
      content:        $content,
      collection:     $collection,
      qdrant_api_key: $api_key
    }'
  )

  # Send to n8n webhook
  HTTP_STATUS=$(curl -s -o /tmp/qdrant_response.json \
    -w "%{http_code}" \
    --max-time "$CURL_TIMEOUT" \
    -X POST "$N8N_WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" 2>/dev/null)

  if [ "$HTTP_STATUS" -ge 200 ] && [ "$HTTP_STATUS" -lt 300 ]; then
    echo "✅ OK ($HTTP_STATUS)"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
  else
    echo "❌ FAILED (HTTP $HTTP_STATUS)"
    if [ -f /tmp/qdrant_response.json ]; then
      echo "     Response: $(cat /tmp/qdrant_response.json)"
    fi
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  # Small delay between chunks to not overwhelm n8n + Ollama
  if [ "$CHUNK_NUM" -lt "$TOTAL_CHUNKS" ]; then
    sleep 1
  fi
done
# ──────────────────────────────────────────────────────────────────────────────

# ─── SUMMARY ──────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo "✅ Done — $SUCCESS_COUNT/$TOTAL_CHUNKS chunks pushed to Qdrant"
  echo "   Collection : ${DOC_COLLECTION:-knowledge_v2}"
  echo "   Doc ID     : $DOC_ID"
else
  echo "⚠️  Partial — $SUCCESS_COUNT OK, $FAIL_COUNT FAILED"
  echo "   Re-run script to retry failed chunks"
fi

# ─── VERIFY: point count delta ────────────────────────────────────────────────
COUNT_AFTER=$(get_point_count 2>/dev/null || echo "?")
if [ "$COUNT_BEFORE" != "?" ] && [ "$COUNT_AFTER" != "?" ]; then
  DELTA=$(( COUNT_AFTER - COUNT_BEFORE ))
  if [ "$DELTA" -gt 0 ]; then
    echo "   Verified   : +${DELTA} points indexed (${COUNT_BEFORE} → ${COUNT_AFTER})" >&2
  elif [ "$FAIL_COUNT" -eq 0 ]; then
    echo "   ⚠️  Delta=0 — points may be updates of existing IDs (${COUNT_AFTER} total)" >&2
  fi
else
  echo "   Verify     : skipped (Qdrant unreachable for count check)" >&2
fi
# ──────────────────────────────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
# ──────────────────────────────────────────────────────────────────────────────

exit $FAIL_COUNT
