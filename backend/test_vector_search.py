"""Test if vector search with kind filters works."""

import asyncio
from app.services.vector_store import vector_store
from app.services.embeddings import embedding_service


async def test_search():
    print("\n=== Testing Vector Search with Kind Filters ===\n")

    # Get collection info
    info = vector_store.get_collection_info()
    print(f"Qdrant Collection: {vector_store.collection_name}")
    print(f"Total vectors: {info.get('vectors_count', 0)}")
    print(f"Total points: {info.get('points_count', 0)}")

    # Generate a test query vector
    test_query = "Python developer with React experience"
    query_vector = await embedding_service.embed_text(test_query)
    print(f"\nQuery: '{test_query}'")
    print(f"Query vector dim: {len(query_vector)}")

    # Test 1: Search for profiles
    print("\n1. Searching for PROFILE vectors...")
    profile_results = vector_store.search(
        query_vector=query_vector,
        filter_dict={
            "must": [
                {"key": "kind", "match": {"value": "profile"}}
            ]
        },
        top_k=10
    )
    print(f"   Results: {len(profile_results)} profiles found")
    for i, point in enumerate(profile_results[:3], 1):
        name = point.payload.get('full_name', 'N/A')
        score = point.score
        print(f"   {i}. {name} (score: {score:.4f})")

    # Test 2: Search for skills
    print("\n2. Searching for SKILLS vectors...")
    skills_results = vector_store.search(
        query_vector=query_vector,
        filter_dict={
            "must": [
                {"key": "kind", "match": {"value": "skills"}}
            ]
        },
        top_k=10
    )
    print(f"   Results: {len(skills_results)} skills vectors found")
    for i, point in enumerate(skills_results[:3], 1):
        skills = point.payload.get('skills', [])
        score = point.score
        print(f"   {i}. Skills: {', '.join(skills[:5])} (score: {score:.4f})")

    # Test 3: Search for chunks
    print("\n3. Searching for CHUNK vectors...")
    chunk_results = vector_store.search(
        query_vector=query_vector,
        filter_dict={
            "must": [
                {"key": "kind", "match": {"value": "chunk"}}
            ]
        },
        top_k=10
    )
    print(f"   Results: {len(chunk_results)} chunk vectors found")
    for i, point in enumerate(chunk_results[:3], 1):
        text = point.payload.get('chunk_text', '')[:50]
        score = point.score
        print(f"   {i}. Text: '{text}...' (score: {score:.4f})")

    # Summary
    print("\n=== SUMMARY ===")
    print(f"Profile vectors: {len(profile_results)}")
    print(f"Skills vectors: {len(skills_results)}")
    print(f"Chunk vectors: {len(chunk_results)}")

    if len(profile_results) > 0 and len(skills_results) > 0 and len(chunk_results) > 0:
        print("\nSTATUS: FIX SUCCESSFUL! All vector types are searchable.")
    else:
        print("\nSTATUS: FIX INCOMPLETE. Some vector types are missing.")
        if len(profile_results) == 0:
            print("  - Profile vectors: MISSING")
        if len(skills_results) == 0:
            print("  - Skills vectors: MISSING")
        if len(chunk_results) == 0:
            print("  - Chunk vectors: MISSING")


if __name__ == "__main__":
    asyncio.run(test_search())