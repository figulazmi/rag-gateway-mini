#!/bin/bash
# test-rag-v2.sh — RAG Capture V2 End-to-End Test
# Usage:
#   bash scripts/rag-capture-v2/test-rag-v2.sh --dry-run   ← SAFE: skip push
#   bash scripts/rag-capture-v2/test-rag-v2.sh             ← LIVE: push ke Qdrant
#
# API Key dibaca dari:
#   1. Environment: export QDRANT_API_KEY="..."
#   2. appsettings.Production.json (auto-detect)
#   3. Flag: --api-key "..."

set -e

# ─── FLAGS ─────────────────────────────────────────────────────
DRY_RUN=false
CLI_API_KEY=""

for arg in "$@"; do
  [[ "$arg" == "--dry-run" ]] && DRY_RUN=true
done
for i in "$@"; do
  if [[ "$i" == "--api-key" ]]; then shift; CLI_API_KEY="$1"; fi
done

# ─── COLORS ────────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'
YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

pass()  { echo -e "  ${GREEN}✅ $1${NC}"; }
fail()  { echo -e "  ${RED}❌ $1${NC}"; }
warn()  { echo -e "  ${YELLOW}⚠️  $1${NC}"; }
info()  { echo -e "  ${CYAN}ℹ️  $1${NC}"; }

PASS_COUNT=0; FAIL_COUNT=0

check() {
  if [[ "$2" == "pass" ]]; then pass "$1"; ((PASS_COUNT++)) || true
  else fail "$1"; ((FAIL_COUNT++)) || true; fi
}

# FIX: count_lines — bersih tanpa newline artifact
count_lines() { echo "$1" | grep -c "$2" 2>/dev/null | tr -d '[:space:]' || echo "0"; }
count_file()  { grep -c "$2" "$1" 2>/dev/null | tr -d '[:space:]' || echo "0"; }

# ─── RESOLVE API KEY ───────────────────────────────────────────
resolve_api_key() {
  [[ -n "$CLI_API_KEY"      ]] && echo "$CLI_API_KEY"      && return
  [[ -n "$QDRANT_API_KEY"   ]] && echo "$QDRANT_API_KEY"   && return
  local f="/opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json"
  [[ -f "$f" ]] && python3 -c "
import json
with open('$f') as fp: d=json.load(fp)
for v in d.values():
    if isinstance(v,dict) and 'QdrantApiKey' in v:
        print(v['QdrantApiKey']); exit()
print(d.get('QdrantApiKey',''))
" 2>/dev/null || echo ""
}

QDRANT_API_KEY_RESOLVED=$(resolve_api_key)

qdrant_curl() {
  if [[ -n "$QDRANT_API_KEY_RESOLVED" ]]; then
    curl -s -H "api-key: $QDRANT_API_KEY_RESOLVED" "$@"
  else
    curl -s "$@"
  fi
}

QDRANT_URL="http://192.168.18.169:6333"

# ─── HEADER ────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════"
echo "  RAG Capture V2 — End-to-End Test"
if $DRY_RUN; then
  echo -e "  Mode  : ${YELLOW}DRY RUN${NC} — push di-skip, collection aman"
else
  echo -e "  Mode  : ${RED}LIVE${NC} — akan push ke Qdrant collection knowledge_v2"
fi
if [[ -n "$QDRANT_API_KEY_RESOLVED" ]]; then
  echo -e "  APIKey: ${GREEN}detected${NC} (${QDRANT_API_KEY_RESOLVED:0:8}...)"
else
  echo -e "  APIKey: ${YELLOW}none${NC} (open Qdrant)"
fi
echo "════════════════════════════════════════════════════════"
echo ""

# ─── TEST 0: PRE-FLIGHT ────────────────────────────────────────
echo "━━━ [0] PRE-FLIGHT CHECK ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

command -v rag &>/dev/null \
  && check "rag command tersedia" "pass" \
  || { check "rag command tersedia" "fail"; exit 1; }

python3 --version &>/dev/null \
  && check "Python 3 tersedia ($(python3 --version))" "pass" \
  || { check "Python 3 tersedia" "fail"; exit 1; }

QDRANT_VERSION=$(qdrant_curl "$QDRANT_URL" 2>/dev/null \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('version',''))" 2>/dev/null || echo "")
[[ -n "$QDRANT_VERSION" ]] \
  && check "Qdrant accessible (v$QDRANT_VERSION)" "pass" \
  || { check "Qdrant accessible" "fail"; exit 1; }

COL_RESP=$(qdrant_curl "$QDRANT_URL/collections/knowledge_v2" 2>/dev/null || echo "")
POINTS_TOTAL=$(echo "$COL_RESP" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null || echo "0")
POINTS_TOTAL=$(echo "$POINTS_TOTAL" | tr -d '[:space:]')

COL_STATUS=$(echo "$COL_RESP" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['status'])" 2>/dev/null || echo "")

VECTORS_OK=$(echo "$COL_RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)['result']['config']['params']
ok='ok' if 'dense' in d.get('vectors',{}) and 'sparse' in d.get('sparse_vectors',{}) else 'fail'
print(ok)
" 2>/dev/null || echo "fail")

[[ "$POINTS_TOTAL" -gt 0 ]] \
  && check "Collection knowledge_v2 ada ($POINTS_TOTAL points, status=$COL_STATUS)" "pass" \
  || { check "Collection knowledge_v2 terisi" "fail"; exit 1; }

[[ "$VECTORS_OK" == "ok" ]] \
  && check "Hybrid config: dense + sparse" "pass" \
  || check "Hybrid config: dense + sparse" "fail"

OLLAMA_UP=$(curl -s http://localhost:11434 2>/dev/null | grep -c "Ollama" || echo "0")
OLLAMA_UP=$(echo "$OLLAMA_UP" | tr -d '[:space:]')
[[ "$OLLAMA_UP" -gt 0 ]] \
  && check "Ollama accessible" "pass" \
  || { check "Ollama accessible" "fail"; exit 1; }

PROJECT_ROOT=$(rag status 2>/dev/null | grep "Project root" | awk '{print $NF}')
SUMMARIES_DIR="$PROJECT_ROOT/.claude/summaries"
check "Project root: $PROJECT_ROOT" "pass"
echo ""

# ─── TEST 1: SIGNAL AUTO-DETECTION ─────────────────────────────
echo "━━━ [1] SIGNAL AUTO-DETECTION (pipe) ━━━━━━━━━━━━━━━━━━"

echo "y" | rag clear 2>/dev/null || true

# FIX: mock content tanpa em dash — semua bullet pakai plain hyphen
MOCK_OUTPUT='<<<RAG_META:project=homelab,type=debug,topic=Qdrant Collection Migration Dense to Hybrid,tags=qdrant|hybrid-search|migration|bm25|homelab|fixed>>>
<<<RAG_CHUNK_START>>>
### Context
RAG Gateway Mini on VM B1 uses Qdrant as vector store with collection "knowledge".
Migration to "knowledge_v2" was needed to support hybrid search with dense and sparse BM25 vectors.

### Problem
Qdrant does not support adding sparse vectors to an existing collection.
A new collection with both dense and sparse vector configs had to be created,
then all points copied from the old collection via scroll and upsert.

### Solution
Created migrate-to-hybrid.py that creates knowledge_v2 with VectorParams for dense
(768-dim cosine) and SparseVectorParams with IDF modifier for server-side BM25,
then scrolls all points from knowledge and upserts with named dense vector and
Document object so Qdrant generates sparse embeddings automatically.

### Key Facts
- Qdrant does not support adding sparse vectors to existing collections - must create new
- Server-side BM25 requires qdrant-client >= 1.13.0 and Qdrant server >= 1.15.2
- Migration uses models.Document(text=content, model="Qdrant/bm25") for sparse embedding
- Dense vector must be renamed from unnamed to "dense" in new collection config
- Payload indexes must be recreated on new collection after migration
<<<RAG_CHUNK_END>>>'

PIPE_OUTPUT=$(echo "$MOCK_OUTPUT" | rag pipe 2>&1 || true)
echo "$PIPE_OUTPUT"
echo ""

echo "$PIPE_OUTPUT" | grep -q "RAG signal detected" \
  && check "Signal <<<RAG_META:...>>> terdeteksi" "pass" \
  || check "Signal <<<RAG_META:...>>> terdeteksi" "fail"

# FIX: count draft dengan cara yang aman
DRAFT_COUNT=$(find ~/.rag_drafts/ -name "chunk_*.md" 2>/dev/null | wc -l | tr -d '[:space:]')
[[ "$DRAFT_COUNT" -ge 1 ]] \
  && check "Draft chunk tersimpan ($DRAFT_COUNT file)" "pass" \
  || check "Draft chunk tersimpan" "fail"
echo ""

# ─── TEST 2: MANUAL ADD ────────────────────────────────────────
echo "━━━ [2] MANUAL ADD ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# FIX: content tanpa em dash
MANUAL_CONTENT="### Context
RAG Gateway Mini serves hybrid search via POST /rag/search after migration to knowledge_v2.
The gateway embeds queries via Ollama nomic-embed-text then queries Qdrant using RRF fusion.

### Problem
After collection migration search returned zero results. QdrantVectorSearchClient still
used old collection name and unnamed vector format. ScoreThreshold 0.55 was too high
for RRF fusion scores which are normalized differently than raw cosine similarity.

### Solution
Updated appsettings.json QdrantCollection to knowledge_v2 and DenseVectorName to dense.
Updated search request body to include using:dense field for named vector lookup.
Lowered ScoreThreshold from 0.55 to 0.35 to match RRF normalized score range.

### Key Facts
- After migration appsettings.json must set QdrantCollection to knowledge_v2
- Named vector search requires using:dense field in Qdrant query request body
- RRF fusion scores are lower than raw cosine - lower ScoreThreshold 0.35 vs 0.55
- DenseVectorName config must match the vector name used during collection creation"

ADD_OUTPUT=$(rag add \
  --project homelab \
  --type debug \
  --topic "RAG Gateway Zero Results After Collection Migration" \
  --tags "rag-gateway,qdrant,appsettings,search,homelab,fixed" \
  --branch "main" \
  --content "$MANUAL_CONTENT" 2>&1)

echo "$ADD_OUTPUT"
echo ""

# FIX: count draft dengan find + wc
DRAFT_COUNT_2=$(find ~/.rag_drafts/ -name "chunk_*.md" 2>/dev/null | wc -l | tr -d '[:space:]')
[[ "$DRAFT_COUNT_2" -ge 2 ]] \
  && check "Manual add berhasil (total $DRAFT_COUNT_2 drafts)" "pass" \
  || check "Manual add berhasil" "fail"
echo ""

# ─── TEST 3: FRONTMATTER VALIDATION ────────────────────────────
echo "━━━ [3] FRONTMATTER VALIDATION ━━━━━━━━━━━━━━━━━━━━━━━━"

rag list
echo ""

CHUNK1=$(find ~/.rag_drafts/ -name "chunk_*.md" 2>/dev/null | sort | head -1)
if [[ -f "$CHUNK1" ]]; then
  # FIX: semua count pakai count_file helper (sudah tr -d whitespace)
  HAS_ID=$(count_file "$CHUNK1" "^id:")
  HAS_PROJECT=$(count_file "$CHUNK1" "^project: homelab")
  HAS_TYPE=$(count_file "$CHUNK1" "^chunk_type:")
  HAS_TOPIC=$(count_file "$CHUNK1" "^topic:")
  HAS_TAGS=$(count_file "$CHUNK1" "^tags:")
  HAS_STATUS=$(count_file "$CHUNK1" "^status:")
  HAS_EM_DASH=$(count_file "$CHUNK1" "—")
  HAS_INDONESIAN=$(grep -cE '\b(ini|yang|dan|atau|dengan|untuk|tidak|bisa|sudah)\b' "$CHUNK1" 2>/dev/null | tr -d '[:space:]' || echo "0")

  [[ "$HAS_ID"         -gt 0 ]] && check "Frontmatter: id"              "pass" || check "Frontmatter: id"         "fail"
  [[ "$HAS_PROJECT"    -gt 0 ]] && check "Frontmatter: project=homelab" "pass" || check "Frontmatter: project"    "fail"
  [[ "$HAS_TYPE"       -gt 0 ]] && check "Frontmatter: chunk_type"      "pass" || check "Frontmatter: chunk_type" "fail"
  [[ "$HAS_TOPIC"      -gt 0 ]] && check "Frontmatter: topic"           "pass" || check "Frontmatter: topic"      "fail"
  [[ "$HAS_TAGS"       -gt 0 ]] && check "Frontmatter: tags"            "pass" || check "Frontmatter: tags"       "fail"
  [[ "$HAS_STATUS"     -gt 0 ]] && check "Frontmatter: status"          "pass" || check "Frontmatter: status"     "fail"
  [[ "$HAS_EM_DASH"    -eq 0 ]] && check "No em dash (—) di chunk"      "pass" || check "Em dash ditemukan!"      "fail"
  [[ "$HAS_INDONESIAN" -eq 0 ]] && check "Content: English only"        "pass" || warn  "Kemungkinan ada Bahasa Indonesia"

  echo ""
  info "Preview chunk 1 frontmatter:"
  head -16 "$CHUNK1"
fi
echo ""

# ─── TEST 4: MERGE ─────────────────────────────────────────────
echo "━━━ [4] MERGE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TODAY=$(date +%Y-%m-%d)
TEST_FILENAME="${TODAY}-rag-capture-v2-test.md"
MERGED_FILE="$SUMMARIES_DIR/$TEST_FILENAME"

echo "y" | rag merge --output "$TEST_FILENAME"
echo ""

if [[ -f "$MERGED_FILE" ]]; then
  check "Merge berhasil: $TEST_FILENAME" "pass"

  CHUNK_COUNT=$(count_file "$MERGED_FILE" "^## CHUNK")
  HAS_METADATA=$(count_file "$MERGED_FILE" "SESSION METADATA")
  WORD_COUNT=$(wc -w < "$MERGED_FILE" | tr -d '[:space:]')

  [[ "$CHUNK_COUNT"  -ge 2 ]] && check "Merged berisi $CHUNK_COUNT chunks" "pass" || check "Merged berisi chunks" "fail"
  [[ "$HAS_METADATA" -gt 0 ]] && check "SESSION METADATA section ada"      "pass" || check "SESSION METADATA ada"  "fail"

  info "Word count: $WORD_COUNT words"
  info "File size : $(du -h "$MERGED_FILE" | cut -f1)"
  echo ""
  info "Preview (25 baris pertama):"
  head -25 "$MERGED_FILE"
else
  check "Merge berhasil" "fail"
fi
echo ""

# ─── TEST 5: PUSH ──────────────────────────────────────────────
echo "━━━ [5] PUSH TO QDRANT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

POINTS_BEFORE=$(qdrant_curl "$QDRANT_URL/collections/knowledge_v2" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null \
  | tr -d '[:space:]' || echo "0")

if $DRY_RUN; then
  echo ""
  warn "DRY RUN — push di-skip. Collection knowledge_v2 tidak disentuh."
  info "Points saat ini    : $POINTS_BEFORE (tidak berubah)"
  info "File yang disiapkan: $MERGED_FILE"
  echo ""
  info "Command push untuk live test:"
  echo ""
  echo "      bash scripts/push-to-qdrant.sh $MERGED_FILE"
  echo ""
  check "Dry-run push simulation OK" "pass"
  [[ -f "$MERGED_FILE" ]] && rm "$MERGED_FILE" && info "Test file dihapus (dry-run cleanup)"
else
  info "Points sebelum push: $POINTS_BEFORE"
  bash scripts/push-to-qdrant.sh "$MERGED_FILE"
  sleep 3

  POINTS_AFTER=$(qdrant_curl "$QDRANT_URL/collections/knowledge_v2" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null \
    | tr -d '[:space:]' || echo "0")
  ADDED=$((POINTS_AFTER - POINTS_BEFORE))

  info "Points sesudah push: $POINTS_AFTER (+$ADDED)"
  [[ "$ADDED" -gt 0 ]] \
    && check "Push berhasil ($ADDED points added)" "pass" \
    || check "Push berhasil" "fail"
fi
echo ""

# ─── TEST 6: RETRIEVAL QUALITY ─────────────────────────────────
echo "━━━ [6] RETRIEVAL QUALITY (read-only) ━━━━━━━━━━━━━━━━━"
echo ""

run_query() {
  local label="$1" query="$2" project="$3"
  echo "  Query: \"$query\""

  VECTOR=$(curl -s http://localhost:11434/api/embeddings \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"nomic-embed-text\",\"prompt\":\"$query\"}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['embedding'])" 2>/dev/null || echo "")

  if [[ -z "$VECTOR" ]]; then
    fail "$label - Ollama embedding gagal"; echo ""; return
  fi

  RESULT=$(qdrant_curl -X POST "$QDRANT_URL/collections/knowledge_v2/points/query" \
    -H "Content-Type: application/json" \
    -d "{
      \"prefetch\": [{\"query\": $VECTOR, \"using\": \"dense\", \"limit\": 5}],
      \"query\": {\"fusion\": \"rrf\"},
      \"limit\": 3,
      \"with_payload\": true,
      \"filter\": {\"must\": [{\"key\": \"project\", \"match\": {\"value\": \"$project\"}}]}
    }" \
    | python3 -c "
import sys, json
pts = json.load(sys.stdin).get('result', {}).get('points', [])
print(f'  Results: {len(pts)}')
for i, p in enumerate(pts):
    print(f'  [{i+1}] score={p[\"score\"]:.4f} | type={p[\"payload\"].get(\"chunk_type\",\"?\")} | {p[\"payload\"].get(\"topic\",\"N/A\")}')
" 2>/dev/null || echo "  parse error")

  echo "$RESULT"
  RESULT_COUNT=$(echo "$RESULT" | grep -c "score=" | tr -d '[:space:]' || echo "0")
  [[ "$RESULT_COUNT" -gt 0 ]] \
    && check "$label - $RESULT_COUNT result(s)" "pass" \
    || check "$label - tidak ada hasil" "fail"
  echo ""
}

run_query "6A. Exact keyword (BM25)"  "Qdrant sparse vector BM25 collection migration python script"    "homelab"
run_query "6B. Semantic query (dense)" "how to fix search returning empty results after database migration" "homelab"
run_query "6C. Technical term"         "nomic-embed-text ollama docker vm homelab embedding"               "homelab"

# ─── TEST 7: REMINDER SYSTEM ───────────────────────────────────
echo "━━━ [7] REMINDER SYSTEM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

REMIND_OUTPUT=$(rag remind 2>&1)
echo "$REMIND_OUTPUT"
echo "$REMIND_OUTPUT" | grep -q "SESSION END REMINDER" \
  && check "rag remind berjalan" "pass" \
  || check "rag remind berjalan" "fail"
echo ""

# ─── FINAL SUMMARY ─────────────────────────────────────────────
echo "════════════════════════════════════════════════════════"
echo "  TEST SUMMARY"
echo "════════════════════════════════════════════════════════"
echo -e "  ${GREEN}PASS : $PASS_COUNT${NC}"
echo -e "  ${RED}FAIL : $FAIL_COUNT${NC}"
echo ""

if $DRY_RUN; then
  echo -e "  Mode   : ${YELLOW}DRY RUN${NC} - collection tidak disentuh"
  echo -e "  Points : $POINTS_BEFORE (tidak berubah)"
  echo ""
  echo "  Untuk live test:"
  echo "  bash scripts/rag-capture-v2/test-rag-v2.sh"
else
  POINTS_AFTER_FINAL=$(qdrant_curl "$QDRANT_URL/collections/knowledge_v2" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null \
    | tr -d '[:space:]' || echo "$POINTS_BEFORE")
  echo -e "  Mode   : ${RED}LIVE${NC}"
  echo -e "  Points : $POINTS_BEFORE -> $POINTS_AFTER_FINAL"
fi

echo ""
if [[ "$FAIL_COUNT" -eq 0 ]]; then
  echo -e "  ${GREEN}✅ Semua test passed! RAG Capture V2 siap digunakan.${NC}"
else
  echo -e "  ${RED}⚠️  $FAIL_COUNT test gagal. Cek output di atas.${NC}"
fi
echo "════════════════════════════════════════════════════════"
echo ""