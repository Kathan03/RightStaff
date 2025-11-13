"""Check what candidates and skills exist in the database."""

import asyncio
import sys
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.candidate import Candidate, CandidateSkill, Skill

# Force UTF-8 encoding for console output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


async def check_database():
    """Check database contents."""

    print("\n🔍 Checking Database Contents...\n")

    async with AsyncSessionLocal() as db:

        # 1. Count candidates
        result = await db.execute(select(func.count(Candidate.id)))
        candidate_count = result.scalar()
        print(f"1️⃣ Total Candidates: {candidate_count}")

        if candidate_count == 0:
            print("   ⚠️  No candidates in database!")
            print("   💡 You need to ingest some candidates first")
            return

        # 2. Sample candidates
        result = await db.execute(
            select(Candidate.id, Candidate.full_name, Candidate.years_experience)
            .limit(5)
        )
        candidates = result.all()

        print("\n2️⃣ Sample Candidates:")
        for cand in candidates:
            print(f"   • {cand.full_name} ({cand.years_experience} years) - ID: {str(cand.id)[:8]}")

        # 3. Check skills
        result = await db.execute(select(func.count(Skill.id)))
        skill_count = result.scalar()
        print(f"\n3️⃣ Total Skills in Ontology: {skill_count}")

        # 4. Sample skills
        result = await db.execute(select(Skill.name).limit(20))
        skills = [row[0] for row in result.all()]
        print(f"\n4️⃣ Sample Skills:")
        for skill in skills:
            print(f"   • {skill}")

        # 5. Check candidate-skill relationships
        result = await db.execute(
            select(func.count(CandidateSkill.candidate_id))
        )
        candidate_skill_count = result.scalar()
        print(f"\n5️⃣ Total Candidate-Skill Mappings: {candidate_skill_count}")

        # 6. Find candidates with specific skills
        for test_skill in ["Python", "JavaScript", "Java", "SQL"]:
            result = await db.execute(
                select(func.count(CandidateSkill.candidate_id.distinct()))
                .join(Skill)
                .where(Skill.name == test_skill)
            )
            count = result.scalar()
            print(f"   • Candidates with '{test_skill}': {count}")

        # 7. Get most common skills
        print(f"\n6️⃣ Most Common Skills:")
        result = await db.execute(
            select(Skill.name, func.count(CandidateSkill.candidate_id).label('count'))
            .join(CandidateSkill)
            .group_by(Skill.name)
            .order_by(func.count(CandidateSkill.candidate_id).desc())
            .limit(10)
        )
        top_skills = result.all()
        for skill, count in top_skills:
            print(f"   • {skill}: {count} candidates")

        # 8. Suggest test job configuration
        if top_skills:
            most_common_skill = top_skills[0][0]
            second_skill = top_skills[1][0] if len(top_skills) > 1 else None

            print(f"\n7️⃣ Suggested Test Job Configuration:")
            print(f"   must_have_skills: [\"{most_common_skill}\"]")
            if second_skill:
                print(f"   required_skills: [\"{second_skill}\"]")

            # Find candidate with most common skill
            result = await db.execute(
                select(Candidate.id, Candidate.full_name, Candidate.years_experience)
                .join(CandidateSkill)
                .join(Skill)
                .where(Skill.name == most_common_skill)
                .limit(1)
            )
            sample = result.first()
            if sample:
                print(f"\n   Example matching candidate:")
                print(f"   • {sample.full_name} ({sample.years_experience} years)")
                print(f"   • Has skill: {most_common_skill}")

    print("\n" + "="*60)
    print("✅ Database check complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(check_database())
