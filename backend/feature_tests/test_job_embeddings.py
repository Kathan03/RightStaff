import asyncio
from app.services.job_embeddings import job_embedding_service

async def test_job_embeddings():
    print("Testing job embeddings...")
    
    job_data = {
        'id': 'test-123',
        'title': 'Python Developer',
        'description': 'Build APIs',
        'must_have_skills_json': ['Python'],
        'required_skills_json': ['FastAPI', 'PostgreSQL']
    }
    
    profile_emb, skills_emb, job_hash = await job_embedding_service.get_or_create_job_embeddings(job_data)
    
    print(f"✅ Profile embedding: {len(profile_emb)} dims")
    print(f"✅ Skills embedding: {len(skills_emb)} dims")
    print(f"✅ Job hash: {job_hash}")

if __name__ == "__main__":
    asyncio.run(test_job_embeddings())