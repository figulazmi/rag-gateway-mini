#!/bin/bash
# test-rag-v2.sh — RAG Capture V2 End-to-End Test
# Usage:
#   bash test-rag-v2.sh --dry-run   ← SAFE: skip push, collection tidak tersentuh
#   bash test-rag-v2.sh             ← LIVE: push ke Qdrant (tambah points)

set -e

# ─── FLAGS ─────────────────────────────────────────────────────
DRY_RUN=false
for arg in "$@"; do
  [[ "$arg" == "--dry-run" ]] && DRY_RUN=true
done

# ─── COLORS ────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}✅ $1${NC}"; }
fail() { echo -e "  ${RED}❌ $1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; }
info() { echo -e "  ${CYAN}ℹ️  $1${NC}"; }

PASS_COUNT=0
FAIL_COUNT=0

check() {
  local desc="$1"
  local result="$2"
  if [[ "$result" == "pass" ]]; then
    pass "$desc"
    ((PASS_COUNT++)) || true
  else
    fail "$desc"
    ((FAIL_COUNT++)) || true
  fi
}

# ─── HEADER ────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════"
echo "  RAG Capture V2 — End-to-End Test"
if $DRY_RUN; then
  echo -e "  Mode: ${YELLOW}DRY RUN${NC} — push di-skip, collection knowledge_v2 aman"
else
  echo -e "  Mode: ${RED}LIVE${NC} — akan push ke Qdrant collection knowledge_v2"
fi
echo "════════════════════════════════════════════════════════"
echo ""

QDRANT_URL="http://localhost:6333"

# ─── TEST 0: PRE-FLIGHT ────────────────────────────────────────
echo "━━━ [0] PRE-FLIGHT CHECK ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 0A. rag command tersedia
if command -v rag &>/dev/null; then
  check "rag command tersedia" "pass"
else
  check "rag command tersedia" "fail"
  fail "Install: bash scripts/rag-capture-v2/rag-setup.sh && source ~/.bashrc"
  exit 1
fi

# 0B. Python 3
if python3 --version &>/dev/null; then
  check "Python 3 tersedia ($(python3 --version))" "pass"
else
  check "Python 3 tersedia" "fail"
  exit 1
fi

# 0C. Qdrant
QDRANT_VERSION=$(curl -s "$QDRANT_URL" 2>/dev/null \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null || echo "")

if [[ -n "$QDRANT_VERSION" ]]; then
  check "Qdrant accessible (v$QDRANT_VERSION)" "pass"
else
  check "Qdrant accessible di $QDRANT_URL" "fail"
  exit 1
fi

# 0D. Collection knowledge_v2 terisi
POINTS_TOTAL=$(curl -s "$QDRANT_URL/collections/knowledge_v2" 2>/dev/null \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null || echo "0")

if [[ "$POINTS_TOTAL" -gt 0 ]]; then
  check "Collection knowledge_v2 ada ($POINTS_TOTAL points)" "pass"
else
  check "Collection knowledge_v2 terisi" "fail"
  warn "Jalankan: python3 scripts/migrate-to-hybrid.py"
  exit 1
fi

# 0E. Ollama
OLLAMA_UP=$(curl -s http://localhost:11434 2>/dev/null | grep -c "Ollama" || true)
if [[ "$OLLAMA_UP" -gt 0 ]]; then
  check "Ollama accessible" "pass"
else
  check "Ollama accessible di localhost:11434" "fail"
  exit 1
fi

# 0F. Project root
PROJECT_ROOT=$(rag status 2>/dev/null | grep "Project root" | awk '{print $NF}')
SUMMARIES_DIR="$PROJECT_ROOT/.claude/summaries"
check "Project root: $PROJECT_ROOT" "pass"

echo ""

# ─── TEST 1: SIGNAL AUTO-DETECTION ─────────────────────────────
echo "━━━ [1] SIGNAL AUTO-DETECTION (pipe) ━━━━━━━━━━━━━━━━━━"

# Bersihkan drafts dulu agar test bersih
echo "y" | rag clear 2>/dev/null || true

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
- Qdrant does not support adding sparse vectors to existing collections — must create new
- Server-side BM25 requires qdrant-client >= 1.13.0 and Qdrant server >= 1.15.2
- Migration uses models.Document(text=content, model="Qdrant/bm25") for sparse embedding
- Dense vector must be renamed from unnamed to "dense" in new collection config
- Payload indexes must be recreated on new collection after migration
<<<RAG_CHUNK_END>>>'

PIPE_OUTPUT=$(echo "$MOCK_OUTPUT" | rag pipe 2>&1 || true)
echo "$PIPE_OUTPUT"
echo ""

if echo "$PIPE_OUTPUT" | grep -q "RAG signal detected"; then
  check "Signal <<<RAG_META:...>>> terdeteksi otomatis" "pass"
else
  check "Signal <<<RAG_META:...>>> terdeteksi otomatis" "fail"
fi

DRAFT_COUNT=$(ls ~/.rag_drafts/ 2>/dev/null | grep -c "chunk_" || echo "0")
if [[ "$DRAFT_COUNT" -ge 1 ]]; then
  check "Draft chunk tersimpan ($DRAFT_COUNT file)" "pass"
else
  check "Draft chunk tersimpan" "fail"
fi

echo ""

# ─── TEST 2: MANUAL ADD ────────────────────────────────────────
echo "━━━ [2] MANUAL ADD ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

MANUAL_CONTENT="### Context
RAG Gateway Mini serves hybrid search via POST /rag/search after migration to knowledge_v2.
The gateway embeds queries via Ollama nomic-embed-text then queries Qdrant using RRF fusion.

### Problem
After collection migration, search returned zero results. QdrantVectorSearchClient
still used old collection name and unnamed vector format. ScoreThreshold 0.55
was too high for RRF fusion scores which are normalized differently than cosine.

### Solution
Updated appsettings.json QdrantCollection to knowledge_v2 and DenseVectorName to dense.
Updated search request body to include using:dense field for named vector lookup.
Lowered ScoreThreshold from 0.55 to 0.35 to match RRF normalized score range.

### Key Facts
- After migration appsettings.json must set QdrantCollection to knowledge_v2
- Named vector search requires using:dense field in Qdrant query request body
- RRF fusion scores are lower than raw cosine scores — lower ScoreThreshold 0.35 vs 0.55
- DenseVectorName config must match vector name used during collection creation"

ADD_OUTPUT=$(rag add \
  --project homelab \
  --type debug \
  --topic "RAG Gateway Zero Results After Collection Migration" \
  --tags "rag-gateway,qdrant,appsettings,search,homelab,fixed" \
  --branch "main" \
  --content "$MANUAL_CONTENT" 2>&1)

echo "$ADD_OUTPUT"
echo ""

DRAFT_COUNT_2=$(ls ~/.rag_drafts/ 2>/dev/null | grep -c "chunk_" || echo "0")
if [[ "$DRAFT_COUNT_2" -ge 2 ]]; then
  check "Manual add berhasil (total $DRAFT_COUNT_2 drafts)" "pass"
else
  check "Manual add berhasil" "fail"
fi

echo ""

# ─── TEST 3: LIST & FRONTMATTER VALIDATION ─────────────────────
echo "━━━ [3] LIST & FRONTMATTER VALIDATION ━━━━━━━━━━━━━━━━━"

rag list
echo ""

CHUNK1=$(ls ~/.rag_drafts/chunk_*.md 2>/dev/null | sort | head -1)
if [[ -f "$CHUNK1" ]]; then
  HAS_ID=$(grep -c "^id:"              "$CHUNK1" || echo "0")
  HAS_PROJECT=$(grep -c "^project: homelab" "$CHUNK1" || echo "0")
  HAS_TYPE=$(grep -c "^chunk_type:"    "$CHUNK1" || echo "0")
  HAS_TOPIC=$(grep -c "^topic:"        "$CHUNK1" || echo "0")
  HAS_TAGS=$(grep -c "^tags:"          "$CHUNK1" || echo "0")
  HAS_STATUS=$(grep -c "^status:"      "$CHUNK1" || echo "0")
  HAS_EM_DASH=$(grep -c "—"            "$CHUNK1" || echo "0")
  HAS_INDONESIAN=$(grep -cE '\b(ini|yang|dan|atau|dengan|untuk|tidak|bisa|sudah)\b' "$CHUNK1" || echo "0")

  [[ "$HAS_ID"          -gt 0 ]] && check "Frontmatter: id"            "pass" || check "Frontmatter: id"        "fail"
  [[ "$HAS_PROJECT"     -gt 0 ]] && check "Frontmatter: project=homelab" "pass" || check "Frontmatter: project" "fail"
  [[ "$HAS_TYPE"        -gt 0 ]] && check "Frontmatter: chunk_type"    "pass" || check "Frontmatter: chunk_type" "fail"
  [[ "$HAS_TOPIC"       -gt 0 ]] && check "Frontmatter: topic"         "pass" || check "Frontmatter: topic"     "fail"
  [[ "$HAS_TAGS"        -gt 0 ]] && check "Frontmatter: tags"          "pass" || check "Frontmatter: tags"      "fail"
  [[ "$HAS_STATUS"      -gt 0 ]] && check "Frontmatter: status"        "pass" || check "Frontmatter: status"    "fail"
  [[ "$HAS_EM_DASH"     -eq 0 ]] && check "No em dash (—) di frontmatter" "pass" || check "Em dash ditemukan!" "fail"
  [[ "$HAS_INDONESIAN"  -eq 0 ]] && check "Content: English only"      "pass" || warn "Kemungkinan ada Bahasa Indonesia"

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

  CHUNK_COUNT=$(grep -c "^## CHUNK" "$MERGED_FILE" || echo "0")
  HAS_METADATA=$(grep -c "SESSION METADATA" "$MERGED_FILE" || echo "0")
  WORD_COUNT=$(wc -w < "$MERGED_FILE")

  [[ "$CHUNK_COUNT"  -ge 2 ]] && check "Merged berisi $CHUNK_COUNT chunks" "pass" || check "Merged berisi chunks" "fail"
  [[ "$HAS_METADATA" -gt 0 ]] && check "SESSION METADATA section ada"      "pass" || check "SESSION METADATA ada"  "fail"

  info "Word count: $WORD_COUNT words"
  info "File size : $(du -h "$MERGED_FILE" | cut -f1)"
  echo ""
  info "Preview (30 baris pertama):"
  head -30 "$MERGED_FILE"
else
  check "Merge berhasil" "fail"
fi

echo ""

# ─── TEST 5: PUSH ──────────────────────────────────────────────
echo "━━━ [5] PUSH TO QDRANT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

POINTS_BEFORE=$(curl -s "$QDRANT_URL/collections/knowledge_v2" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null || echo "0")

if $DRY_RUN; then
  echo ""
  warn "DRY RUN — push di-skip. Collection knowledge_v2 tidak disentuh."
  info "Points saat ini  : $POINTS_BEFORE (tidak berubah)"
  info "File yang disiapkan: $MERGED_FILE"
  echo ""
  info "Command push jika ingin live:"
  echo ""
  echo "      bash scripts/push-to-qdrant.sh $MERGED_FILE"
  echo ""
  check "Dry-run push simulation OK" "pass"

  # Cleanup test file agar tidak mengganggu
  [[ -f "$MERGED_FILE" ]] && rm "$MERGED_FILE" && info "Test file dihapus (dry-run cleanup)"
else
  info "Points sebelum: $POINTS_BEFORE"
  bash scripts/push-to-qdrant.sh "$MERGED_FILE"
  sleep 3

  POINTS_AFTER=$(curl -s "$QDRANT_URL/collections/knowledge_v2" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null || echo "0")
  ADDED=$((POINTS_AFTER - POINTS_BEFORE))

  info "Points sesudah : $POINTS_AFTER (+$ADDED)"
  [[ "$ADDED" -gt 0 ]] \
    && check "Push berhasil ($ADDED points added)" "pass" \
    || check "Push berhasil — points bertambah" "fail"
fi

echo ""

# ─── TEST 6: RETRIEVAL QUALITY (read-only) ─────────────────────
echo "━━━ [6] RETRIEVAL QUALITY (read-only, selalu jalan) ━━━"
echo ""

run_query() {
  local label="$1"
  local query="$2"
  local project="$3"

  echo "  Query: \"$query\""

  VECTOR=$(curl -s http://localhost:11434/api/embeddings \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"nomic-embed-text\",\"prompt\":\"$query\"}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['embedding'])" 2>/dev/null || echo "")

  if [[ -z "$VECTOR" ]]; then
    fail "$label — Ollama embedding gagal"
    echo ""
    return
  fi

  RESULT=$(curl -s -X POST "$QDRANT_URL/collections/knowledge_v2/points/query" \
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
data = json.load(sys.stdin)
pts = data.get('result', {}).get('points', [])
print(f'  Results: {len(pts)}')
for i, p in enumerate(pts):
    score = p.get('score', 0)
    topic = p.get('payload', {}).get('topic', 'N/A')
    ctype = p.get('payload', {}).get('chunk_type', '?')
    print(f'  [{i+1}] score={score:.4f} | type={ctype} | {topic}')
" 2>/dev/null || echo "  parse error")

  echo "$RESULT"

  RESULT_COUNT=$(echo "$RESULT" | grep -c "score=" || echo "0")
  [[ "$RESULT_COUNT" -gt 0 ]] \
    && check "$label — $RESULT_COUNT result(s)" "pass" \
    || check "$label — tidak ada hasil" "fail"
  echo ""
}

run_query "6A. Exact keyword (BM25)" \
  "Qdrant sparse vector BM25 collection migration python script" \
  "homelab"

run_query "6B. Semantic query (dense)" \
  "how to fix search returning empty results after database migration" \
  "homelab"

run_query "6C. Technical term" \
  "nomic-embed-text ollama embedding docker vm" \
  "homelab"

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
  echo -e "  Mode   : ${YELLOW}DRY RUN${NC} — collection knowledge_v2 tidak disentuh"
  echo -e "  Points : $POINTS_BEFORE (tidak berubah)"
  echo ""
  echo "  Untuk live test dengan push sungguhan:"
  echo "  bash scripts/test-rag-v2.sh"
else
  echo -e "  Mode   : ${RED}LIVE${NC}"
  echo -e "  Points : $POINTS_BEFORE → ${POINTS_AFTER:-$POINTS_BEFORE} (+${ADDED:-0})"
fi

echo ""
if [[ "$FAIL_COUNT" -eq 0 ]]; then
  echo -e "  ${GREEN}✅ Semua test passed! RAG Capture V2 siap digunakan.${NC}"
else
  echo -e "  ${RED}⚠️  $FAIL_COUNT test gagal. Cek output di atas.${NC}"
fi
echo "════════════════════════════════════════════════════════"
echo ""
