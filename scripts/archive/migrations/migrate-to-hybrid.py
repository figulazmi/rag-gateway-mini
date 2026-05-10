#!/usr/bin/env python3
"""
Migrate Qdrant collection from dense-only to hybrid (dense + sparse BM25).

Creates a new collection 'knowledge_v2' with:
  - Named dense vector ('dense', 768-dim, COSINE) — same embeddings as 'knowledge'
  - Named sparse vector ('sparse', IDF modifier) — client-side djb2 BM25

Sparse vectors are generated using djb2 hash tokenizer, which is identical to
the implementation in:
  - n8n Prepare Qdrant Point node (JavaScript)
  - QdrantVectorSearchClient.cs BuildSparseVector() (C#)

This ensures index-time and query-time sparse indices are consistent.

Requirements:
    pip install 'qdrant-client>=1.13.0' --break-system-packages

Run on VM B1:
    python3 scripts/migrate-to-hybrid.py
"""

import re
from qdrant_client import QdrantClient, models
from qdrant_client.models import SparseVector
import time


def djb2_sparse(text: str) -> SparseVector:
    """
    Build sparse BM25 vector using djb2 hash — must match n8n JS and C# implementations:
      h = 5381
      for ch in token: h = ((h << 5) + h + ord(ch)) & 0x7FFFFFFF
    """
    tokens = re.findall(r'[a-z0-9]+', text.lower())
    tf: dict[int, int] = {}
    for t in tokens:
        h = 5381
        for ch in t:
            h = (((h << 5) + h) + ord(ch)) & 0x7FFFFFFF
        tf[h] = tf.get(h, 0) + 1

    if not tf:
        return SparseVector(indices=[], values=[])

    indices = list(tf.keys())
    values  = [float(v) for v in tf.values()]
    return SparseVector(indices=indices, values=values)


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

QDRANT_URL = "http://localhost:6333"
OLD_COLLECTION = "knowledge"
NEW_COLLECTION = "knowledge_v2"
DENSE_VECTOR_SIZE = 768  # nomic-embed-text dimension

client = QdrantClient(url=QDRANT_URL)

# ─── Step 1: Inspect source collection ──────────────────────────
print(f"📊 Checking existing collection '{OLD_COLLECTION}'...")
old_info = client.get_collection(OLD_COLLECTION)
print(f"   Points: {old_info.points_count}")
print(f"   Vectors config: {old_info.config.params.vectors}")

# ─── Step 2: Create hybrid collection ───────────────────────────
print(f"\n🔨 Creating hybrid collection '{NEW_COLLECTION}'...")

if client.collection_exists(NEW_COLLECTION):
    print(f"   ⚠️  Collection '{NEW_COLLECTION}' exists. Deleting...")
    client.delete_collection(NEW_COLLECTION)

client.create_collection(
    collection_name=NEW_COLLECTION,
    vectors_config={
        "dense": models.VectorParams(
            size=DENSE_VECTOR_SIZE,
            distance=models.Distance.COSINE,
        ),
    },
    sparse_vectors_config={
        "sparse": models.SparseVectorParams(
            modifier=models.Modifier.IDF,
        ),
    },
)
print(f"   ✅ Collection '{NEW_COLLECTION}' created with dense + sparse (BM25 IDF) support")

# ─── Step 3: Payload indexes for filtered search ────────────────
print(f"\n📇 Creating payload indexes...")
index_fields = [
    ("project", models.PayloadSchemaType.KEYWORD),
    ("chunk_type", models.PayloadSchemaType.KEYWORD),
    ("status", models.PayloadSchemaType.KEYWORD),
    ("tags", models.PayloadSchemaType.KEYWORD),
    ("session_type", models.PayloadSchemaType.KEYWORD),
    ("environment", models.PayloadSchemaType.KEYWORD),
]
for field_name, field_type in index_fields:
    client.create_payload_index(
        collection_name=NEW_COLLECTION,
        field_name=field_name,
        field_schema=field_type,
        wait=True,
    )
    print(f"   ✅ Indexed: {field_name} ({field_type})")

# ─── Step 4: Migrate points ─────────────────────────────────────
print(f"\n📦 Migrating points from '{OLD_COLLECTION}' to '{NEW_COLLECTION}'...")
offset = None
migrated = 0
batch_size = 50

while True:
    results, offset = client.scroll(
        collection_name=OLD_COLLECTION,
        limit=batch_size,
        offset=offset,
        with_vectors=True,
        with_payload=True,
    )

    if not results:
        break

    points_to_upsert = []
    for point in results:
        # Extract dense vector (handle named/unnamed source format)
        if isinstance(point.vector, dict):
            dense_vector = point.vector.get("dense", next(iter(point.vector.values())))
        elif isinstance(point.vector, list):
            dense_vector = point.vector
        else:
            print(f"   ⚠️  Skipping point {point.id}: unknown vector format")
            continue

        # Build sparse text from topic + Key Facts to reduce full-content sparse noise.
        content_text = point.payload.get("content", "") if point.payload else ""
        topic_text   = point.payload.get("topic",   "") if point.payload else ""
        sparse_text  = f"{topic_text} {extract_key_facts(content_text)}".strip()

        new_point = models.PointStruct(
            id=point.id,
            vector={
                "dense":  dense_vector,
                "sparse": djb2_sparse(sparse_text),
            },
            payload=point.payload,
        )
        points_to_upsert.append(new_point)

    if points_to_upsert:
        client.upsert(
            collection_name=NEW_COLLECTION,
            points=points_to_upsert,
        )
        migrated += len(points_to_upsert)
        print(f"   Migrated: {migrated} points...")

    if offset is None:
        break

    time.sleep(0.5)

# ─── Step 5: Verify ─────────────────────────────────────────────
print(f"\n🔍 Verification...")
new_info = client.get_collection(NEW_COLLECTION)
print(f"   Old collection '{OLD_COLLECTION}': {old_info.points_count} points")
print(f"   New collection '{NEW_COLLECTION}': {new_info.points_count} points")

if new_info.points_count == old_info.points_count:
    print(f"\n✅ Migration complete! All {migrated} points migrated successfully.")
    print(f"\n📝 Next steps:")
    print(f"   1. Test hybrid search via Qdrant Query API on '{NEW_COLLECTION}'")
    print(f"   2. RAG Gateway already targets '{NEW_COLLECTION}' (appsettings updated)")
    print(f"   3. Update n8n workflow + push-to-qdrant.sh to ingest into '{NEW_COLLECTION}'")
    print(f"   4. After verification, optionally delete '{OLD_COLLECTION}'")
else:
    print(f"\n⚠️  Point count mismatch! Check for errors above.")
