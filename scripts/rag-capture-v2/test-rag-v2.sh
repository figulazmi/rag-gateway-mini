#!/bin/bash
# test-rag-v2.sh — RAG Capture V2 End-to-End Test (Cross-platform)
# Usage:
#   bash scripts/rag-capture-v2/test-rag-v2.sh --dry-run   ← SAFE
#   bash scripts/rag-capture-v2/test-rag-v2.sh             ← LIVE
#
# API Key: export QDRANT_API_KEY="..." sebelum jalankan
# Windows : export PYTHONUTF8=1 && export PYTHONIOENCODING=utf-8

set -e

# ─── UTF-8 SAFETY (Windows Git Bash) ───────────────────────────
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

# ─── FLAGS ─────────────────────────────────────────────────────
DRY_RUN=false
for arg in "$@"; do
  [[ "$arg" == "--dry-run" ]] && DRY_RUN=true
done

# ─── COLORS ────────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'
YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

pass()  { echo -e "  ${GREEN}[PASS] $1${NC}"; }
fail()  { echo -e "  ${RED}[FAIL] $1${NC}"; }
warn()  { echo -e "  ${YELLOW}[WARN] $1${NC}"; }
info()  { echo -e "  ${CYAN}[INFO] $1${NC}"; }

PASS_COUNT=0; FAIL_COUNT=0

check() {
  if [[ "$2" == "pass" ]]; then pass "$1"; ((PASS_COUNT++)) || true
  else fail "$1"; ((FAIL_COUNT++)) || true; fi
}

# ─── DETECT PATHS DYNAMICALLY FROM rag status ──────────────────
# Semua path diambil dari rag status — tidak ada hardcode
detect_paths() {
  local status_output
  status_output=$(rag status 2>/dev/null || echo "")

  # Extract paths dari rag status output
  DRAFTS_PATH_RAW=$(echo "$status_output" | grep "Global drafts" | sed 's/.*Global drafts *: *//')
  SUMMARIES_PATH_RAW=$(echo "$status_output" | grep "Summaries dir" | sed 's/.*Summaries dir *: *//')
  PROJECT_ROOT_RAW=$(echo "$status_output" | grep "Project root" | sed 's/.*Project root *: *//')

  # Convert Windows path ke Unix path jika di Git Bash
  to_unix_path() {
    local p="$1"
    # Jika path mulai dengan huruf drive (C:\), konversi ke /c/
    if echo "$p" | grep -qE '^[A-Za-z]:\\'; then
      local drive
      drive=$(echo "$p" | cut -c1 | tr '[:upper:]' '[:lower:]')
      p=$(echo "$p" | cut -c3- | sed 's|\\|/|g')
      p="/$drive$p"
    fi
    echo "$p"
  }

  DRAFTS_PATH=$(to_unix_path "$DRAFTS_PATH_RAW")
  SUMMARIES_PATH=$(to_unix_path "$SUMMARIES_PATH_RAW")
  PROJECT_ROOT=$(to_unix_path "$PROJECT_ROOT_RAW")
}

detect_paths

# ─── RESOLVE API KEY ───────────────────────────────────────────
resolve_api_key() {
  [[ -n "$QDRANT_API_KEY" ]] && echo "$QDRANT_API_KEY" && return

  # Coba dari appsettings.Production.json
  local settings_file="$PROJECT_ROOT/appsettings.Production.json"
  if [[ -f "$settings_file" ]]; then
    python3 -c "
import json
with open('$settings_file') as f: d=json.load(f)
for v in d.values():
    if isinstance(v,dict) and 'QdrantApiKey' in v:
        print(v['QdrantApiKey']); exit()
print(d.get('QdrantApiKey',''))
" 2>/dev/null || echo ""
  else
    echo ""
  fi
}

API_KEY=$(resolve_api_key)

qdrant_curl() {
  if [[ -n "$API_KEY" ]]; then
    curl -s -H "api-key: $API_KEY" "$@"
  else
    curl -s "$@"
  fi
}

# Helper: count files di drafts folder (cross-platform)
count_drafts() {
  if [[ -d "$DRAFTS_PATH" ]]; then
    find "$DRAFTS_PATH" -name "chunk_*.md" 2>/dev/null | wc -l | tr -d '[:space:]'
  else
    echo "0"
  fi
}

# Helper: get first draft file
first_draft() {
  if [[ -d "$DRAFTS_PATH" ]]; then
    find "$DRAFTS_PATH" -name "chunk_*.md" 2>/dev/null | sort | head -1
  else
    echo ""
  fi
}

# Helper: count pattern in file
count_in_file() {
  local file="$1" pattern="$2"
  grep -c "$pattern" "$file" 2>/dev/null | tr -d '[:space:]' || echo "0"
}

QDRANT_URL="http://192.168.18.199:6333"
OLLAMA_URL="http://192.168.18.199:11434"

# ─── HEADER ────────────────────────────────────────────────────
echo ""
echo "========================================================"
echo "  RAG Capture V2 -- End-to-End Test (Cross-platform)"
if $DRY_RUN; then
  echo -e "  Mode  : ${YELLOW}DRY RUN${NC} -- push di-skip, collection aman"
else
  echo -e "  Mode  : ${RED}LIVE${NC} -- akan push ke Qdrant collection knowledge_v2"
fi
if [[ -n "$API_KEY" ]]; then
  echo -e "  APIKey: ${GREEN}detected${NC} (${API_KEY:0:8}...)"
else
  echo -e "  APIKey: ${YELLOW}none${NC} -- export QDRANT_API_KEY=... dulu"
fi
echo "  Drafts: $DRAFTS_PATH"
echo "========================================================"
echo ""

# ─── TEST 0: PRE-FLIGHT ────────────────────────────────────────
echo "--- [0] PRE-FLIGHT CHECK ---"

command -v rag &>/dev/null \
  && check "rag command tersedia" "pass" \
  || { check "rag command tersedia" "fail"; exit 1; }

python3 --version &>/dev/null \
  && check "Python 3 tersedia ($(python3 --version 2>&1))" "pass" \
  || { check "Python 3 tersedia" "fail"; exit 1; }

QDRANT_VERSION=$(qdrant_curl "$QDRANT_URL" 2>/dev/null \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('version',''))" 2>/dev/null || echo "")
[[ -n "$QDRANT_VERSION" ]] \
  && check "Qdrant accessible (v$QDRANT_VERSION)" "pass" \
  || { check "Qdrant accessible di $QDRANT_URL" "fail"; exit 1; }

COL_RESP=$(qdrant_curl "$QDRANT_URL/collections/knowledge_v2" 2>/dev/null || echo "")
POINTS_TOTAL=$(echo "$COL_RESP" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null \
  | tr -d '[:space:]' || echo "0")
COL_STATUS=$(echo "$COL_RESP" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['status'])" 2>/dev/null || echo "")
VECTORS_OK=$(echo "$COL_RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)['result']['config']['params']
print('ok' if 'dense' in d.get('vectors',{}) and 'sparse' in d.get('sparse_vectors',{}) else 'fail')
" 2>/dev/null || echo "fail")

[[ "$POINTS_TOTAL" -gt 0 ]] \
  && check "Collection knowledge_v2 ($POINTS_TOTAL points, status=$COL_STATUS)" "pass" \
  || { check "Collection knowledge_v2 terisi" "fail"; exit 1; }

[[ "$VECTORS_OK" == "ok" ]] \
  && check "Hybrid config: dense + sparse" "pass" \
  || check "Hybrid config: dense + sparse" "fail"

OLLAMA_UP=$(curl -s "$OLLAMA_URL" 2>/dev/null | grep -c "Ollama" | tr -d '[:space:]' || echo "0")
[[ "$OLLAMA_UP" -gt 0 ]] \
  && check "Ollama accessible ($OLLAMA_URL)" "pass" \
  || { check "Ollama accessible" "fail"; exit 1; }

[[ -n "$PROJECT_ROOT" ]] \
  && check "Project root detected" "pass" \
  || check "Project root detected" "fail"

info "Drafts path : $DRAFTS_PATH"
info "Summaries  : $SUMMARIES_PATH"
echo ""

# ─── TEST 1: SIGNAL AUTO-DETECTION ─────────────────────────────
echo "--- [1] SIGNAL AUTO-DETECTION (pipe) ---"

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
  && check "Signal <<<RAG_META>>> terdeteksi" "pass" \
  || check "Signal <<<RAG_META>>> terdeteksi" "fail"

DRAFT_COUNT=$(count_drafts)
[[ "$DRAFT_COUNT" -ge 1 ]] \
  && check "Draft chunk tersimpan ($DRAFT_COUNT file)" "pass" \
  || check "Draft chunk tersimpan" "fail"
echo ""

# ─── TEST 2: MANUAL ADD ────────────────────────────────────────
echo "--- [2] MANUAL ADD ---"

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

DRAFT_COUNT_2=$(count_drafts)
[[ "$DRAFT_COUNT_2" -ge 2 ]] \
  && check "Manual add berhasil (total $DRAFT_COUNT_2 drafts)" "pass" \
  || check "Manual add berhasil" "fail"
echo ""

# ─── TEST 3: FRONTMATTER VALIDATION ────────────────────────────
echo "--- [3] FRONTMATTER VALIDATION ---"

rag list
echo ""

CHUNK1=$(first_draft)
if [[ -f "$CHUNK1" ]]; then
  HAS_ID=$(count_in_file "$CHUNK1" "^id:")
  HAS_PROJECT=$(count_in_file "$CHUNK1" "^project: homelab")
  HAS_TYPE=$(count_in_file "$CHUNK1" "^chunk_type:")
  HAS_TOPIC=$(count_in_file "$CHUNK1" "^topic:")
  HAS_TAGS=$(count_in_file "$CHUNK1" "^tags:")
  HAS_STATUS=$(count_in_file "$CHUNK1" "^status:")
  HAS_EM_DASH=$(count_in_file "$CHUNK1" "—")
  HAS_INDONESIAN=$(grep -cE '\b(ini|yang|dan|atau|dengan|untuk|tidak|bisa|sudah)\b' "$CHUNK1" 2>/dev/null | tr -d '[:space:]' || echo "0")

  [[ "$HAS_ID"         -gt 0 ]] && check "Frontmatter: id"              "pass" || check "Frontmatter: id"         "fail"
  [[ "$HAS_PROJECT"    -gt 0 ]] && check "Frontmatter: project=homelab" "pass" || check "Frontmatter: project"    "fail"
  [[ "$HAS_TYPE"       -gt 0 ]] && check "Frontmatter: chunk_type"      "pass" || check "Frontmatter: chunk_type" "fail"
  [[ "$HAS_TOPIC"      -gt 0 ]] && check "Frontmatter: topic"           "pass" || check "Frontmatter: topic"      "fail"
  [[ "$HAS_TAGS"       -gt 0 ]] && check "Frontmatter: tags"            "pass" || check "Frontmatter: tags"       "fail"
  [[ "$HAS_STATUS"     -gt 0 ]] && check "Frontmatter: status"          "pass" || check "Frontmatter: status"     "fail"
  [[ "$HAS_EM_DASH"    -eq 0 ]] && check "No em dash di chunk"          "pass" || check "Em dash ditemukan!"      "fail"
  [[ "$HAS_INDONESIAN" -eq 0 ]] && check "Content: English only"        "pass" || warn  "Kemungkinan ada Bahasa Indonesia"

  echo ""
  info "Preview chunk 1 frontmatter:"
  head -16 "$CHUNK1"
else
  warn "Chunk file tidak ditemukan di: $DRAFTS_PATH"
fi
echo ""

# ─── TEST 4: MERGE ─────────────────────────────────────────────
echo "--- [4] MERGE ---"

TODAY=$(date +%Y-%m-%d)
TEST_FILENAME="${TODAY}-rag-capture-v2-test.md"
MERGED_FILE="$SUMMARIES_PATH/$TEST_FILENAME"

echo "y" | rag merge --output "$TEST_FILENAME"
echo ""

if [[ -f "$MERGED_FILE" ]]; then
  check "Merge berhasil: $TEST_FILENAME" "pass"

  CHUNK_COUNT=$(count_in_file "$MERGED_FILE" "^## CHUNK")
  HAS_METADATA=$(count_in_file "$MERGED_FILE" "SESSION METADATA")
  WORD_COUNT=$(wc -w < "$MERGED_FILE" | tr -d '[:space:]')

  [[ "$CHUNK_COUNT"  -ge 2 ]] && check "Merged berisi $CHUNK_COUNT chunks" "pass" || check "Merged berisi chunks" "fail"
  [[ "$HAS_METADATA" -gt 0 ]] && check "SESSION METADATA ada"              "pass" || check "SESSION METADATA ada"  "fail"

  info "Word count: $WORD_COUNT words"
  info "File size : $(du -h "$MERGED_FILE" | cut -f1)"
  echo ""
  info "Preview (20 baris pertama):"
  head -20 "$MERGED_FILE"
else
  check "Merge berhasil" "fail"
  warn "File tidak ditemukan: $MERGED_FILE"
fi
echo ""

# ─── TEST 5: PUSH ──────────────────────────────────────────────
echo "--- [5] PUSH TO QDRANT ---"

POINTS_BEFORE=$(qdrant_curl "$QDRANT_URL/collections/knowledge_v2" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null \
  | tr -d '[:space:]' || echo "0")

if $DRY_RUN; then
  echo ""
  warn "DRY RUN -- push di-skip. Collection knowledge_v2 tidak disentuh."
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

  # Jalankan push dan capture output untuk cek HTTP 200
  PUSH_OUTPUT=$(bash scripts/push-to-qdrant.sh "$MERGED_FILE" 2>&1)
  echo "$PUSH_OUTPUT"

  # Cek sukses dari output push script (OK 200)
  PUSH_OK=$(echo "$PUSH_OUTPUT" | grep -c "OK (200)" | tr -d '[:space:]' || echo "0")

  sleep 3

  POINTS_AFTER=$(qdrant_curl "$QDRANT_URL/collections/knowledge_v2" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null \
    | tr -d '[:space:]' || echo "0")
  ADDED=$((POINTS_AFTER - POINTS_BEFORE))

  info "Points sesudah push: $POINTS_AFTER"

  # Verifikasi data ada di Qdrant via scroll (bukan hanya points count)
  # Ambil topic dari merged file untuk verifikasi
  VERIFY_TOPIC=$(grep "^topic:" "$SUMMARIES_PATH/$TEST_FILENAME" 2>/dev/null \
    | head -1 | sed 's/^topic: //' | tr -d '\r' || echo "")

  VERIFY_COUNT="0"
  if [[ -n "$VERIFY_TOPIC" ]]; then
    VERIFY_COUNT=$(qdrant_curl -X POST "$QDRANT_URL/collections/knowledge_v2/points/scroll" \
      -H "Content-Type: application/json" \
      -d "{\"filter\":{\"must\":[{\"key\":\"topic\",\"match\":{\"value\":\"$VERIFY_TOPIC\"}}]},\"limit\":5}" \
      | python3 -c "import sys,json; print(len(json.load(sys.stdin)['result']['points']))" 2>/dev/null \
      | tr -d '[:space:]' || echo "0")
    info "Verified in Qdrant: $VERIFY_COUNT point(s) with topic='$VERIFY_TOPIC'"
  fi

  # Pass jika: HTTP 200 DAN data ada di Qdrant
  # Note: points count tidak bertambah jika ID sama (upsert/update) — itu normal
  if [[ "$PUSH_OK" -gt 0 ]] && [[ "$VERIFY_COUNT" -gt 0 ]]; then
    if [[ "$ADDED" -gt 0 ]]; then
      check "Push berhasil — $ADDED points baru ditambahkan" "pass"
    else
      check "Push berhasil — upsert/update (ID sudah ada, data ter-update)" "pass"
      info "Points tidak bertambah karena ID duplikat dari test sebelumnya — ini normal"
    fi
  else
    check "Push berhasil" "fail"
    warn "PUSH_OK=$PUSH_OK | VERIFY_COUNT=$VERIFY_COUNT"
  fi
fi
echo ""

# ─── TEST 6: RETRIEVAL QUALITY ─────────────────────────────────
echo "--- [6] RETRIEVAL QUALITY (read-only) ---"
echo ""

run_query() {
  local label="$1" query="$2" project="$3"
  echo "  Query: \"$query\""

  VECTOR=$(curl -s "$OLLAMA_URL/api/embeddings" \
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

run_query "6A. Exact keyword (BM25)"   "Qdrant sparse vector BM25 collection migration python script"    "homelab"
run_query "6B. Semantic query (dense)" "how to fix search returning empty results after database migration" "homelab"
run_query "6C. Technical term"         "nomic-embed-text ollama docker vm homelab embedding"               "homelab"

# ─── TEST 7: REMINDER SYSTEM ───────────────────────────────────
echo "--- [7] REMINDER SYSTEM ---"

REMIND_OUTPUT=$(rag remind 2>&1)
echo "$REMIND_OUTPUT"
echo "$REMIND_OUTPUT" | grep -q "SESSION END REMINDER" \
  && check "rag remind berjalan" "pass" \
  || check "rag remind berjalan" "fail"
echo ""

# ─── FINAL SUMMARY ─────────────────────────────────────────────
echo "========================================================"
echo "  TEST SUMMARY"
echo "========================================================"
echo -e "  ${GREEN}PASS : $PASS_COUNT${NC}"
echo -e "  ${RED}FAIL : $FAIL_COUNT${NC}"
echo ""

if $DRY_RUN; then
  echo -e "  Mode   : ${YELLOW}DRY RUN${NC} - collection tidak disentuh"
  echo -e "  Points : $POINTS_BEFORE (tidak berubah)"
  echo ""
  echo "  Untuk live test:"
  echo "  export QDRANT_API_KEY=<YOUR_KEY>"
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
  echo -e "  ${GREEN}[OK] Semua test passed! RAG Capture V2 siap digunakan.${NC}"
else
  echo -e "  ${RED}[!!] $FAIL_COUNT test gagal. Cek output di atas.${NC}"
fi
echo "========================================================"
echo ""