#!/usr/bin/env python3
"""
Retrieval Quality Evaluation Framework — knowledge_v2 Hybrid Search
Author  : Figur Ulul Azmi
Version : 1.0.0

Evaluates two retrieval strategies against knowledge_v2 on VM B1:
  - Dense-only  : nomic-embed-text (768-dim, COSINE), using "dense"
  - Hybrid-RRF  : dense + sparse djb2 BM25, fused with Qdrant RRF

Metrics:
  Hit@1 / Hit@3 / Hit@5   — Did a relevant result appear in top K?
  MRR                      — Mean Reciprocal Rank of first relevant result
  NDCG@5                   — Normalized Discounted Cumulative Gain at 5
  Score distribution        — min / max / avg / p50 / p95 per query
  Latency (ms)             — embed + search time per query

Usage:
  python3 scripts/eval-retrieval-quality.py
  python3 scripts/eval-retrieval-quality.py --project homelab
  python3 scripts/eval-retrieval-quality.py --limit 5 --output reports/eval.json
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

QDRANT_URL    = "http://localhost:6333"
QDRANT_API_KEY = "QDRANT_API_KEY_REDACTED"
OLLAMA_URL    = "http://localhost:11434"
COLLECTION    = "knowledge_v2"
DENSE_VECTOR  = "dense"    # REQUIRED: knowledge_v2 has no default/unnamed vector
SPARSE_VECTOR = "sparse"
EMBED_MODEL   = "nomic-embed-text"
DEFAULT_LIMIT = 5
PREFETCH_MULT = 4           # prefetch = limit * PREFETCH_MULT per leg


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
    TestCase(
        query="MCP server upgrade knowledge_v2 hybrid search djb2 RRF fusion",
        project="homelab",
        gold_keywords=["djb2", "hybrid", "knowledge_v2", "rrf", "sparse"],
        gold_topics=["MCP Server", "knowledge_v2", "Hybrid"],
        description="MCP server v2.0 migration to hybrid search",
    ),
    TestCase(
        query="qdrant collection named vector dense sparse migration script",
        project="homelab",
        gold_keywords=["named", "dense", "sparse", "migration", "collection"],
        gold_topics=["migration", "hybrid", "knowledge_v2"],
        description="knowledge_v2 collection schema migration",
    ),
    TestCase(
        query="docker compose VM B1 deployment rag gateway service update",
        project="homelab",
        gold_keywords=["docker", "compose", "deploy", "vm", "gateway"],
        gold_topics=["deploy", "docker", "VM B1"],
        description="VM B1 docker deployment workflow",
    ),
    TestCase(
        query="RAG gateway ASP.NET Core hybrid BM25 prefetch RRF score threshold",
        project="homelab",
        gold_keywords=["hybrid", "bm25", "prefetch", "rrf", "threshold"],
        gold_topics=["Hybrid Search Gateway", "RAG Gateway"],
        description="RAG Gateway hybrid search refactor",
    ),
    TestCase(
        query="push to qdrant script ingest knowledge chunks pipeline n8n",
        project="homelab",
        gold_keywords=["push", "qdrant", "ingest", "knowledge"],
        gold_topics=["push", "ingest", "pipeline"],
        description="Knowledge ingestion pipeline",
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


# ─── SPARSE VECTOR — djb2 ──────────────────────────────────────────────────
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


# ─── HTTP HELPERS ─────────────────────────────────────────────────────────

def _post(url: str, body: dict, qdrant_url: str, api_key: str) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "api-key": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


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


# ─── SEARCH STRATEGIES ─────────────────────────────────────────────────────

def search_dense_only(
    dense_vector: list[float],
    project: str,
    limit: int,
    qdrant_url: str,
    api_key: str,
) -> list[dict]:
    """
    Dense-only retrieval using /points/query with a single dense prefetch leg.
    MUST specify using="dense" — knowledge_v2 has no default vector.
    """
    body = {
        "prefetch": [
            {
                "query": dense_vector,
                "using": DENSE_VECTOR,           # REQUIRED: named vector
                "limit": limit * PREFETCH_MULT,
                "filter": {"must": [{"key": "project", "match": {"value": project}}]},
            }
        ],
        "query": {"fusion": "rrf"},
        "limit": limit,
        "with_payload": True,
    }
    result = _post(
        f"{qdrant_url}/collections/{COLLECTION}/points/query",
        body, qdrant_url, api_key,
    )
    return result.get("result", {}).get("points", [])


def search_hybrid(
    dense_vector: list[float],
    sparse_vector: dict,
    project: str,
    limit: int,
    qdrant_url: str,
    api_key: str,
) -> list[dict]:
    """
    Hybrid retrieval: dense + sparse djb2, fused server-side with RRF.
    MUST specify using="dense" / using="sparse" per leg.
    """
    body = {
        "prefetch": [
            {
                "query": dense_vector,
                "using": DENSE_VECTOR,           # REQUIRED: named vector
                "limit": limit * PREFETCH_MULT,
                "filter": {"must": [{"key": "project", "match": {"value": project}}]},
            },
            {
                "query": sparse_vector,
                "using": SPARSE_VECTOR,          # REQUIRED: named vector
                "limit": limit * PREFETCH_MULT,
                "filter": {"must": [{"key": "project", "match": {"value": project}}]},
            },
        ],
        "query": {"fusion": "rrf"},
        "limit": limit,
        "with_payload": True,
    }
    result = _post(
        f"{qdrant_url}/collections/{COLLECTION}/points/query",
        body, qdrant_url, api_key,
    )
    return result.get("result", {}).get("points", [])


# ─── RELEVANCE SCORING ────────────────────────────────────────────────────

def relevance_score(point: dict, tc: TestCase) -> float:
    """
    Binary relevance: 1.0 if ANY gold keyword found in content,
    or ANY gold topic substring found in payload["topic"].
    Returns value between 0.0 and 1.0.
    """
    payload = point.get("payload", {})
    content = (payload.get("content", "") or "").lower()
    topic   = (payload.get("topic", "") or "").lower()

    keyword_hits = sum(1 for kw in tc.gold_keywords if kw.lower() in content)
    topic_hits   = sum(1 for t in tc.gold_topics if t.lower() in topic)

    total_signals = len(tc.gold_keywords) + len(tc.gold_topics)
    if total_signals == 0:
        return 0.0
    return min(1.0, (keyword_hits + topic_hits) / total_signals)


def is_relevant(point: dict, tc: TestCase, threshold: float = 0.2) -> bool:
    return relevance_score(point, tc) >= threshold


# ─── METRICS ─────────────────────────────────────────────────────────────

def hit_at_k(points: list[dict], tc: TestCase, k: int) -> float:
    for p in points[:k]:
        if is_relevant(p, tc):
            return 1.0
    return 0.0


def reciprocal_rank(points: list[dict], tc: TestCase) -> float:
    for i, p in enumerate(points, start=1):
        if is_relevant(p, tc):
            return 1.0 / i
    return 0.0


def ndcg_at_k(points: list[dict], tc: TestCase, k: int = 5) -> float:
    rels = [relevance_score(p, tc) for p in points[:k]]
    dcg  = sum(r / math.log2(i + 2) for i, r in enumerate(rels))
    ideal_rels = sorted(rels, reverse=True)
    idcg = sum(r / math.log2(i + 2) for i, r in enumerate(ideal_rels))
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


# ─── RESULT DATACLASS ─────────────────────────────────────────────────────

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


@dataclass
class EvalReport:
    timestamp: str
    collection: str
    limit: int
    total_queries: int
    dense_avg: dict
    hybrid_avg: dict
    hybrid_vs_dense_delta: dict
    per_query: list


# ─── AGGREGATION ──────────────────────────────────────────────────────────

def aggregate(results: list[QueryResult]) -> dict:
    if not results:
        return {}
    n = len(results)
    return {
        "hit@1":       round(sum(r.hit_at_1 for r in results) / n, 4),
        "hit@3":       round(sum(r.hit_at_3 for r in results) / n, 4),
        "hit@5":       round(sum(r.hit_at_5 for r in results) / n, 4),
        "mrr":         round(sum(r.mrr for r in results) / n, 4),
        "ndcg@5":      round(sum(r.ndcg5 for r in results) / n, 4),
        "avg_latency_ms": round(sum(r.latency_ms for r in results) / n, 1),
    }


def delta(hybrid: dict, dense: dict) -> dict:
    keys = ["hit@1", "hit@3", "hit@5", "mrr", "ndcg@5"]
    return {
        k: round(hybrid.get(k, 0) - dense.get(k, 0), 4)
        for k in keys
    }


# ─── PRINTING ─────────────────────────────────────────────────────────────

def print_header():
    print()
    print("=" * 72)
    print("  Retrieval Quality Evaluation — knowledge_v2 Hybrid Search")
    print(f"  Collection : {COLLECTION}  |  Vectors: {DENSE_VECTOR} (768-dim) + {SPARSE_VECTOR} (djb2)")
    print(f"  Timestamp  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)


def print_query_result(dense: QueryResult, hybrid: QueryResult, idx: int):
    print(f"\n[{idx}] {dense.description}")
    print(f"    Query   : {dense.query[:70]}")
    print(f"    Project : {dense.project}")
    print(f"    {'Metric':<12} {'Dense-Only':>12} {'Hybrid-RRF':>12} {'Delta':>10}")
    print(f"    {'-'*46}")
    for label, d_val, h_val in [
        ("Hit@1",  dense.hit_at_1, hybrid.hit_at_1),
        ("Hit@3",  dense.hit_at_3, hybrid.hit_at_3),
        ("Hit@5",  dense.hit_at_5, hybrid.hit_at_5),
        ("MRR",    dense.mrr,      hybrid.mrr),
        ("NDCG@5", dense.ndcg5,    hybrid.ndcg5),
    ]:
        delta_val = h_val - d_val
        sign = "+" if delta_val > 0 else ""
        print(f"    {label:<12} {d_val:>12.4f} {h_val:>12.4f} {sign+str(round(delta_val,4)):>10}")
    print(f"    {'Latency(ms)':<12} {dense.latency_ms:>12.1f} {hybrid.latency_ms:>12.1f}")
    print(f"    Score dist (hybrid): min={hybrid.score_dist['min']} "
          f"max={hybrid.score_dist['max']} avg={hybrid.score_dist['avg']}")


def print_summary(dense_avg: dict, hybrid_avg: dict, d: dict):
    print()
    print("=" * 72)
    print("  AGGREGATE SUMMARY")
    print("=" * 72)
    print(f"  {'Metric':<14} {'Dense-Only':>12} {'Hybrid-RRF':>12} {'Delta':>10}")
    print(f"  {'-'*48}")
    for k in ["hit@1", "hit@3", "hit@5", "mrr", "ndcg@5"]:
        dv = dense_avg.get(k, 0)
        hv = hybrid_avg.get(k, 0)
        sign = "+" if d[k] > 0 else ""
        verdict = " ✓" if d[k] > 0 else (" =" if d[k] == 0 else " ✗")
        print(f"  {k:<14} {dv:>12.4f} {hv:>12.4f} {sign+str(d[k]):>10}{verdict}")
    print(f"  {'avg latency':<14} {dense_avg['avg_latency_ms']:>11.1f}ms "
          f"{hybrid_avg['avg_latency_ms']:>11.1f}ms")
    print()
    improvement = sum(1 for v in d.values() if v > 0)
    print(f"  Hybrid improved {improvement}/{len(d)} metrics vs dense-only.")
    print("=" * 72)
    print()


# ─── MAIN ─────────────────────────────────────────────────────────────────

def run_evaluation(
    qdrant_url: str,
    ollama_url: str,
    api_key: str,
    project_filter: Optional[str],
    limit: int,
    output_path: Optional[str],
):
    suite = [tc for tc in TEST_SUITE if project_filter is None or tc.project == project_filter]
    if not suite:
        print(f"No test cases for project '{project_filter}'. Available: {list({tc.project for tc in TEST_SUITE})}")
        return

    print_header()
    print(f"\n  Running {len(suite)} queries  |  limit={limit}")
    if project_filter:
        print(f"  Project filter: {project_filter}")
    print()

    dense_results:  list[QueryResult] = []
    hybrid_results: list[QueryResult] = []

    for idx, tc in enumerate(suite, start=1):
        print(f"  [{idx}/{len(suite)}] Embedding: {tc.query[:60]}...")

        # Generate vectors
        t0 = time.perf_counter()
        dense_vec  = embed(tc.query, ollama_url)
        sparse_vec = djb2_sparse(tc.query)
        embed_ms   = (time.perf_counter() - t0) * 1000

        # Dense-only search
        t0 = time.perf_counter()
        dense_points = search_dense_only(dense_vec, tc.project, limit, qdrant_url, api_key)
        dense_search_ms = (time.perf_counter() - t0) * 1000

        # Hybrid search
        t0 = time.perf_counter()
        hybrid_points = search_hybrid(dense_vec, sparse_vec, tc.project, limit, qdrant_url, api_key)
        hybrid_search_ms = (time.perf_counter() - t0) * 1000

        # Build results
        def build_result(points: list[dict], strategy: str, search_ms: float) -> QueryResult:
            return QueryResult(
                query=tc.query,
                project=tc.project,
                description=tc.description,
                strategy=strategy,
                hit_at_1=hit_at_k(points, tc, 1),
                hit_at_3=hit_at_k(points, tc, 3),
                hit_at_5=hit_at_k(points, tc, 5),
                mrr=reciprocal_rank(points, tc),
                ndcg5=ndcg_at_k(points, tc, 5),
                score_dist=score_distribution(points),
                latency_ms=round(embed_ms + search_ms, 1),
                raw_scores=[p.get("score", 0) for p in points],
            )

        dr = build_result(dense_points, "dense", dense_search_ms)
        hr = build_result(hybrid_points, "hybrid-rrf", hybrid_search_ms)

        dense_results.append(dr)
        hybrid_results.append(hr)

        print_query_result(dr, hr, idx)

    # Aggregate
    dense_avg  = aggregate(dense_results)
    hybrid_avg = aggregate(hybrid_results)
    d          = delta(hybrid_avg, dense_avg)

    print_summary(dense_avg, hybrid_avg, d)

    # Save JSON report
    if output_path:
        import os
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        report = {
            "timestamp":            datetime.now().isoformat(),
            "collection":           COLLECTION,
            "dense_vector_name":    DENSE_VECTOR,
            "sparse_vector_name":   SPARSE_VECTOR,
            "limit":                limit,
            "project_filter":       project_filter,
            "total_queries":        len(suite),
            "dense_avg":            dense_avg,
            "hybrid_avg":           hybrid_avg,
            "hybrid_vs_dense_delta": d,
            "per_query": [
                {"dense": asdict(dr), "hybrid": asdict(hr)}
                for dr, hr in zip(dense_results, hybrid_results)
            ],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"  Report saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Retrieval Quality Evaluation — knowledge_v2 hybrid search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/eval-retrieval-quality.py
  python3 scripts/eval-retrieval-quality.py --project homelab
  python3 scripts/eval-retrieval-quality.py --project petrochina-eproc --limit 3
  python3 scripts/eval-retrieval-quality.py --output .claude/reports/eval-2026-04-14.json
  python3 scripts/eval-retrieval-quality.py --qdrant-url http://192.168.18.169:6333
        """,
    )
    parser.add_argument(
        "--qdrant-url", default=QDRANT_URL,
        help=f"Qdrant base URL (default: {QDRANT_URL})",
    )
    parser.add_argument(
        "--ollama-url", default=OLLAMA_URL,
        help=f"Ollama base URL (default: {OLLAMA_URL})",
    )
    parser.add_argument(
        "--api-key", default=QDRANT_API_KEY,
        help="Qdrant API key",
    )
    parser.add_argument(
        "--project", default=None, choices=["homelab", "petrochina-eproc"],
        help="Filter test cases by project (default: all)",
    )
    parser.add_argument(
        "--limit", type=int, default=DEFAULT_LIMIT,
        help=f"Result limit per query (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--output", default=None,
        help="Save JSON report to file path",
    )
    args = parser.parse_args()

    run_evaluation(
        qdrant_url=args.qdrant_url.rstrip("/"),
        ollama_url=args.ollama_url.rstrip("/"),
        api_key=args.api_key,
        project_filter=args.project,
        limit=args.limit,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
