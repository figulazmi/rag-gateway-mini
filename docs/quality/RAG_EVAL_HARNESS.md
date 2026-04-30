# RAG Evaluation Harness — Retrieval Quality Tracker

Tracks benchmark metrics and test results for `knowledge_v2` collection on VM B1.
Baseline defined 2026-04-29. Re-run after any significant pipeline change.

> **How to use:** Run the test queries in Section 3 against the live system.
> Record scores in the Baseline vs Current table. Target thresholds defined in Section 2.
> For task/status tracking, follow [`../reference/TRACKING_STATUS_STANDARD.md`](../reference/TRACKING_STATUS_STANDARD.md).
> Green = at/above target. Red = below target. Cross-reference `RAG_SECURITY_POSTURE.md` for hardening tasks.

---

## Status Legend

- `[x] MET` — metric at or above target
- `[ ] NOT MET` — below target, action required
- `[?] UNMEASURED` — no data yet

---

## 1. Stack Snapshot

| Component | Value | Notes |
|---|---|---|
| Collection | `knowledge_v2` | Hybrid dense + sparse |
| Embedding model | `nomic-embed-text` | 768-dim cosine |
| Query embed prefix | `This chunk is from project {p}. Content: {normalized}` | v2 format |
| Ingest embed prefix | `This chunk is from project {p}, type {t}, topic {topic}, tagged {tags}. Session date {d}. Content: {body}` | n8n ingest format |
| Hybrid search | Dense prefetch=30, Sparse prefetch=5, score_thresh=0.01, RRF fusion, top-8 | `RagGatewayOptions` |
| LLM (generation) | `llama3.2:3b` | Local Ollama |
| LLM (code) | `qwen2.5-coder:7b` | Local Ollama |
| Chunk count | 368 | Live VM verification on 2026-04-30; older docs may show historical 252/296/350/359 checkpoints |
| Gateway endpoint | `http://192.168.18.199:5200` | VM B1 Docker |

---

## 2. Target Thresholds

| Metric | Definition | Target | Current | Status |
|---|---|---|---|---|
| **MRR@5** | Mean Reciprocal Rank in top-5 | ≥ 0.80 | 0.90 | `[x] MET` |
| **Hit Rate @3** | Correct chunk in top-3 | ≥ 0.85 | 1.00 | `[x] MET` |
| **NDCG@10** | Graded relevance, top-10 | ≥ 0.75 | 0.905 (NDCG@5 proxy) | `[x] MET` |
| **Faithfulness** | LLM output consistent with retrieved chunks | ≥ 0.85 | — | `[?] UNMEASURED` |
| **Answer Relevance** | Output on-topic for the query | ≥ 0.80 | — | `[?] UNMEASURED` |
| **Context Precision** | Fraction of retrieved chunks actually used | ≥ 0.60 | — | `[?] UNMEASURED` |
| **Latency p50** | End-to-end query time, VM B1 CPU | ≤ 1.5s | — | `[?] UNMEASURED` |
| **Latency p95** | End-to-end query time, VM B1 CPU | ≤ 4.0s | — | `[?] UNMEASURED` |
| **Hallucination Rate** | Claims with zero chunk grounding | ≤ 5% | — | `[?] UNMEASURED` |
| **Cross-project contamination** | homelab result in project-alpha query (or vice versa) | 0% | 0% (no contamination observed in latest smoke/eval checks) | `[x] MET` |

**How to update Current column:**  
Run `eval-retrieval-quality.py` against VM B1, copy scores here, update Status.

---

## 3. Test Query Set (Labeled)

> Label format: `query | expected_doc_id | expected_rank | category`  
> Add rows as you build the eval set. Aim for ≥ 5 queries per category.

### 3.1 Factual Lookup

| # | Query | Expected doc_id | Expected rank ≤ | Last result |
|---|---|---|---|---|
| F-01 | "What IP address is VM B1 on Tailscale?" | (chunk with Tailscale IP) | 1 | — |
| F-02 | "What port does rag-gateway-mini listen on?" | (chunk with port 5200) | 1 | — |
| F-03 | "What embedding dimension does nomic-embed-text produce?" | nomic-embed-decision-chunk | 1 | — |
| F-04 | "What is the Qdrant collection name for knowledge_v2?" | (embed model decision chunk) | 2 | — |
| F-05 | "What user does SSH to VM B1 use?" | (vm-b1 access chunk) | 3 | — |

### 3.2 Code Pattern

| # | Query | Expected doc_id | Expected rank ≤ | Last result |
|---|---|---|---|---|
| C-01 | "How does push-to-qdrant.sh handle TimeoutExpired retry?" | (pipeline reliability chunk) | 2 | — |
| C-02 | "Bash pattern for failing fast when env var is missing" | (api-key scrub chunk) | 2 | — |
| C-03 | "Python pattern to guard against missing QDRANT_API_KEY" | (api-key scrub chunk) | 2 | — |
| C-04 | "What is the query embed content format for rag-gateway?" | (bottleneck fix #1 chunk) | 1 | — |
| C-05 | "How to compute cosine similarity between two Qdrant vectors?" | (verify_embed_cosine chunk) | 3 | — |

### 3.3 Runbook / Procedural

| # | Query | Expected doc_id | Expected rank ≤ | Last result |
|---|---|---|---|---|
| R-01 | "Steps to redeploy rag-gateway-mini after git push" | (vm-b1 deployment chunk) | 1 | — |
| R-02 | "How to push a knowledge chunk to Qdrant manually?" | (push-to-qdrant runbook chunk) | 2 | — |
| R-03 | "How to SSH to VM B1 from laptop?" | (vm-b1 access chunk) | 1 | — |
| R-04 | "How to run rag add and rag merge to save a session?" | (rag-capture-cli skill chunk) | 2 | — |
| R-05 | "How to check if a Qdrant chunk was successfully upserted?" | (rag pipeline reliability chunk) | 3 | — |

### 3.4 Decision / ADR

| # | Query | Expected doc_id | Expected rank ≤ | Last result |
|---|---|---|---|---|
| D-01 | "Why was nomic-embed-text chosen over bge-m3 and mxbai?" | nomic-embed-decision-chunk | 1 | — |
| D-02 | "Why was QueryNormalizer removed from the pipeline?" | (bottleneck fix #4 chunk) | 1 | — |
| D-03 | "Why does the RAG query use a prefix format for embedding?" | (bottleneck fix #1 chunk) | 1 | — |
| D-04 | "Why was sparse BM25 score threshold set to 0.01?" | (bottleneck fix #2 chunk) | 2 | — |
| D-05 | "Why is IDF weighting deferred (Opsi C)?" | (bottleneck fixes chunk) | 3 | — |

### 3.5 Cross-chunk Synthesis

| # | Query | Expected chunks | Min in top-5 | Last result |
|---|---|---|---|---|
| S-01 | "All known bugs fixed in the RAG ingestion pipeline" | multiple debug chunks | 3 | — |
| S-02 | "What security issues were found and fixed in rag-gateway-mini?" | api-key scrub + pipeline reliability | 2 | — |
| S-03 | "What bottlenecks were found in the hybrid search pipeline?" | bottleneck fix chunks | 3 | — |

### 3.6 Adversarial Near-miss (Semantic Precision)

| # | Query | Expected doc_id | Distractor doc_id | Correct ranks above distractor? |
|---|---|---|---|---|
| A-01 | "What embedding dimension does nomic-embed-text produce?" | nomic chunk (768) | any mxbai chunk (1024) | — |
| A-02 | "What port does rag-gateway-mini use?" | port 5200 chunk | any n8n port 5678 chunk | — |
| A-03 | "What IP was wrong in rag_config.json?" | pipeline reliability chunk (.169) | vm-b1 access chunk (.199) | — |

### 3.7 Negative (Out-of-Project, Should Return Empty or Low Score)

| # | Query | Project filter | Expected result |
|---|---|---|---|
| N-01 | "What is the project-alpha Blazor login flow?" | `project=homelab` | No results or score < 0.35 |
| N-02 | "How does EF Core migration work in eproc?" | `project=homelab` | No results or score < 0.35 |
| N-03 | "What is the weather in Jakarta today?" | `project=homelab` | No results |

---

## 4. Embed Prefix Alignment Validation

Run after any change to the query embed format or after bulk re-ingestion.

**Script:** `~/scripts/verify_embed_cosine.py` on VM B1

**Pass criteria:**
- `cos(stored_prefixed, raw_body) < 0.80` — confirms prefix shifts the embedding
- `cos(stored_prefixed, prefixed_query) ≥ 0.95` — confirms query lands near stored vector

| Run date | Chunks tested | Pass | Fail | Notes |
|---|---|---|---|---|
| — | — | — | — | Initial baseline not yet run |

**Command:**
```bash
ssh figulazmi@192.168.18.199 'python ~/scripts/verify_embed_cosine.py --sample 10'
```

---

## 5. Baseline vs Current Comparison

Fill in after first eval run. Update "Current" column with each subsequent run.

| Metric | Baseline (pre-fixes) | After embed prefix fix | After sparse fix | Current | Target |
|---|---|---|---|---|---|
| MRR@5 | ~0.45 (estimated) | ~0.65 (estimated) | 0.90 | 0.90 | ≥ 0.80 |
| Hit Rate @3 | — | — | 1.00 | 1.00 | ≥ 0.85 |
| p95 Latency | — | — | — | — | ≤ 4.0s |
| Faithfulness | — | — | — | — | ≥ 0.85 |

> **Note:** Pre-fix metrics are estimates from session notes (2026-04-25). First real measurement
> will be the actual baseline. Run `eval-retrieval-quality.py` to populate.

---

## 6. Eval Harness — How to Run

**Prerequisites:**
```bash
# On laptop: source env file
source ~/.config/qdrant-knowledge.env

# Verify gateway is up
curl http://192.168.18.199:5200/health
```

**Run eval:**
```bash
# Feed labeled query set to eval script
python scripts/eval-retrieval-quality.py \
  --eval-set docs/eval_queries.jsonl \
  --gateway http://192.168.18.199:5200 \
  --project homelab \
  --top-k 5

# Output: MRR@5, hit rate, per-category breakdown
```

**Build labeled eval set (first time):**
```bash
# Create eval_queries.jsonl from the test queries in Section 3
# Format per line:
# {"query": "...", "expected_doc_id": "...", "expected_rank": 1, "category": "factual"}
```

> **Status update:** Initial retrieval baseline has been measured (MRR@5, Hit@3, NDCG proxy).
> **Remaining TODO:** expand to end-to-end metrics (faithfulness, answer relevance, context precision, latency p50/p95) and keep `eval_queries.jsonl` as the canonical reproducible set.

---

*Last updated: 2026-04-30 · Author: Figur Ulul Azmi*  
*Cross-reference: [`RAG_SECURITY_POSTURE.md`](../security/RAG_SECURITY_POSTURE.md) (hardening tasks) · [`RAG_BOTTLENECK_FIXES.md`](../pipeline/RAG_BOTTLENECK_FIXES.md) (pipeline history)*
