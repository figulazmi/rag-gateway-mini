#!/usr/bin/env python3
import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import Request, urlopen

DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_COLLECTION = "knowledge_v2_keyfacts"
DEFAULT_THRESHOLD = 0.99
DEFAULT_AUDIT_LOG = os.path.expanduser("~/.rag_audit.log")


def post_json(url: str, payload: dict, headers: dict[str, str], timeout: int = 30) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    for key, value in headers.items():
        req.add_header(key, value)
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read())


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


def parse_point_id(raw: str):
    raw = raw.strip()
    if raw.isdigit():
        return int(raw)
    return raw


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def append_audit_line(path: str, line: str) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def scroll_points(qdrant_url: str, collection: str, headers: dict[str, str], limit: int, point_id=None) -> list[dict]:
    payload: dict = {
        "limit": limit,
        "with_payload": True,
        "with_vector": ["dense", "snapshot"],
    }
    if point_id is not None:
        payload["filter"] = {"must": [{"has_id": [point_id]}]}

    data = post_json(f"{qdrant_url}/collections/{collection}/points/scroll", payload, headers)
    return data.get("result", {}).get("points", [])


def check_point(point: dict, threshold: float, audit_log: str) -> bool:
    point_id = point.get("id")
    vectors = point.get("vector", {})
    dense = vectors.get("dense")
    snapshot = vectors.get("snapshot")
    if not dense or not snapshot:
        line = f"{timestamp()} TAMPER point_id={point_id} reason=missing dense_or_snapshot_vector"
        print(line)
        append_audit_line(audit_log, line)
        return True

    score = cosine(dense, snapshot)
    if score >= threshold:
        print(f"OK point_id={point_id} cos={score:.6f}")
        return False

    line = f"{timestamp()} TAMPER point_id={point_id} cos_dense_snapshot={score:.6f} threshold={threshold:.2f}"
    print(line)
    append_audit_line(audit_log, line)
    return True


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare Qdrant dense vector against immutable snapshot vector")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--point-id", help="Specific Qdrant point id")
    group.add_argument("--sample", type=int, help="Number of points to sample from collection")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--qdrant-url", default=DEFAULT_QDRANT_URL)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--audit-log", default=DEFAULT_AUDIT_LOG)
    args = parser.parse_args()

    api_key = load_api_key()
    headers = {"api-key": api_key} if api_key else {}
    point_id = parse_point_id(args.point_id) if args.point_id else None
    limit = args.sample or 1

    try:
        points = scroll_points(args.qdrant_url, args.collection, headers, limit, point_id)
    except URLError as err:
        print(f"SKIP: Qdrant unreachable ({err})")
        return 2

    if not points:
        print("SKIP: no points found")
        return 2

    tampered = False
    for point in points:
        tampered = check_point(point, args.threshold, args.audit_log) or tampered

    return 1 if tampered else 0


if __name__ == "__main__":
    sys.exit(main())
