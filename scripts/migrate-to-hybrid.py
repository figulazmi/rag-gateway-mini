#!/usr/bin/env python3
"""
Migrate Qdrant collection from dense-only to hybrid (dense + sparse BM25).

Creates a new collection 'knowledge_v2' with:
  - Named dense vector ('dense', 768-dim, COSINE) — same embeddings as 'knowledge'
  - Named sparse vector ('sparse', BM25 IDF modifier) — server-side BM25 inference

Then copies all points from 'knowledge' to 'knowledge_v2', re-using the existing
dense vector and sending raw text as a Document so Qdrant generates the sparse
vector server-side.

Requirements:
    pip install 'qdrant-client>=1.13.0' --break-system-packages

Run on VM B1:
    python3 scripts/migrate-to-hybrid.py
"""

from qdrant_client import QdrantClient, models
import time

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

        # Build sparse text: prefer topic + content for richer BM25 signal
        content_text = point.payload.get("content", "") if point.payload else ""
        topic_text = point.payload.get("topic", "") if point.payload else ""
        sparse_text = f"{topic_text} {content_text}".strip()

        new_point = models.PointStruct(
            id=point.id,
            vector={
                "dense": dense_vector,
                "sparse": models.Document(
                    text=sparse_text,
                    model="Qdrant/bm25",
                ),
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
