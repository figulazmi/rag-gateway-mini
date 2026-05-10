#!/usr/bin/env python3
"""P2-3 Existing Chunk Provenance Backfill.

Idempotently adds provenance fields to legacy Qdrant points that lack them.
Uses Qdrant set_payload with is_empty filters — safe to re-run at any time.

Usage:
    # Preflight: show counts and sample missing points
    python3 scripts/backfill-provenance.py --collection knowledge_v2_keyfacts --dry-run

    # Apply backfill
    python3 scripts/backfill-provenance.py --collection knowledge_v2_keyfacts --apply

    # Post-verify: confirm nothing is missing
    python3 scripts/backfill-provenance.py --collection knowledge_v2_keyfacts --dry-run

Run on VM B1 after git pull from /opt/homelab/ai-stack/rag-gateway-mini.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_COLLECTION = "knowledge_v2_keyfacts"

BACKFILL_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

BACKFILL_PAYLOAD = {
    "ingested_by": "backfill-p2-3",
    "push_method": "provenance-backfill-script",
    "backfill_id": "p2-3-existing-chunk-provenance-2026-05-07",
}

PROVENANCE_FIELDS = list(BACKFILL_PAYLOAD.keys()) + ["backfilled_at"]

SAMPLE_PAYLOAD_FIELDS = ["doc_id", "topic", "project", "chunk_type", "session_type", "environment"]


def request_json(
    url: str,
    method: str,
    headers: dict[str, str],
    payload: dict | None = None,
    timeout: int = 30,
) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(url, data=data, method=method)
    if data is not None:
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


def count_total(qdrant_url: str, collection: str, headers: dict[str, str]) -> int:
    data = request_json(
        f"{qdrant_url}/collections/{collection}/points/count",
        "POST",
        headers,
        {"exact": True},
    )
    return data["result"]["count"]


def count_missing(
    qdrant_url: str, collection: str, headers: dict[str, str], field: str
) -> int:
    data = request_json(
        f"{qdrant_url}/collections/{collection}/points/count",
        "POST",
        headers,
        {"exact": True, "filter": {"must": [{"is_empty": {"key": field}}]}},
    )
    return data["result"]["count"]


def sample_missing(
    qdrant_url: str,
    collection: str,
    headers: dict[str, str],
    field: str,
    limit: int = 3,
) -> list[dict]:
    data = request_json(
        f"{qdrant_url}/collections/{collection}/points/scroll",
        "POST",
        headers,
        {
            "limit": limit,
            "with_payload": SAMPLE_PAYLOAD_FIELDS,
            "with_vector": False,
            "filter": {"must": [{"is_empty": {"key": field}}]},
        },
    )
    return data.get("result", {}).get("points", [])


def apply_field(
    qdrant_url: str,
    collection: str,
    headers: dict[str, str],
    field: str,
    value: object,
) -> None:
    request_json(
        f"{qdrant_url}/collections/{collection}/points/payload?wait=true",
        "POST",
        headers,
        {
            "payload": {field: value},
            "filter": {"must": [{"is_empty": {"key": field}}]},
        },
        timeout=60,
    )


def run_dry(qdrant_url: str, collection: str, headers: dict[str, str]) -> int:
    print(f"DRY-RUN — collection={collection}")
    total = count_total(qdrant_url, collection, headers)
    print(f"  total_points={total}")

    all_ok = True
    for field in PROVENANCE_FIELDS:
        missing = count_missing(qdrant_url, collection, headers, field)
        flag = "MISSING" if missing > 0 else "ok"
        print(f"  {flag} field={field} missing={missing}")
        if missing > 0:
            all_ok = False
            samples = sample_missing(qdrant_url, collection, headers, field, limit=3)
            for point in samples:
                payload = point.get("payload", {})
                doc_id = payload.get("doc_id", "?")
                topic = payload.get("topic", "?")
                project = payload.get("project", "?")
                print(f"    sample id={point['id']} doc_id={doc_id} topic={topic} project={project}")

    if all_ok:
        print("  result=all_provenance_fields_present — nothing to backfill")
        return 0
    return 1


def run_apply(qdrant_url: str, collection: str, headers: dict[str, str]) -> int:
    print(f"APPLY — collection={collection}")
    total = count_total(qdrant_url, collection, headers)
    print(f"  total_points={total}")

    # Apply fixed fields
    for field, value in BACKFILL_PAYLOAD.items():
        before = count_missing(qdrant_url, collection, headers, field)
        if before == 0:
            print(f"  SKIP field={field} — already present on all points")
            continue
        print(f"  applying field={field} to {before} points ...")
        apply_field(qdrant_url, collection, headers, field, value)
        after = count_missing(qdrant_url, collection, headers, field)
        print(f"  applied field={field} before={before} after={after}")

    # Apply backfilled_at separately because value uses current timestamp
    field = "backfilled_at"
    before = count_missing(qdrant_url, collection, headers, field)
    if before == 0:
        print(f"  SKIP field={field} — already present on all points")
    else:
        print(f"  applying field={field} to {before} points ...")
        apply_field(qdrant_url, collection, headers, field, BACKFILL_TIMESTAMP)
        after = count_missing(qdrant_url, collection, headers, field)
        print(f"  applied field={field} before={before} after={after}")

    # Post-verify
    failures = []
    for field in PROVENANCE_FIELDS:
        remaining = count_missing(qdrant_url, collection, headers, field)
        if remaining > 0:
            failures.append(f"{field}={remaining}")
    if failures:
        print(f"  FAIL post-verify still missing: {', '.join(failures)}")
        return 1
    print("  result=all_provenance_fields_present")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="P2-3 idempotent provenance backfill for Qdrant")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--qdrant-url", default=DEFAULT_QDRANT_URL)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True, help="Preflight only — no writes (default)")
    mode.add_argument("--apply", action="store_true", help="Write backfill payload to Qdrant")
    args = parser.parse_args()

    api_key = load_api_key()
    headers = {"api-key": api_key} if api_key else {}

    try:
        if args.apply:
            return run_apply(args.qdrant_url, args.collection, headers)
        return run_dry(args.qdrant_url, args.collection, headers)
    except HTTPError as err:
        print(f"ERROR: HTTP {err.code} {err.reason}")
        print(err.read().decode("utf-8", errors="replace"))
        return 1
    except URLError as err:
        print(f"ERROR: Qdrant unreachable ({err})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
