#!/usr/bin/env python3
"""
Build an experimental Qdrant collection with unchanged dense vectors and sparse
vectors generated from topic plus Key Facts instead of full chunk content.

This script does not modify knowledge_v2. It writes to knowledge_v2_keyfacts by
default so retrieval quality can be compared with eval-retrieval-quality.py.
"""

import argparse
import os
import re
import time
from typing import Any

from qdrant_client import QdrantClient, models
from qdrant_client.models import SparseVector


DENSE_VECTOR_SIZE = 768
INDEX_FIELDS = [
    ("project", models.PayloadSchemaType.KEYWORD),
    ("chunk_type", models.PayloadSchemaType.KEYWORD),
    ("status", models.PayloadSchemaType.KEYWORD),
    ("tags", models.PayloadSchemaType.KEYWORD),
    ("session_type", models.PayloadSchemaType.KEYWORD),
    ("environment", models.PayloadSchemaType.KEYWORD),
]


def djb2_sparse(text: str) -> SparseVector:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    tf: dict[int, int] = {}
    for token in tokens:
        h = 5381
        for ch in token:
            h = (((h << 5) + h) + ord(ch)) & 0x7FFFFFFF
        tf[h] = tf.get(h, 0) + 1

    return SparseVector(indices=list(tf.keys()), values=[float(v) for v in tf.values()])


def extract_key_facts(content: str) -> str:
    lines = content.splitlines()
    facts: list[str] = []
    in_key_facts = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### "):
            heading = stripped.lower().strip("# ")
            in_key_facts = heading == "key facts"
            continue
        if in_key_facts and stripped.startswith(("- ", "* ")):
            facts.append(stripped[2:].strip())

    return " ".join(facts)


def extract_dense_vector(vector: Any) -> list[float] | None:
    if isinstance(vector, dict):
        dense = vector.get("dense")
        if dense is None and vector:
            dense = next(iter(vector.values()))
        return dense
    if isinstance(vector, list):
        return vector
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Build sparse Key Facts experiment collection")
    parser.add_argument("--qdrant-url", default="http://192.168.18.199:6333")
    parser.add_argument("--api-key", default=os.environ.get("QDRANT_API_KEY", ""))
    parser.add_argument("--source", default="knowledge_v2")
    parser.add_argument("--target", default="knowledge_v2_keyfacts")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--force", action="store_true", help="Delete target collection if it already exists")
    args = parser.parse_args()

    client = QdrantClient(url=args.qdrant_url, api_key=args.api_key or None)
    source_info = client.get_collection(args.source)

    if client.collection_exists(args.target):
        if not args.force:
            raise SystemExit(f"Target collection exists: {args.target}. Re-run with --force to rebuild it.")
        client.delete_collection(args.target)

    client.create_collection(
        collection_name=args.target,
        vectors_config={
            "dense": models.VectorParams(size=DENSE_VECTOR_SIZE, distance=models.Distance.COSINE),
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF),
        },
    )

    for field_name, field_type in INDEX_FIELDS:
        client.create_payload_index(
            collection_name=args.target,
            field_name=field_name,
            field_schema=field_type,
            wait=True,
        )

    offset = None
    migrated = 0
    keyfacts_points = 0

    while True:
        points, offset = client.scroll(
            collection_name=args.source,
            limit=args.batch_size,
            offset=offset,
            with_vectors=True,
            with_payload=True,
        )
        if not points:
            break

        upserts = []
        for point in points:
            payload = point.payload or {}
            dense_vector = extract_dense_vector(point.vector)
            if dense_vector is None:
                continue

            topic = payload.get("topic", "") or ""
            content = payload.get("content", "") or ""
            key_facts = extract_key_facts(content)
            sparse_text = f"{topic} {key_facts}".strip()
            if key_facts:
                keyfacts_points += 1

            upserts.append(models.PointStruct(
                id=point.id,
                vector={
                    "dense": dense_vector,
                    "sparse": djb2_sparse(sparse_text),
                },
                payload=payload,
            ))

        if upserts:
            client.upsert(collection_name=args.target, points=upserts)
            migrated += len(upserts)
            print(f"Migrated {migrated} points...")

        if offset is None:
            break
        time.sleep(0.2)

    target_info = client.get_collection(args.target)
    print(f"Source points: {source_info.points_count}")
    print(f"Target points: {target_info.points_count}")
    print(f"Points with Key Facts sparse text: {keyfacts_points}")

    if source_info.points_count != target_info.points_count:
        raise SystemExit("Point count mismatch")


if __name__ == "__main__":
    main()
