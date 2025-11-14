import asyncio
from app.services.embeddings import embedding_service

async def test_embeddings():
    print("Testing embedding service...")
    
    # Test single embedding
    text = "Python developer with FastAPI experience"
    embedding = await embedding_service.embed_text(text)
    print(f"✅ Single embedding: {len(embedding)} dimensions")
    
    # Test batch
    texts = ["Python", "JavaScript", "AWS"]
    embeddings = await embedding_service.embed_batch(texts)
    print(f"✅ Batch embeddings: {len(embeddings)} vectors")
    
    # Model info
    info = embedding_service.get_model_info()
    print(f"Model info: {info}")

if __name__ == "__main__":
    asyncio.run(test_embeddings())