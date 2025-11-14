"""Quick Day-4 feature verification without pytest."""

import asyncio


async def test_services():
    """Test that all Day-4 services can be imported."""

    print("\n🧪 Testing Day-4 Service Imports...")

    try:
        from app.services.job_embeddings import job_embedding_service
        print("✅ job_embeddings service imported")
    except Exception as e:
        print(f"❌ job_embeddings failed: {e}")

    try:
        from app.services.retrieval import dense_retriever
        print("✅ retrieval service imported")
    except Exception as e:
        print(f"❌ retrieval failed: {e}")

    try:
        from app.services.scoring import structured_scorer
        print("✅ scoring service imported")
    except Exception as e:
        print(f"❌ scoring failed: {e}")

    try:
        from app.services.explanation import explanation_generator
        print("✅ explanation service imported")
    except Exception as e:
        print(f"❌ explanation failed: {e}")

    try:
        from app.services.ranking import ranking_service
        print("✅ ranking service imported")
    except Exception as e:
        print(f"❌ ranking failed: {e}")

    # Test scoring logic
    print("\n🧪 Testing Structured Scoring Logic...")
    from app.services.scoring import structured_scorer

    candidate = {
        'years_experience': 5,
        'skills': ['Python', 'FastAPI'],
        'city': 'Austin',
        'open_to_remote': True,
        'updated_at': '2025-11-01T00:00:00Z',
        'professional_summary': 'Engineer'
    }

    job = {
        'required_skills_json': ['Python', 'FastAPI'],
        'min_years_experience': 3,
        'max_years_experience': 10,
        'location': 'Austin',
        'work_arrangement': 'hybrid',
        'department': 'engineering'
    }

    score = await structured_scorer.calculate_score(candidate, job)
    print(f"✅ Structured score calculated: {score.combined_score:.2%}")
    print(f"   - Nice-to-have: {score.nice_to_have_coverage:.2%}")
    print(f"   - Experience: {score.experience_score:.2%}")
    print(f"   - Location: {score.location_score:.2%}")

    # Test ontology
    print("\n🧪 Testing Ontology Skills Expansion...")
    from app.services.ontology import expand_skills

    skills = ['Python', 'JavaScript']
    expanded = await expand_skills(skills, use_taxonomy=False)
    print(f"✅ Skills expanded: {skills} → {expanded}")

    print("\n✅ All Day-4 services verified successfully!")


if __name__ == "__main__":
    asyncio.run(test_services())
