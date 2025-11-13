"""Comprehensive diagnostic for Day-4 ranking system."""

import asyncio
import sys

# Force UTF-8 encoding for console output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


async def diagnose_all():
    """Check all components of the ranking system."""

    print("\n" + "="*70)
    print("  Day-4 System Diagnostic")
    print("="*70 + "\n")

    # 1. Check Qdrant
    print("1️⃣ Checking Qdrant...")
    try:
        from app.services.vector_store import vector_store
        healthy = vector_store.health_check()
        if healthy:
            info = vector_store.get_collection_info()
            print(f"   ✅ Qdrant is healthy")
            print(f"   Collection: {vector_store.collection_name}")
            print(f"   Vectors: {info.get('vectors_count', 0)}")
            print(f"   Points: {info.get('points_count', 0)}")

            if info.get('vectors_count', 0) == 0:
                print(f"   ⚠️  WARNING: No vectors in Qdrant!")
                print(f"   💡 Run: python populate_qdrant.py")
        else:
            print(f"   ❌ Qdrant is NOT healthy")
            print(f"   💡 Check: docker logs rightstaff-qdrant")
    except Exception as e:
        print(f"   ❌ Qdrant error: {e}")

    # 2. Check Redis
    print("\n2️⃣ Checking Redis...")
    try:
        from app.services.redis_client import redis_client
        result = await redis_client.ping()
        if result:
            print(f"   ✅ Redis is healthy")
        else:
            print(f"   ❌ Redis ping failed")
    except Exception as e:
        print(f"   ❌ Redis error: {e}")

    # 3. Check Database
    print("\n3️⃣ Checking PostgreSQL...")
    try:
        from sqlalchemy import select, func
        from app.database import AsyncSessionLocal
        from app.models.candidate import Candidate, Skill, CandidateSkill

        async with AsyncSessionLocal() as db:
            # Count candidates
            result = await db.execute(select(func.count(Candidate.id)))
            cand_count = result.scalar()

            # Count skills
            result = await db.execute(select(func.count(Skill.id)))
            skill_count = result.scalar()

            # Count mappings
            result = await db.execute(select(func.count(CandidateSkill.candidate_id)))
            mapping_count = result.scalar()

            print(f"   ✅ PostgreSQL is healthy")
            print(f"   Candidates: {cand_count}")
            print(f"   Skills: {skill_count}")
            print(f"   Candidate-Skill mappings: {mapping_count}")

            if cand_count == 0:
                print(f"   ⚠️  WARNING: No candidates in database!")
                print(f"   💡 Run: python add_test_candidate.py")
            elif mapping_count == 0:
                print(f"   ⚠️  WARNING: No skills assigned to candidates!")
    except Exception as e:
        print(f"   ❌ PostgreSQL error: {e}")

    # 4. Check Embedding Service
    print("\n4️⃣ Checking Embedding Service...")
    try:
        from app.services.embeddings import embedding_service
        test_embedding = await embedding_service.embed_text("test")
        print(f"   ✅ Embedding service working")
        print(f"   Embedding dim: {len(test_embedding)}")
    except Exception as e:
        print(f"   ❌ Embedding error: {e}")

    # 5. Check Ranking Services
    print("\n5️⃣ Checking Ranking Services...")
    try:
        from app.services.scoring import structured_scorer
        from app.services.explanation import explanation_generator
        from app.services.ranking import ranking_service

        print(f"   ✅ All ranking services imported successfully")
        print(f"      • Structured scorer")
        print(f"      • Explanation generator")
        print(f"      • Ranking service")
    except Exception as e:
        print(f"   ❌ Import error: {e}")

    # Summary
    print("\n" + "="*70)
    print("Diagnostic Summary:")
    print("="*70)
    print("\nNext steps based on your results:")
    print("1. If Qdrant has 0 vectors: python populate_qdrant.py")
    print("2. If no candidates: python add_test_candidate.py")
    print("3. If all healthy: python test_day4_e2e_adaptive.py")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(diagnose_all())
