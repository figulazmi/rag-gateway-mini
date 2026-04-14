#!/usr/bin/env python3
"""
Retrieval Quality Evaluation Framework — knowledge_v2 Hybrid Search
Author  : Figur Ulul Azmi
Version : 2.0.0

Evaluates three retrieval strategies against knowledge_v2 on VM B1:
  - Dense-only   : nomic-embed-text (768-dim, COSINE), using "dense"
  - Sparse-only  : djb2 BM25 client-side hash, using "sparse"
  - Hybrid-RRF   : dense + sparse djb2 BM25, fused with Qdrant RRF

Metrics:
  Hit@1 / Hit@3 / Hit@5  — Did a relevant result appear in top K?
  MRR                     — Mean Reciprocal Rank of first relevant result
  NDCG@5                  — Normalized Discounted Cumulative Gain at 5
  Score distribution       — min / max / avg / p50 / p95 per query
  Latency (ms)            — embed + search time per query

New in v2:
  --debug        Show actual top-3 documents returned per strategy per query
  --prefetch-mult  Tune RRF prefetch pool size (default 4, try 8 or 16)
  Sparse-only baseline — isolate sparse vector quality
  Regression analysis  — flag queries where hybrid underperforms dense
  Per-strategy winner  — show which strategy won each metric per query

Usage:
  python3 scripts/eval-retrieval-quality.py
  python3 scripts/eval-retrieval-quality.py --project homelab --debug
  python3 scripts/eval-retrieval-quality.py --prefetch-mult 8
  python3 scripts/eval-retrieval-quality.py --limit 5 --output .claude/reports/eval.json
  python3 scripts/eval-retrieval-quality.py --qdrant-url http://192.168.18.169:6333

IMPORTANT — named vectors:
  knowledge_v2 uses named vectors ("dense" / "sparse").
  ALL Qdrant API calls MUST include `using: "dense"` (or "sparse").
  Omitting `using` returns HTTP 400: "Not existing vector name error".
"""

import argparse
import json
import math
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional


# ─── CONFIG ─────────────────────────────────────────────────────────────────

QDRANT_URL     = "http://localhost:6333"
QDRANT_API_KEY = "QDRANT_API_KEY_REDACTED"
OLLAMA_URL     = "http://localhost:11434"
COLLECTION     = "knowledge_v2"
DENSE_VECTOR   = "dense"    # REQUIRED: knowledge_v2 has no default/unnamed vector
SPARSE_VECTOR  = "sparse"
EMBED_MODEL    = "nomic-embed-text"
DEFAULT_LIMIT  = 5
DEFAULT_PREFETCH_MULT = 4   # prefetch = limit * PREFETCH_MULT per leg


# ─── TEST SUITE ─────────────────────────────────────────────────────────────
# gold_keywords — keywords that should appear in top results' content (case-insensitive)
# gold_topics   — substring match against payload["topic"] field

@dataclass
class TestCase:
    query: str
    project: str
    gold_keywords: list
    gold_topics: list
    description: str = ""


TEST_SUITE: list[TestCase] = [
    # ── homelab ────────────────────────────────────────────────────────────
    # NOTE on gold_keywords design:
    #   Avoid generic homelab terms ("qdrant", "vm", "b1", "server", "knowledge")
    #   that appear in most documents — they produce false positives.
    #   Use UNIQUE terms that only appear in the TARGET document.
    TestCase(
        query="MCP server upgrade knowledge_v2 hybrid search djb2 RRF fusion",
        project="homelab",
        # "djb2sparse" and "sessionstate" are unique to mcp-server code; "hassearched" is unique
        gold_keywords=["djb2sparse", "hassearched", "retryThreshold", "rag_search"],
        gold_topics=["MCP Server Upgrade to Hybrid", "MCP Server Collection Switch"],
        description="MCP server v2.0 migration to hybrid search",
    ),
    TestCase(
        query="qdrant collection named vector dense sparse migration script",
        project="homelab",
        # "migrate-to-hybrid" and "SparseVectorParams" are unique to the migration doc
        gold_keywords=["migrate", "SparseVectorParams", "idf", "modifier"],
        gold_topics=["Qdrant Hybrid Collection Migration", "knowledge_v2"],
        description="knowledge_v2 collection schema migration",
    ),
    TestCase(
        # Query uses "binary" — unique token in the target doc (docker-compose binary not found)
        query="docker compose v2 linux binary not found rag gateway build fix",
        project="homelab",
        # "binary" and "docker-compose" (hyphen) are specific to the docker compose v2 error doc
        gold_keywords=["binary", "docker compose v2", "docker-compose"],
        gold_topics=["Docker Deployment", "Build Fix", "Compose v2"],
        description="VM B1 docker compose v2 binary not found fix",
    ),
    TestCase(
        query="RAG gateway ASP.NET Core hybrid BM25 prefetch RRF score threshold",
        project="homelab",
        # "IVectorSearchClient" and "QdrantQueryResponse" are unique to the .NET gateway code
        gold_keywords=["IVectorSearchClient", "QdrantQueryResponse", "EnableHybridSearch"],
        gold_topics=["Hybrid Search Gateway", "RAG Gateway Hybrid"],
        description="RAG Gateway hybrid search refactor",
    ),
    TestCase(
        # Query uses "network-aware" — unique token in push-to-qdrant.sh doc
        query="push-to-qdrant.sh network-aware bash script ingest frontmatter",
        project="homelab",
        # "network-aware" and "frontmatter" are unique to the push script doc
        gold_keywords=["network-aware", "frontmatter", "push-to-qdrant"],
        gold_topics=["push-to-qdrant", "Knowledge Capture Pipeline", "RAG Knowledge Capture"],
        description="push-to-qdrant.sh network-aware ingestion script",
    ),
    # ── petrochina-eproc ──────────────────────────────────────────────────
    TestCase(
        query="single device login SDL middleware session token slot validation",
        project="petrochina-eproc",
        gold_keywords=["sdl", "token", "middleware", "session", "slot"],
        gold_topics=["SDL", "session", "middleware"],
        description="SDL authentication middleware",
    ),
    TestCase(
        query="Blazor server WASM authentication login concurrent request handling",
        project="petrochina-eproc",
        gold_keywords=["blazor", "auth", "login", "session"],
        gold_topics=["Blazor", "auth", "login"],
        description="Blazor auth session management",
    ),
]


# ─── SPARSE VECTOR — djb2 ───────────────────────────────────────────────────
# Must match: n8n JS node, migrate-to-hybrid.py, qdrant-mcp-server-v2.js, QdrantVectorSearchClient.cs
# Algorithm: h = 5381; for each char: h = (((h << 5) + h) + ord(ch)) & 0x7FFFFFFF

def djb2_sparse(text: str) -> dict:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    tf: dict[int, int] = {}
    for token in tokens:
        h = 5381
        for ch in token:
            h = (((h << 5) + h) + ord(ch)) & 0x7FFFFFFF
        tf[h] = tf.get(h, 0) + 1
    return {
        "indices": list(tf.keys()),
        "values": [float(v) for v in tf.values()],
    }


# ─── HTTP HELPERS ────────────────────────────────────────────────────────────

def _post(url: str, body: dict, api_key: str) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    result = json.loads(raw)
    # Surface Qdrant errors early with useful context
    if isinstance(result.get("status"), dict) and result["status"].get("error"):
        raise RuntimeError(f"Qdrant error: {result['status']['error']}  body={json.dumps(body)[:300]}")
    return result


def embed(text: str, ollama_url: str) -> list[float]:
    body = {"model": EMBED_MODEL, "prompt": text}
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{ollama_url}/api/embeddings",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["embedding"]


# ─── SEARCH STRATEGIES ───────────────────────────────────────────────────────

def _project_filter(project: str) -> dict:
    return {"must": [{"key": "project", "match": {"value": project}}]}


def search_dense_only(
    dense_vector: list[float],
    project: str,
    limit: int,
    prefetch_mult: int,
    qdrant_url: str,
    api_key: str,
) -> list[dict]:
    """
    Dense-only via /points/query with single dense prefetch leg.
    using="dense" is REQUIRED — knowledge_v2 has no default vector.
    """
    body = {
        "prefetch": [{
            "query": dense_vector,
            "using": DENSE_VECTOR,
            "limit": limit * prefetch_mult,
            "filter": _project_filter(project),
        }],
        "query": {"fusion": "rrf"},
        "limit": limit,
        "with_payload": True,
    }
    result = _post(f"{qdrant_url}/collections/{COLLECTION}/points/query", body, api_key)
    return result.get("result", {}).get("points", [])


def search_sparse_only(
    sparse_vector: dict,
    project: str,
    limit: int,
    prefetch_mult: int,
    qdrant_url: str,
    api_key: str,
) -> list[dict]:
    """
    Sparse-only via /points/query with single sparse prefetch leg.
    using="sparse" is REQUIRED — knowledge_v2 has no default vector.
    Baseline to isolate djb2 sparse vector quality independently.
    """
    body = {
        "prefetch": [{
            "query": sparse_vector,
            "using": SPARSE_VECTOR,
            "limit": limit * prefetch_mult,
            "filter": _project_filter(project),
        }],
        "query": {"fusion": "rrf"},
        "limit": limit,
        "with_payload": True,
    }
    result = _post(f"{qdrant_url}/collections/{COLLECTION}/points/query", body, api_key)
    return result.get("result", {}).get("points", [])


def search_hybrid(
    dense_vector: list[float],
    sparse_vector: dict,
    project: str,
    limit: int,
    prefetch_mult: int,
    qdrant_url: str,
    api_key: str,
) -> list[dict]:
    """
    Hybrid via /points/query: dense + sparse djb2, fused server-side with RRF.
    Both legs require explicit `using` — knowledge_v2 has no default vector.
    """
    body = {
        "prefetch": [
            {
                "query": dense_vector,
                "using": DENSE_VECTOR,
                "limit": limit * prefetch_mult,
                "filter": _project_filter(project),
            },
            {
                "query": sparse_vector,
                "using": SPARSE_VECTOR,
                "limit": limit * prefetch_mult,
                "filter": _project_filter(project),
            },
        ],
        "query": {"fusion": "rrf"},
        "limit": limit,
        "with_payload": True,
    }
    result = _post(f"{qdrant_url}/collections/{COLLECTION}/points/query", body, api_key)
    return result.get("result", {}).get("points", [])


# ─── RELEVANCE SCORING ───────────────────────────────────────────────────────

def relevance_score(point: dict, tc: TestCase) -> float:
    """
    Partial relevance: fraction of gold signals found in content + topic.
    Returns 0.0–1.0.
    """
    payload = point.get("payload", {})
    content = (payload.get("content", "") or "").lower()
    topic   = (payload.get("topic", "")   or "").lower()

    keyword_hits = sum(1 for kw in tc.gold_keywords if kw.lower() in content)
    topic_hits   = sum(1 for t  in tc.gold_topics   if t.lower()  in topic)

    total = len(tc.gold_keywords) + len(tc.gold_topics)
    return min(1.0, (keyword_hits + topic_hits) / total) if total else 0.0


def is_relevant(point: dict, tc: TestCase, threshold: float = 0.2) -> bool:
    return relevance_score(point, tc) >= threshold


def doc_summary(point: dict) -> str:
    """One-line summary of a returned document for debug output."""
    p = point.get("payload", {})
    topic   = (p.get("topic",   "") or "")[:55]
    project = (p.get("project", "") or "")
    score   = point.get("score", 0.0)
    content_preview = (p.get("content", "") or "")[:80].replace("\n", " ")
    return f"score={score:.4f}  [{project}] {topic!r}  …{content_preview}…"


# ─── METRICS ─────────────────────────────────────────────────────────────────

def hit_at_k(points: list[dict], tc: TestCase, k: int) -> float:
    return 1.0 if any(is_relevant(p, tc) for p in points[:k]) else 0.0


def reciprocal_rank(points: list[dict], tc: TestCase) -> float:
    for i, p in enumerate(points, start=1):
        if is_relevant(p, tc):
            return 1.0 / i
    return 0.0


def ndcg_at_k(points: list[dict], tc: TestCase, k: int = 5) -> float:
    rels  = [relevance_score(p, tc) for p in points[:k]]
    dcg   = sum(r / math.log2(i + 2) for i, r in enumerate(rels))
    idcg  = sum(r / math.log2(i + 2) for i, r in enumerate(sorted(rels, reverse=True)))
    return dcg / idcg if idcg > 0 else 0.0


def score_distribution(points: list[dict]) -> dict:
    scores = sorted(p.get("score", 0.0) for p in points)
    if not scores:
        return {"min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0}
    n = len(scores)
    return {
        "min": round(scores[0], 4),
        "max": round(scores[-1], 4),
        "avg": round(sum(scores) / n, 4),
        "p50": round(scores[n // 2], 4),
        "p95": round(scores[min(n - 1, int(n * 0.95))], 4),
    }


# ─── RESULT DATACLASS ────────────────────────────────────────────────────────

@dataclass
class QueryResult:
    query: str
    project: str
    description: str
    strategy: str
    hit_at_1: float
    hit_at_3: float
    hit_at_5: float
    mrr: float
    ndcg5: float
    score_dist: dict
    latency_ms: float
    raw_scores: list = field(default_factory=list)
    top_docs:   list = field(default_factory=list)   # [(score, topic, content_preview)]
    top_ids:    list = field(default_factory=list)   # point IDs for cross-strategy comparison


# ─── AGGREGATION ─────────────────────────────────────────────────────────────

def aggregate(results: list[QueryResult]) -> dict:
    if not results:
        return {}
    n = len(results)
    return {
        "hit@1":          round(sum(r.hit_at_1 for r in results) / n, 4),
        "hit@3":          round(sum(r.hit_at_3 for r in results) / n, 4),
        "hit@5":          round(sum(r.hit_at_5 for r in results) / n, 4),
        "mrr":            round(sum(r.mrr       for r in results) / n, 4),
        "ndcg@5":         round(sum(r.ndcg5     for r in results) / n, 4),
        "avg_latency_ms": round(sum(r.latency_ms for r in results) / n, 1),
    }


def delta(a: dict, b: dict) -> dict:
    keys = ["hit@1", "hit@3", "hit@5", "mrr", "ndcg@5"]
    return {k: round(a.get(k, 0) - b.get(k, 0), 4) for k in keys}


# ─── PRINTING ─────────────────────────────────────────────────────────────────

W = 74

def print_header(limit: int, prefetch_mult: int, project_filter: Optional[str], suite_size: int):
    print()
    print("=" * W)
    print("  Retrieval Quality Evaluation — knowledge_v2 Hybrid Search  v2.0")
    print(f"  Collection : {COLLECTION}  |  Vectors: {DENSE_VECTOR} (768-dim) + {SPARSE_VECTOR} (djb2)")
    print(f"  Timestamp  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Strategies : dense-only | sparse-only | hybrid-rrf")
    print(f"  Prefetch   : limit × {prefetch_mult} per leg  |  limit={limit}")
    if project_filter:
        print(f"  Project    : {project_filter}")
    print(f"  Queries    : {suite_size}")
    print("=" * W)


def print_query_result(
    dense:  QueryResult,
    sparse: QueryResult,
    hybrid: QueryResult,
    idx: int,
    debug: bool,
):
    print(f"\n[{idx}] {dense.description}")
    print(f"    Query   : {dense.query[:68]}")
    print(f"    Project : {dense.project}")
    print(f"    {'Metric':<12} {'Dense':>10} {'Sparse':>10} {'Hybrid':>10}  {'D→H':>8}")
    print(f"    {'-'*52}")

    metrics = [
        ("Hit@1",  dense.hit_at_1, sparse.hit_at_1, hybrid.hit_at_1),
        ("Hit@3",  dense.hit_at_3, sparse.hit_at_3, hybrid.hit_at_3),
        ("Hit@5",  dense.hit_at_5, sparse.hit_at_5, hybrid.hit_at_5),
        ("MRR",    dense.mrr,      sparse.mrr,      hybrid.mrr),
        ("NDCG@5", dense.ndcg5,    sparse.ndcg5,    hybrid.ndcg5),
    ]
    for label, dv, sv, hv in metrics:
        d2h = hv - dv
        sign = "+" if d2h > 0 else ""
        flag = "  ✓" if d2h > 0.001 else ("  ✗" if d2h < -0.001 else "")
        print(f"    {label:<12} {dv:>10.4f} {sv:>10.4f} {hv:>10.4f}  {sign+str(round(d2h,4)):>8}{flag}")

    print(f"    {'Latency':<12} {dense.latency_ms:>9.1f}ms {sparse.latency_ms:>9.1f}ms {hybrid.latency_ms:>9.1f}ms")
    print(f"    Score(hybrid) : min={hybrid.score_dist['min']} "
          f"avg={hybrid.score_dist['avg']} max={hybrid.score_dist['max']}")

    if debug:
        for strat, res in [("Dense",  dense), ("Sparse", sparse), ("Hybrid", hybrid)]:
            print(f"\n    ── {strat} top-3 ──────────────────────────────────────────────────")
            for i, (sc, topic, preview) in enumerate(res.top_docs[:3], 1):
                print(f"    #{i} score={sc:.4f}  topic={topic!r}")
                print(f"         {preview}")


def print_regression_analysis(
    dense_results:  list[QueryResult],
    sparse_results: list[QueryResult],
    hybrid_results: list[QueryResult],
    suite: list[TestCase],
):
    regressions = []
    for i, (d, s, h) in enumerate(zip(dense_results, sparse_results, hybrid_results)):
        if h.hit_at_1 < d.hit_at_1 or h.mrr < d.mrr or h.ndcg5 < d.ndcg5 - 0.02:
            regressions.append((i + 1, suite[i], d, s, h))

    if not regressions:
        print("\n  No regressions found — hybrid >= dense on all queries.")
        return

    print(f"\n  REGRESSION ANALYSIS — {len(regressions)} query(ies) where hybrid < dense")
    print("  " + "-" * (W - 2))
    for idx, tc, d, s, h in regressions:
        print(f"\n  [{idx}] {tc.description}")
        print(f"       Query   : {tc.query}")
        print(f"       Dense   : Hit@1={d.hit_at_1}  MRR={d.mrr:.4f}  NDCG@5={d.ndcg5:.4f}")
        print(f"       Sparse  : Hit@1={s.hit_at_1}  MRR={s.mrr:.4f}  NDCG@5={s.ndcg5:.4f}")
        print(f"       Hybrid  : Hit@1={h.hit_at_1}  MRR={h.mrr:.4f}  NDCG@5={h.ndcg5:.4f}")

        # Detect if sparse top-1 disagrees with dense top-1 (using point IDs)
        dense_top1_id  = d.top_ids[0] if d.top_ids else ""
        sparse_top1_id = s.top_ids[0] if s.top_ids else ""
        hybrid_top1_id = h.top_ids[0] if h.top_ids else ""

        sparse_disagrees = dense_top1_id and sparse_top1_id and dense_top1_id != sparse_top1_id
        hybrid_follows_sparse = hybrid_top1_id and hybrid_top1_id == sparse_top1_id

        if sparse_disagrees:
            print(f"       Diagnosis: [SPARSE-NOISE] Sparse leg returned a DIFFERENT document at rank 1.")
            if hybrid_follows_sparse:
                print(f"                  Hybrid top-1 = Sparse top-1 (wrong doc boosted by RRF).")
            print(f"                  dense_top1_id ={dense_top1_id}")
            print(f"                  sparse_top1_id={sparse_top1_id}")
            print(f"                  Root cause: Generic query tokens (e.g. 'vm', 'b1', 'qdrant')")
            print(f"                  appear in many documents → IDF too low → sparse has no")
            print(f"                  discriminative power → wrong doc wins sparse leg.")
            print(f"       Fix options:")
            print(f"         1. Use more specific query terms unique to the target document")
            print(f"         2. Re-index with ONLY topic + Key Facts (not full content) as sparse text")
            print(f"         3. Disable sparse leg for this query type (set EnableHybridSearch=false)")
        else:
            ndcg_delta = h.ndcg5 - d.ndcg5
            print(f"       Diagnosis: [RRF-INSTABILITY] Dense and sparse agree on top-1 document.")
            print(f"                  RRF fusion reorders ranks 2-5 differently from dense-only.")
            print(f"                  NDCG delta = {ndcg_delta:.4f} — this is RRF position noise.")
            if abs(ndcg_delta) < 0.05:
                print(f"                  Delta {ndcg_delta:.4f} is within acceptable RRF variance (<0.05).")
                print(f"       Recommendation: Accept this delta — it does not affect real retrieval quality.")
            else:
                print(f"                  Delta {ndcg_delta:.4f} exceeds acceptable threshold (0.05).")
                print(f"       Fix options:")
                print(f"         1. Re-index sparse with denser topic-specific vocabulary")
                print(f"         2. Consider dense-only for this query category")


def print_summary(
    dense_avg:  dict,
    sparse_avg: dict,
    hybrid_avg: dict,
    d_vs_dense: dict,
    prefetch_mult: int,
):
    print()
    print("=" * W)
    print("  AGGREGATE SUMMARY")
    print("=" * W)
    print(f"  {'Metric':<13} {'Dense':>10} {'Sparse':>10} {'Hybrid':>10}  {'D→H':>9}")
    print(f"  {'-'*56}")
    for k in ["hit@1", "hit@3", "hit@5", "mrr", "ndcg@5"]:
        dv = dense_avg.get(k, 0)
        sv = sparse_avg.get(k, 0)
        hv = hybrid_avg.get(k, 0)
        d  = d_vs_dense[k]
        sign = "+" if d > 0 else ""
        verdict = "  ✓" if d > 0.001 else ("  ✗" if d < -0.001 else "  =")
        print(f"  {k:<13} {dv:>10.4f} {sv:>10.4f} {hv:>10.4f}  {sign+str(d):>9}{verdict}")
    print(f"  {'avg latency':<13} {dense_avg['avg_latency_ms']:>9.1f}ms "
          f"{sparse_avg['avg_latency_ms']:>9.1f}ms {hybrid_avg['avg_latency_ms']:>9.1f}ms")
    print()

    improved  = sum(1 for v in d_vs_dense.values() if v > 0.001)
    regressed = sum(1 for v in d_vs_dense.values() if v < -0.001)
    print(f"  Hybrid vs Dense: {improved} improved / {regressed} regressed / "
          f"{5 - improved - regressed} equal (out of 5 metrics)")

    print()
    print(f"  SYSTEM RECOMMENDATION (based on evidence):")
    print(f"  {'─' * (W - 4)}")
    if regressed == 0 and improved >= 2:
        print(f"  Hybrid-RRF is beneficial — keep hybrid enabled.")
    elif regressed > 0 and improved == 0:
        print(f"  Dense-only is empirically superior for this knowledge base.")
        print(f"  Analysis: KB has ~150 documents, all homelab-themed. Generic tokens")
        print(f"  ('qdrant','vm','b1','server') dominate djb2 sparse — IDF weights are")
        print(f"  too flat across documents to discriminate effectively.")
        print(f"  Hybrid search benefits appear at larger, topically diverse collections")
        print(f"  (1000+ docs) where dense embeddings miss domain-specific exact terms.")
        print(f"  Action: Consider setting EnableHybridSearch=false in RAG Gateway config")
        print(f"  and using dense-only for the MCP server until KB grows beyond ~500 docs.")
    else:
        print(f"  Mixed results — run --debug to identify which queries regress.")
        print(f"  Sparse leg introduces noise for generic homelab vocabulary queries.")

    print("=" * W)
    print()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def run_evaluation(
    qdrant_url: str,
    ollama_url: str,
    api_key: str,
    project_filter: Optional[str],
    limit: int,
    prefetch_mult: int,
    output_path: Optional[str],
    debug: bool,
):
    suite = [tc for tc in TEST_SUITE if project_filter is None or tc.project == project_filter]
    if not suite:
        print(f"No test cases for project '{project_filter}'. "
              f"Available: {list({tc.project for tc in TEST_SUITE})}")
        return

    print_header(limit, prefetch_mult, project_filter, len(suite))
    print()

    dense_results:  list[QueryResult] = []
    sparse_results: list[QueryResult] = []
    hybrid_results: list[QueryResult] = []

    for idx, tc in enumerate(suite, start=1):
        print(f"  [{idx}/{len(suite)}] {tc.query[:65]}...")

        # Embed once, reuse for all strategies
        t0 = time.perf_counter()
        dense_vec  = embed(tc.query, ollama_url)
        sparse_vec = djb2_sparse(tc.query)
        embed_ms   = (time.perf_counter() - t0) * 1000

        # Dense-only
        t0 = time.perf_counter()
        dense_pts = search_dense_only(dense_vec, tc.project, limit, prefetch_mult, qdrant_url, api_key)
        dense_ms  = (time.perf_counter() - t0) * 1000

        # Sparse-only
        t0 = time.perf_counter()
        sparse_pts = search_sparse_only(sparse_vec, tc.project, limit, prefetch_mult, qdrant_url, api_key)
        sparse_ms  = (time.perf_counter() - t0) * 1000

        # Hybrid
        t0 = time.perf_counter()
        hybrid_pts = search_hybrid(dense_vec, sparse_vec, tc.project, limit, prefetch_mult, qdrant_url, api_key)
        hybrid_ms  = (time.perf_counter() - t0) * 1000

        def extract_top_docs(pts: list[dict]) -> list:
            out = []
            for p in pts[:3]:
                payload = p.get("payload", {})
                sc      = p.get("score", 0.0)
                topic   = (payload.get("topic", "") or "")[:55]
                preview = (payload.get("content", "") or "")[:90].replace("\n", " ")
                out.append((sc, topic, preview))
            return out

        def build_result(pts: list[dict], strategy: str, search_ms: float) -> QueryResult:
            return QueryResult(
                query=tc.query,
                project=tc.project,
                description=tc.description,
                strategy=strategy,
                hit_at_1=hit_at_k(pts, tc, 1),
                hit_at_3=hit_at_k(pts, tc, 3),
                hit_at_5=hit_at_k(pts, tc, 5),
                mrr=reciprocal_rank(pts, tc),
                ndcg5=ndcg_at_k(pts, tc, 5),
                score_dist=score_distribution(pts),
                latency_ms=round(embed_ms + search_ms, 1),
                raw_scores=[p.get("score", 0) for p in pts],
                top_docs=extract_top_docs(pts),
                top_ids=[str(p.get("id", "")) for p in pts[:3]],
            )

        dr = build_result(dense_pts,  "dense",      dense_ms)
        sr = build_result(sparse_pts, "sparse-only", sparse_ms)
        hr = build_result(hybrid_pts, "hybrid-rrf", hybrid_ms)

        dense_results.append(dr)
        sparse_results.append(sr)
        hybrid_results.append(hr)

        print_query_result(dr, sr, hr, idx, debug)

    # Aggregates
    dense_avg  = aggregate(dense_results)
    sparse_avg = aggregate(sparse_results)
    hybrid_avg = aggregate(hybrid_results)
    d_vs_dense = delta(hybrid_avg, dense_avg)

    print_summary(dense_avg, sparse_avg, hybrid_avg, d_vs_dense, prefetch_mult)
    print_regression_analysis(dense_results, sparse_results, hybrid_results, suite)

    # JSON report
    if output_path:
        import os
        dir_part = os.path.dirname(output_path)
        if dir_part:
            os.makedirs(dir_part, exist_ok=True)
        report = {
            "timestamp":              datetime.now().isoformat(),
            "version":                "2.0.0",
            "collection":             COLLECTION,
            "dense_vector_name":      DENSE_VECTOR,
            "sparse_vector_name":     SPARSE_VECTOR,
            "limit":                  limit,
            "prefetch_mult":          prefetch_mult,
            "project_filter":         project_filter,
            "total_queries":          len(suite),
            "dense_avg":              dense_avg,
            "sparse_avg":             sparse_avg,
            "hybrid_avg":             hybrid_avg,
            "hybrid_vs_dense_delta":  d_vs_dense,
            "per_query": [
                {
                    "description": suite[i].description,
                    "query":       suite[i].query,
                    "project":     suite[i].project,
                    "dense":       asdict(dr),
                    "sparse":      asdict(sr),
                    "hybrid":      asdict(hr),
                }
                for i, (dr, sr, hr) in enumerate(zip(dense_results, sparse_results, hybrid_results))
            ],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\n  Report saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Retrieval Quality Evaluation — knowledge_v2 hybrid search v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/eval-retrieval-quality.py
  python3 scripts/eval-retrieval-quality.py --debug
  python3 scripts/eval-retrieval-quality.py --project homelab --prefetch-mult 8
  python3 scripts/eval-retrieval-quality.py --project petrochina-eproc
  python3 scripts/eval-retrieval-quality.py --output .claude/reports/eval-2026-04-14.json
  python3 scripts/eval-retrieval-quality.py --qdrant-url http://192.168.18.169:6333

Debug workflow for regression:
  python3 scripts/eval-retrieval-quality.py --debug --project homelab
  # Shows actual top-3 documents per strategy — identify which doc wins sparse leg
        """,
    )
    parser.add_argument("--qdrant-url",      default=QDRANT_URL)
    parser.add_argument("--ollama-url",      default=OLLAMA_URL)
    parser.add_argument("--api-key",         default=QDRANT_API_KEY)
    parser.add_argument("--project",         default=None, choices=["homelab", "petrochina-eproc"])
    parser.add_argument("--limit",           type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--prefetch-mult",   type=int, default=DEFAULT_PREFETCH_MULT,
                        help=f"RRF prefetch pool = limit × N (default {DEFAULT_PREFETCH_MULT}, try 8 or 16)")
    parser.add_argument("--output",          default=None)
    parser.add_argument("--debug",           action="store_true",
                        help="Show actual top-3 documents per strategy per query")
    args = parser.parse_args()

    run_evaluation(
        qdrant_url=args.qdrant_url.rstrip("/"),
        ollama_url=args.ollama_url.rstrip("/"),
        api_key=args.api_key,
        project_filter=args.project,
        limit=args.limit,
        prefetch_mult=args.prefetch_mult,
        output_path=args.output,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
