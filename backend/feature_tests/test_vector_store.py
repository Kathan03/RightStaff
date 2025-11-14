import asyncio
from app.services.vector_store import vector_store

async def test_qdrant():
    print("Testing Qdrant connection...")
    
    # Health check
    healthy = vector_store.health_check()
    print(f"Health: {'✅' if healthy else '❌'}")
    
    # Collection info
    info = vector_store.get_collection_info()
    print(f"Collection: {info}")

if __name__ == "__main__":
    asyncio.run(test_qdrant())