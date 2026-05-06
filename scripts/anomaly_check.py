#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import Request, urlopen

DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_COLLECTION = "knowledge_v2_keyfacts"
DEFAULT_THRESHOLD = 0.97
DEFAULT_LIMIT = 6
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


def normalize_type(payload: dict) -> str:
    value = payload.get("chunk_type") or payload.get("session_type") or "unknown"
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return str(value)


def normalize_project(payload: dict) -> str:
    value = payload.get("project") or "unknown"
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return str(value)


def append_audit_line(audit_log: str, line: str) -> None:
    with open(audit_log, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def load_point(qdrant_url: str, collection: str, point_id, headers: dict[str, str]) -> dict | None:
    data = post_json(
        f"{qdrant_url}/collections/{collection}/points/scroll",
        {
            "filter": {"must": [{"has_id": [point_id]}]},
            "limit": 1,
            "with_payload": True,
            "with_vector": ["dense"],
        },
        headers,
    )
    points = data.get("result", {}).get("points", [])
    if not points:
        return None
    return points[0]


def query_neighbors(
    qdrant_url: str,
    collection: str,
    dense_vector: list[float],
    headers: dict[str, str],
    limit: int,
) -> list[dict]:
    data = post_json(
        f"{qdrant_url}/collections/{collection}/points/query",
        {
            "prefetch": [
                {
                    "query": dense_vector,
                    "using": "dense",
                    "limit": limit,
                }
            ],
            "query": {"fusion": "rrf"},
            "limit": limit,
            "with_payload": True,
            "with_vector": False,
        },
        headers,
    )
    return data.get("result", {}).get("points", [])


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect post-upsert dense-neighbor metadata anomalies")
    parser.add_argument("--point-id", required=True, help="Qdrant point id (numeric or string)")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--qdrant-url", default=DEFAULT_QDRANT_URL)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--audit-log", default=DEFAULT_AUDIT_LOG)
    args = parser.parse_args()

    point_id = parse_point_id(args.point_id)
    api_key = load_api_key()
    headers = {"api-key": api_key} if api_key else {}

    try:
        point = load_point(args.qdrant_url, args.collection, point_id, headers)
    except URLError as err:
        print(f"SKIP: Qdrant unreachable ({err})")
        return 2

    if point is None:
        print(f"SKIP: point not found ({args.point_id})")
        return 2

    vector = point.get("vector", {}).get("dense")
    if not vector:
        print(f"SKIP: dense vector missing ({args.point_id})")
        return 2

    base_payload = point.get("payload", {})
    base_project = normalize_project(base_payload)
    base_type = normalize_type(base_payload)

    try:
        neighbors = query_neighbors(args.qdrant_url, args.collection, vector, headers, args.limit)
    except URLError as err:
        print(f"SKIP: neighbor query failed ({err})")
        return 2

    anomalies: list[str] = []
    for item in neighbors:
        neighbor_id = item.get("id")
        if str(neighbor_id) == str(point_id):
            continue

        score = float(item.get("score", 0.0))
        if score <= args.threshold:
            continue

        payload = item.get("payload", {})
        neighbor_project = normalize_project(payload)
        neighbor_type = normalize_type(payload)

        reasons: list[str] = []
        if base_project != neighbor_project:
            reasons.append(f"project {base_project} vs {neighbor_project}")
        if base_type != neighbor_type:
            reasons.append(f"type {base_type} vs {neighbor_type}")

        if not reasons:
            continue

        reason_text = "; ".join(reasons)
        line = (
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} "
            f"ANOMALY point_id={point_id} neighbor_id={neighbor_id} score={score:.4f} {reason_text}"
        )
        anomalies.append(line)

    if not anomalies:
        print(f"OK: no anomalies for point_id={point_id} threshold={args.threshold:.2f}")
        return 0

    for line in anomalies:
        print(line)
        append_audit_line(args.audit_log, line)

    return 1


if __name__ == "__main__":
    sys.exit(main())
