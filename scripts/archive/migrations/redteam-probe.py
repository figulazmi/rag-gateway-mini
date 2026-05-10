#!/usr/bin/env python3
"""P2-4 Automated Red Team Probe.

Inserts a temporary synthetic probe into Qdrant, queries the live rag-gateway,
alerts if the probe appears in top-k results, and deletes the probe before exit.
"""
import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_COLLECTION = "knowledge_v2_keyfacts"
DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_GATEWAY_URL = "http://localhost:5200"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_PROJECT = "homelab"
DEFAULT_TOP_K = 5
DEFAULT_ALERT_EMAIL = "azmi.codes@gmail.com"
PROBE_ID_SALT = "p2-4-redteam-probe"


def request_json(
    url: str,
    method: str,
    headers: dict[str, str] | None = None,
    payload: dict | None = None,
    timeout: int = 30,
) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
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


def current_year_week() -> str:
    now = datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()
    return f"{year}{week:02d}"


def point_id_for(doc_id: str) -> int:
    digest = hashlib.sha256(f"{PROBE_ID_SALT}:{doc_id}".encode("utf-8")).hexdigest()
    return int(digest[:15], 16)


def build_probe(project: str, year_week: str) -> tuple[int, str, str, str]:
    topic = f"redteam-probe-{year_week}"
    doc_id = f"{topic}-synthetic-poison-check"
    point_id = point_id_for(doc_id)
    content = (
        f"Synthetic red-team probe {topic}. This temporary chunk is inserted only to validate "
        "that RAG poisoning defenses and retrieval thresholds do not surface controlled probe content "
        "in normal gateway search results. If this chunk appears in top results, alert the operator."
    )
    return point_id, doc_id, topic, content


def generate_embedding(ollama_url: str, model: str, text: str) -> list[float]:
    data = request_json(
        f"{ollama_url}/api/embeddings",
        "POST",
        payload={"model": model, "prompt": text},
        timeout=60,
    )
    embedding = data.get("embedding", [])
    if not embedding:
        raise RuntimeError("Ollama returned empty embedding")
    return embedding


def upsert_probe(
    qdrant_url: str,
    collection: str,
    headers: dict[str, str],
    point_id: int,
    doc_id: str,
    topic: str,
    project: str,
    content: str,
    embedding: list[float],
) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "id": doc_id,
        "doc_id": doc_id,
        "topic": topic,
        "project": project,
        "chunk_type": "reference",
        "status": "implemented",
        "tags": ["homelab", "redteam", "probe", "security"],
        "content": content,
        "chunk_source": "redteam-probe.py",
        "session_type": "redteam-probe",
        "environment": "vm-b1",
        "ingested_by": "redteam-probe.py",
        "push_method": "redteam-probe.py",
        "captured_at": now,
    }
    body = {
        "points": [
            {
                "id": point_id,
                "vector": {
                    "dense": embedding,
                    "snapshot": embedding,
                },
                "payload": payload,
            }
        ]
    }
    request_json(
        f"{qdrant_url}/collections/{collection}/points?wait=true",
        "PUT",
        headers,
        body,
        timeout=60,
    )


def delete_probe(qdrant_url: str, collection: str, headers: dict[str, str], point_id: int) -> None:
    request_json(
        f"{qdrant_url}/collections/{collection}/points/delete?wait=true",
        "POST",
        headers,
        {"points": [point_id]},
        timeout=60,
    )


def query_gateway(gateway_url: str, query: str, project: str) -> dict:
    return request_json(
        f"{gateway_url.rstrip('/')}/rag/search",
        "POST",
        payload={
            "query": query,
            "project": project,
            "knowledge_expansion": True,
        },
        timeout=60,
    )


def find_probe_rank(response: dict, doc_id: str, topic: str, top_k: int) -> tuple[int | None, float | None, list[str]]:
    summaries: list[str] = []
    for index, item in enumerate(response.get("results") or [], start=1):
        metadata = item.get("metadata") or {}
        item_doc = str(metadata.get("doc_id") or metadata.get("id") or "")
        item_topic = str(metadata.get("topic") or "")
        score = float(item.get("score") or 0.0)
        summaries.append(f"{index}. score={score:.4f} doc_id={item_doc} topic={item_topic}")
        if index <= top_k and (item_doc == doc_id or item_topic == topic):
            return index, score, summaries
    return None, None, summaries


def send_alert(email: str, subject: str, body: str) -> None:
    proc = subprocess.run(
        ["mail", "-s", subject, email],
        input=body,
        text=True,
        check=False,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"mail failed rc={proc.returncode}: {proc.stderr.strip()}")


def build_alert_body(
    collection: str,
    doc_id: str,
    topic: str,
    query: str,
    rank: int,
    score: float,
    summaries: list[str],
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return "\n".join(
        [
            "P2-4 redteam probe surfaced in RAG search results.",
            f"timestamp={now}",
            f"hostname={socket.gethostname()}",
            f"collection={collection}",
            f"doc_id={doc_id}",
            f"topic={topic}",
            f"query={query}",
            f"rank={rank}",
            f"score={score:.4f}",
            "top_results:",
            *summaries,
        ]
    )


def confirm_deleted(qdrant_url: str, collection: str, headers: dict[str, str], point_id: int) -> bool:
    data = request_json(
        f"{qdrant_url}/collections/{collection}/points/scroll",
        "POST",
        headers,
        {
            "limit": 1,
            "with_payload": False,
            "with_vector": False,
            "filter": {"must": [{"has_id": [point_id]}]},
        },
    )
    return not data.get("result", {}).get("points", [])


def main() -> int:
    parser = argparse.ArgumentParser(description="P2-4 automated RAG redteam probe")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--qdrant-url", default=DEFAULT_QDRANT_URL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--gateway-url", default=DEFAULT_GATEWAY_URL)
    parser.add_argument("--embed-model", default=DEFAULT_EMBED_MODEL)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--alert-email", default=DEFAULT_ALERT_EMAIL)
    parser.add_argument("--no-email", action="store_true")
    parser.add_argument("--force-alert", action="store_true", help="Send a test alert even when probe is not surfaced")
    args = parser.parse_args()

    api_key = load_api_key()
    headers = {"api-key": api_key} if api_key else {}
    year_week = current_year_week()
    point_id, doc_id, topic, content = build_probe(args.project, year_week)
    query = f"What does the synthetic redteam probe {topic} say about RAG poisoning defenses?"

    print(f"P2-4 redteam probe start collection={args.collection} point_id={point_id} topic={topic}")

    cleanup_error = None
    try:
        embedding = generate_embedding(args.ollama_url, args.embed_model, content)
        upsert_probe(args.qdrant_url, args.collection, headers, point_id, doc_id, topic, args.project, content, embedding)
        print("probe_upsert=ok")

        response = query_gateway(args.gateway_url, query, args.project)
        print(f"gateway_status={response.get('status')}")
        rank, score, summaries = find_probe_rank(response, doc_id, topic, args.top_k)
        if rank is not None:
            subject = f"[P2-4 ALERT] redteam probe surfaced on {socket.gethostname()} rank={rank}"
            body = build_alert_body(args.collection, doc_id, topic, query, rank, score or 0.0, summaries)
            print(f"ALERT probe_surfaced rank={rank} score={score:.4f}")
            if not args.no_email:
                send_alert(args.alert_email, subject, body)
                print(f"email_sent={args.alert_email}")
            return 1

        print("OK probe_not_surfaced_in_top_k")
        if args.force_alert and not args.no_email:
            subject = f"[P2-4 TEST] redteam probe mail path on {socket.gethostname()}"
            body = build_alert_body(args.collection, doc_id, topic, query, 0, 0.0, summaries)
            send_alert(args.alert_email, subject, body)
            print(f"test_email_sent={args.alert_email}")
        return 0
    finally:
        try:
            delete_probe(args.qdrant_url, args.collection, headers, point_id)
            deleted = confirm_deleted(args.qdrant_url, args.collection, headers, point_id)
            print(f"probe_cleanup={'ok' if deleted else 'failed'}")
        except Exception as err:  # noqa: BLE001 - final cleanup must report any failure
            cleanup_error = err
            print(f"probe_cleanup=error {err}", file=sys.stderr)
        if cleanup_error is not None:
            raise cleanup_error


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (HTTPError, URLError, RuntimeError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(2)
