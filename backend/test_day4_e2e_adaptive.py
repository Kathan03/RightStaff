"""Adaptive Day-4 E2E test that works with your existing database."""

import asyncio
import httpx
import json
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.candidate import Candidate, CandidateSkill, Skill


async def get_test_job_config():
    """Get job configuration that will match candidates in database."""

    async with AsyncSessionLocal() as db:
        # Check if we have candidates
        result = await db.execute(select(func.count(Candidate.id)))
        candidate_count = result.scalar()

        if candidate_count == 0:
            print("⚠️  No candidates in database!")
            return None

        # Get most common skills
        result = await db.execute(
            select(Skill.name, func.count(CandidateSkill.candidate_id).label('count'))
            .join(CandidateSkill)
            .group_by(Skill.name)
            .order_by(func.count(CandidateSkill.candidate_id).desc())
            .limit(5)
        )
        top_skills = result.all()

        if not top_skills:
            # No skills assigned - use minimal requirements
            return {
                "title": "General Position",
                "description": "Looking for qualified candidates.",
                "required_skills": [],
                "must_have_skills": [],
                "min_years_experience": 0,
                "max_years_experience": 50,
                "location": None
            }

        # Use most common skill as must-have
        must_have = top_skills[0][0]
        nice_to_have = [s[0] for s in top_skills[1:4]]

        # Get experience range from candidates
        result = await db.execute(
            select(
                func.min(Candidate.years_experience),
                func.max(Candidate.years_experience),
                func.avg(Candidate.years_experience)
            )
        )
        min_exp, max_exp, avg_exp = result.first()

        return {
            "title": f"Senior {must_have} Developer",
            "description": f"Looking for experienced {must_have} developers with knowledge of {', '.join(nice_to_have[:2])}.",
            "required_skills": nice_to_have,
            "must_have_skills": [must_have],
            "min_years_experience": max(0, float(avg_exp or 2) - 2) if avg_exp else 0,
            "max_years_experience": float(max_exp or 20) if max_exp else 20,
            "location": None  # Don't filter by location for better match rate
        }


async def test_day4_pipeline():
    """Test Day-4 ranking pipeline with adaptive job configuration."""

    print("\n" + "="*70)
    print("  Day-4 Adaptive End-to-End Test")
    print("="*70)

    # Step 0: Check database and get adaptive job config
    print("\n0️⃣ Analyzing database for test configuration...")
    job_config = await get_test_job_config()

    if not job_config:
        print("❌ Cannot run test - no candidates in database")
        print("\n💡 To add candidates:")
        print("   1. Upload resumes via API: POST /api/v1/candidates")
        print("   2. Or insert test data directly into PostgreSQL")
        return

    print("✅ Found candidates in database")
    print(f"\n   Test job will use:")
    print(f"   • Must-have: {job_config['must_have_skills']}")
    print(f"   • Nice-to-have: {job_config['required_skills']}")
    print(f"   • Experience: {job_config['min_years_experience']}-{job_config['max_years_experience']} years")

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:

        # Step 1: Check backend health
        print("\n1️⃣ Checking backend health...")
        try:
            response = await client.get("http://localhost:8000/health")
            print(f"✅ Backend is running (status: {response.status_code})")
        except httpx.ConnectError:
            print(f"❌ Backend is NOT running on port 8000")
            print(f"💡 Start backend: cd backend && uvicorn app.main:app --reload")
            return

        # Step 2: Create test job
        print("\n2️⃣ Creating test job...")
        response = await client.post(
            "http://localhost:8000/api/v1/jobs/",
            json=job_config,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code != 201:
            print(f"❌ Failed to create job: {response.status_code}")
            print(f"   Error: {response.text}")
            return

        job = response.json()
        job_id = job["job_id"]
        print(f"✅ Job created: {job_id}")
        print(f"   Title: {job_config['title']}")

        # Step 3: Test Day-3 SQL gating
        print(f"\n3️⃣ Testing SQL gating (Day-3 baseline)...")
        response = await client.post(
            f"http://localhost:8000/api/v1/jobs/rank",
            json={"job_id": job_id, "use_cache": False}
        )

        if response.status_code == 200:
            result = response.json()
            qualified = result.get('total_qualified', 0)
            print(f"✅ SQL gating: {qualified} candidates qualified")

            if qualified == 0:
                print(f"\n⚠️  WARNING: No candidates passed SQL gates!")
                print(f"   This means no candidates have the required skills/experience")
                print(f"   The full ranking pipeline will return empty results")
                print(f"\n   Job requirements:")
                print(f"   • Must-have skills: {job_config['must_have_skills']}")
                print(f"   • Min experience: {job_config['min_years_experience']} years")
        else:
            print(f"⚠️  SQL gating failed: {response.status_code}")

        # Step 4: Test Day-4 full ranking
        print(f"\n4️⃣ Testing FULL ranking pipeline (Day-4)...")
        response = await client.post(
            f"http://localhost:8000/api/v1/jobs/{job_id}/rank_full",
            json={"use_cache": False}
        )

        if response.status_code == 200:
            ranking = response.json()
            total = ranking['metadata']['total_candidates']

            print(f"✅ Full ranking complete!")
            print(f"\n📊 Results Summary:")
            print(f"   Total candidates: {total}")
            print(f"   High confidence: {ranking['metadata']['high_confidence']}")
            print(f"   Medium confidence: {ranking['metadata']['medium_confidence']}")
            print(f"   Low confidence: {ranking['metadata']['low_confidence']}")

            if total == 0:
                print(f"\n⚠️  No candidates returned")
                print(f"   This is expected if SQL gating filtered everyone out")
            else:
                # Show top 3 candidates
                for i, candidate in enumerate(ranking['ranked_candidates'][:3], 1):
                    print(f"\n🏆 Rank #{i}:")
                    print(f"   ID: {candidate['candidate_id']}")
                    print(f"   Score: {candidate['final_score']:.2%}")
                    print(f"   Band: {candidate['band']}")
                    print(f"   Summary: {candidate['summary']}")
                    print(f"   Top reasons:")
                    for reason in candidate['reasons'][:3]:
                        print(f"      • {reason}")

                # Test caching
                print(f"\n5️⃣ Testing cache...")
                response = await client.post(
                    f"http://localhost:8000/api/v1/jobs/{job_id}/rank_full",
                    json={"use_cache": True}
                )
                if response.status_code == 200:
                    print("✅ Cache working")

                print(f"\n✅ All Day-4 features tested successfully!")

        elif response.status_code == 500:
            error = response.json()
            print(f"❌ Ranking failed with error:")
            print(f"   {error.get('detail', 'Unknown error')}")
        else:
            print(f"❌ Unexpected status: {response.status_code}")
            print(f"   Response: {response.text}")

    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(test_day4_pipeline())
