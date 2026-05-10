#!/usr/bin/env python3
"""Build knowledge_v2_keyfacts using Qdrant REST only, without touching knowledge_v2."""

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any


DENSE_VECTOR_SIZE = 768
INDEX_FIELDS = ["project", "chunk_type", "status", "tags", "session_type", "environment"]


def request_json(method: str, url: str, api_key: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["api-key"] = api_key
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} {method} {url}: {detail}") from exc


def collection_exists(qdrant_url: str, api_key: str, collection: str) -> bool:
    try:
        request_json("GET", f"{qdrant_url}/collections/{collection}", api_key)
        return True
    except SystemExit as exc:
        if "HTTP 404" in str(exc):
            return False
        raise


def djb2_sparse(text: str) -> dict[str, list[float] | list[int]]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    tf: dict[int, int] = {}
    for token in tokens:
        h = 5381
        for ch in token:
            h = (((h << 5) + h) + ord(ch)) & 0x7FFFFFFF
        tf[h] = tf.get(h, 0) + 1
    return {"indices": list(tf.keys()), "values": [float(v) for v in tf.values()]}


def extract_key_facts(content: str) -> str:
    facts: list[str] = []
    in_key_facts = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("### "):
            in_key_facts = stripped.lower().strip("# ") == "key facts"
            continue
        if in_key_facts and stripped.startswith(("- ", "* ")):
            facts.append(stripped[2:].strip())
    return " ".join(facts)


def extract_dense(vector: Any) -> list[float] | None:
    if isinstance(vector, dict):
        dense = vector.get("dense")
        if isinstance(dense, list):
            return dense
        for value in vector.values():
            if isinstance(value, list):
                return value
    if isinstance(vector, list):
        return vector
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qdrant-url", default="http://192.168.18.199:6333")
    parser.add_argument("--api-key", default=os.environ.get("QDRANT_API_KEY", ""))
    parser.add_argument("--source", default="knowledge_v2")
    parser.add_argument("--target", default="knowledge_v2_keyfacts")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    qdrant_url = args.qdrant_url.rstrip("/")

    source_info = request_json("GET", f"{qdrant_url}/collections/{args.source}", args.api_key)
    source_count = source_info["result"]["points_count"]

    if collection_exists(qdrant_url, args.api_key, args.target):
        if not args.force:
            raise SystemExit(f"Target collection exists: {args.target}. Re-run with --force.")
        request_json("DELETE", f"{qdrant_url}/collections/{args.target}", args.api_key)

    request_json("PUT", f"{qdrant_url}/collections/{args.target}", args.api_key, {
        "vectors": {"dense": {"size": DENSE_VECTOR_SIZE, "distance": "Cosine"}},
        "sparse_vectors": {"sparse": {"modifier": "idf"}},
    })

    for field in INDEX_FIELDS:
        request_json("PUT", f"{qdrant_url}/collections/{args.target}/index", args.api_key, {
            "field_name": field,
            "field_schema": "keyword",
        })

    offset = None
    migrated = 0
    keyfacts_points = 0
    while True:
        body: dict[str, Any] = {
            "limit": args.batch_size,
            "with_payload": True,
            "with_vector": True,
        }
        if offset is not None:
            body["offset"] = offset
        result = request_json("POST", f"{qdrant_url}/collections/{args.source}/points/scroll", args.api_key, body)["result"]
        points = result.get("points", [])
        offset = result.get("next_page_offset")
        if not points:
            break

        upserts = []
        for point in points:
            payload = point.get("payload") or {}
            dense = extract_dense(point.get("vector"))
            if dense is None:
                continue
            topic = payload.get("topic", "") or ""
            content = payload.get("content", "") or ""
            key_facts = extract_key_facts(content)
            if key_facts:
                keyfacts_points += 1
            sparse_text = f"{topic} {key_facts}".strip()
            upserts.append({
                "id": point["id"],
                "vector": {"dense": dense, "sparse": djb2_sparse(sparse_text)},
                "payload": payload,
            })

        if upserts:
            request_json("PUT", f"{qdrant_url}/collections/{args.target}/points", args.api_key, {"points": upserts})
            migrated += len(upserts)
            print(f"Migrated {migrated} points...")

        if offset is None:
            break
        time.sleep(0.2)

    target_info = request_json("GET", f"{qdrant_url}/collections/{args.target}", args.api_key)
    target_count = target_info["result"]["points_count"]
    print(f"Source points: {source_count}")
    print(f"Target points: {target_count}")
    print(f"Points with Key Facts sparse text: {keyfacts_points}")
    if source_count != target_count:
        raise SystemExit("Point count mismatch")


if __name__ == "__main__":
    main()
