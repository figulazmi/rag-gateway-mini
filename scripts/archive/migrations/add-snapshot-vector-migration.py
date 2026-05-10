#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_COLLECTION = "knowledge_v2_keyfacts"
DENSE_SIZE = 768

PAYLOAD_INDEXES = [
    "project",
    "chunk_type",
    "status",
    "tags",
    "session_type",
    "environment",
]


def request_json(url: str, method: str, headers: dict[str, str], payload: dict | None = None, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(url, data=data, method=method)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    for key, value in headers.items():
        req.add_header(key, value)
    with urlopen(req, timeout=timeout) as response:
        raw = response.read()
        return json.loads(raw) if raw else {}


def load_api_key() -> str:
    key = os.environ.get("QDRANT_API_KEY", "").strip()
    if key:
        return key
    env_file = os.path.expanduser("~/.config/qdrant-knowledge.env")
    if not os.path.exists(env_file):
        return ""
    with open(env_file, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("QDRANT_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


def collection_url(base: str, name: str) -> str:
    return f"{base}/collections/{name}"


def collection_exists(base: str, name: str, headers: dict[str, str]) -> bool:
    try:
        request_json(collection_url(base, name), "GET", headers)
        return True
    except HTTPError as err:
        if err.code == 404:
            return False
        raise


def get_collection(base: str, name: str, headers: dict[str, str]) -> dict:
    return request_json(collection_url(base, name), "GET", headers)["result"]


def create_collection(base: str, name: str, headers: dict[str, str]) -> None:
    request_json(
        collection_url(base, name),
        "PUT",
        headers,
        {
            "vectors": {
                "dense": {"size": DENSE_SIZE, "distance": "Cosine"},
                "snapshot": {"size": DENSE_SIZE, "distance": "Cosine"},
            },
            "sparse_vectors": {
                "sparse": {"modifier": "idf"},
            },
            "on_disk_payload": True,
        },
    )
    for field in PAYLOAD_INDEXES:
        request_json(
            f"{base}/collections/{name}/index",
            "PUT",
            headers,
            {"field_name": field, "field_schema": {"type": "keyword"}},
        )


def delete_collection(base: str, name: str, headers: dict[str, str]) -> None:
    request_json(collection_url(base, name), "DELETE", headers)


def scroll_batch(
    base: str,
    collection: str,
    headers: dict[str, str],
    offset,
    include_snapshot: bool,
) -> tuple[list[dict], object | None]:
    vector_names = ["dense", "sparse"]
    if include_snapshot:
        vector_names.append("snapshot")

    payload = {
        "limit": 64,
        "with_payload": True,
        "with_vector": vector_names,
    }
    if offset is not None:
        payload["offset"] = offset
    data = request_json(f"{base}/collections/{collection}/points/scroll", "POST", headers, payload)
    result = data.get("result", {})
    return result.get("points", []), result.get("next_page_offset")


def point_vector(point: dict) -> dict:
    vector = point.get("vector", {})
    dense = vector.get("dense")
    if not dense:
        raise ValueError(f"point {point.get('id')} has no dense vector")

    out = {
        "dense": dense,
        "snapshot": vector.get("snapshot") or dense,
    }
    sparse = vector.get("sparse")
    if sparse and sparse.get("indices"):
        out["sparse"] = sparse
    return out


def copy_points(base: str, source: str, target: str, headers: dict[str, str]) -> int:
    offset = None
    copied = 0
    include_snapshot = has_snapshot(base, source, headers)
    while True:
        points, offset = scroll_batch(base, source, headers, offset, include_snapshot)
        if not points:
            break

        upsert = {
            "points": [
                {
                    "id": point["id"],
                    "vector": point_vector(point),
                    "payload": point.get("payload", {}),
                }
                for point in points
            ]
        }
        request_json(f"{base}/collections/{target}/points?wait=true", "PUT", headers, upsert, timeout=120)
        copied += len(points)
        print(f"copied {copied} points into {target}")

        if offset is None:
            break
    return copied


def verify_count(base: str, collection: str, headers: dict[str, str]) -> int:
    info = get_collection(base, collection, headers)
    return int(info["points_count"])


def has_snapshot(base: str, collection: str, headers: dict[str, str]) -> bool:
    info = get_collection(base, collection, headers)
    vectors = info["config"]["params"].get("vectors", {})
    return "dense" in vectors and "snapshot" in vectors


def main() -> int:
    parser = argparse.ArgumentParser(description="Add snapshot named vector to a Qdrant collection via staged migration")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--qdrant-url", default=DEFAULT_QDRANT_URL)
    parser.add_argument("--stage", default="knowledge_v2_keyfacts_snapshot_stage")
    parser.add_argument("--backup", default="")
    parser.add_argument("--prepare-stage", action="store_true")
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    api_key = load_api_key()
    headers = {"api-key": api_key} if api_key else {}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    backup = args.backup or f"{args.collection}_backup_{stamp}"

    if not args.prepare_stage and not args.promote:
        info = get_collection(args.qdrant_url, args.collection, headers)
        print(json.dumps(info["config"]["params"], indent=2))
        print(f"points_count={info['points_count']}")
        print(f"has_snapshot={has_snapshot(args.qdrant_url, args.collection, headers)}")
        return 0

    if args.prepare_stage:
        source_count = verify_count(args.qdrant_url, args.collection, headers)
        if collection_exists(args.qdrant_url, args.stage, headers):
            if not args.force:
                print(f"stage exists: {args.stage}; pass --force to recreate")
                return 2
            delete_collection(args.qdrant_url, args.stage, headers)
        create_collection(args.qdrant_url, args.stage, headers)
        copied = copy_points(args.qdrant_url, args.collection, args.stage, headers)
        stage_count = verify_count(args.qdrant_url, args.stage, headers)
        if copied != source_count or stage_count != source_count:
            print(f"count mismatch source={source_count} copied={copied} stage={stage_count}")
            return 1
        print(f"stage_ready={args.stage} points={stage_count}")
        return 0

    if args.promote:
        stage_count = verify_count(args.qdrant_url, args.stage, headers)
        source_count = verify_count(args.qdrant_url, args.collection, headers)
        if stage_count != source_count:
            print(f"refusing promote: stage={stage_count} source={source_count}")
            return 1

        if collection_exists(args.qdrant_url, backup, headers):
            print(f"backup already exists: {backup}")
            return 2
        create_collection(args.qdrant_url, backup, headers)
        copy_points(args.qdrant_url, args.collection, backup, headers)
        backup_count = verify_count(args.qdrant_url, backup, headers)
        if backup_count != source_count:
            print(f"backup count mismatch source={source_count} backup={backup_count}")
            return 1

        delete_collection(args.qdrant_url, args.collection, headers)
        create_collection(args.qdrant_url, args.collection, headers)
        copy_points(args.qdrant_url, args.stage, args.collection, headers)
        final_count = verify_count(args.qdrant_url, args.collection, headers)
        if final_count != stage_count or not has_snapshot(args.qdrant_url, args.collection, headers):
            print(f"promote verification failed final={final_count} stage={stage_count}")
            return 1
        print(f"promoted={args.collection} points={final_count} backup={backup}")
        return 0

    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except HTTPError as err:
        print(f"ERROR: HTTP {err.code} {err.reason}")
        print(err.read().decode("utf-8", errors="replace"))
        sys.exit(1)
    except (URLError, ValueError) as err:
        print(f"ERROR: {err}")
        sys.exit(1)
