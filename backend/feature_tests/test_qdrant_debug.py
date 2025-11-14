"""
Debug script to test Qdrant vector upsert and identify the ID type issue.
"""
import sys
import io

# Fix Windows console encoding for emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
import uuid

# Connect to Qdrant
client = QdrantClient(host="localhost", port=6333)

# Test collection name
test_collection = "debug_test_collection"

# Clean up if exists
try:
    client.delete_collection(test_collection)
    print(f"✅ Deleted existing collection: {test_collection}")
except Exception as e:
    print(f"ℹ️  Collection doesn't exist yet: {e}")

# Create test collection
client.create_collection(
    collection_name=test_collection,
    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
)
print(f"✅ Created collection: {test_collection}")

# Test 1: String UUID as ID
print("\n=== TEST 1: String UUID as ID ===")
test_vector_1 = [0.1] * 384
test_payload_1 = {"candidate_id": "12eb0a0d-4d02-45c4-96c2-9ab97c1f29e9", "chunk_index": 0}
test_id_1 = "12eb0a0d-4d02-45c4-96c2-9ab97c1f29e9_chunk_0"

try:
    point_1 = PointStruct(
        id=test_id_1,
        vector=test_vector_1,
        payload=test_payload_1
    )
    client.upsert(
        collection_name=test_collection,
        points=[point_1],
        wait=True
    )
    print(f"✅ SUCCESS: String UUID ID works: {test_id_1}")
except Exception as e:
    print(f"❌ FAILED: String UUID ID doesn't work: {e}")

# Test 2: Integer as ID
print("\n=== TEST 2: Integer as ID ===")
test_vector_2 = [0.2] * 384
test_payload_2 = {"candidate_id": "12eb0a0d-4d02-45c4-96c2-9ab97c1f29e9", "chunk_index": 1}
test_id_2 = 1

try:
    point_2 = PointStruct(
        id=test_id_2,
        vector=test_vector_2,
        payload=test_payload_2
    )
    client.upsert(
        collection_name=test_collection,
        points=[point_2],
        wait=True
    )
    print(f"✅ SUCCESS: Integer ID works: {test_id_2}")
except Exception as e:
    print(f"❌ FAILED: Integer ID doesn't work: {e}")

# Test 3: UUID object as ID
print("\n=== TEST 3: UUID object as ID ===")
test_vector_3 = [0.3] * 384
test_payload_3 = {"candidate_id": "12eb0a0d-4d02-45c4-96c2-9ab97c1f29e9", "chunk_index": 2}
test_id_3 = uuid.uuid4()

try:
    point_3 = PointStruct(
        id=test_id_3,
        vector=test_vector_3,
        payload=test_payload_3
    )
    client.upsert(
        collection_name=test_collection,
        points=[point_3],
        wait=True
    )
    print(f"✅ SUCCESS: UUID object ID works: {test_id_3}")
except Exception as e:
    print(f"❌ FAILED: UUID object ID doesn't work: {e}")

# Test 4: Check actual data format being sent
print("\n=== TEST 4: Inspect actual PointStruct ===")
test_vector_4 = [0.4] * 384
test_payload_4 = {"candidate_id": "12eb0a0d-4d02-45c4-96c2-9ab97c1f29e9", "chunk_index": 3}
test_id_4 = "test_id_4"

point_4 = PointStruct(
    id=test_id_4,
    vector=test_vector_4,
    payload=test_payload_4
)

print(f"Point ID type: {type(point_4.id)}")
print(f"Point ID value: {point_4.id}")
print(f"Vector length: {len(point_4.vector)}")
print(f"Vector type: {type(point_4.vector)}")
print(f"First 5 vector elements: {point_4.vector[:5]}")
print(f"Payload: {point_4.payload}")

# Check if vector contains any non-float values
print(f"\n=== TEST 5: Vector validation ===")
print(f"All vector elements are floats: {all(isinstance(x, (float, int)) for x in point_4.vector)}")
print(f"Vector contains NaN: {any(str(x) == 'nan' for x in point_4.vector)}")
print(f"Vector contains Inf: {any(str(x) in ['inf', '-inf'] for x in point_4.vector)}")

# Clean up
print("\n=== CLEANUP ===")
try:
    client.delete_collection(test_collection)
    print(f"✅ Deleted test collection: {test_collection}")
except Exception as e:
    print(f"❌ Failed to delete collection: {e}")

print("\n=== DIAGNOSIS COMPLETE ===")
print("If TEST 1 (String UUID) passed, the issue is elsewhere.")
print("If TEST 1 failed, we need to use integer IDs instead.")

