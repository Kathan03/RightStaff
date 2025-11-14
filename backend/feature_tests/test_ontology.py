import asyncio
from app.services.ontology import expand_skills, extract_skills_from_text

async def test_ontology():
    print("Testing ontology service...")
    
    # Test expansion
    skills = ['Python', 'JS']
    expanded = await expand_skills(skills)
    print(f"✅ Expanded: {skills} → {expanded}")
    
    # Test extraction
    text = "5 years Python, JavaScript, AWS, PostgreSQL experience"
    extracted = await extract_skills_from_text(text)
    print(f"✅ Extracted: {extracted}")

if __name__ == "__main__":
    asyncio.run(test_ontology())