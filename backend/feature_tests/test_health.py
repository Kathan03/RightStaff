"""
Quick test script to verify the application can start and health checks work.
"""
import asyncio
import sys
from app.database import AsyncSessionLocal
from app.services.redis_client import redis_client
from app.services.vector_store import vector_store
from app.services.s3_client import s3_client
from sqlalchemy import text

async def test_health():
    """Test all service connections."""
    print("Testing RightStaff AI Backend Health...")
    print("=" * 50)

    results = {}

    # Test PostgreSQL
    print("\n1. Testing PostgreSQL...")
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        results["database"] = "OK"
        print("   [OK] PostgreSQL: OK")
    except Exception as e:
        results["database"] = f"ERROR: {str(e)[:50]}"
        print(f"   [ERROR] PostgreSQL: ERROR - {e}")

    # Test Redis
    print("\n2. Testing Redis...")
    try:
        await redis_client.ping()
        results["redis"] = "OK"
        print("   [OK] Redis: OK")
    except Exception as e:
        results["redis"] = f"ERROR: {str(e)[:50]}"
        print(f"   [ERROR] Redis: ERROR - {e}")

    # Test Qdrant
    print("\n3. Testing Qdrant...")
    try:
        vector_store.client.get_collections()
        results["qdrant"] = "OK"
        print("   [OK] Qdrant: OK")
    except Exception as e:
        results["qdrant"] = f"ERROR: {str(e)[:50]}"
        print(f"   [ERROR] Qdrant: ERROR - {e}")

    # Test MinIO
    print("\n4. Testing MinIO...")
    try:
        if s3_client.client.bucket_exists(s3_client.bucket_name):
            results["minio"] = "OK"
            print("   [OK] MinIO: OK")
        else:
            results["minio"] = "WARNING: bucket not found"
            print("   [WARN] MinIO: WARNING - bucket not found")
    except Exception as e:
        results["minio"] = f"ERROR: {str(e)[:50]}"
        print(f"   [ERROR] MinIO: ERROR - {e}")

    print("\n" + "=" * 50)
    print("SUMMARY:")
    for service, status in results.items():
        print(f"  {service:12} : {status}")

    # Check if all services are OK
    all_ok = all("OK" in status for status in results.values())
    if all_ok:
        print("\n[SUCCESS] All services are healthy!")
        return 0
    else:
        print("\n[WARNING] Some services have issues")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(test_health())
    sys.exit(exit_code)
