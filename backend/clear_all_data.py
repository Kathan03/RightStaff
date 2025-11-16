"""Clear all data from PostgreSQL, MinIO, and Qdrant."""

import asyncio
import sys
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.services.vector_store import vector_store
from app.services.redis_client import redis_client

# Force UTF-8 encoding for console output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


async def clear_postgresql():
    """Clear all tables in PostgreSQL database."""

    print("\n1️⃣ Clearing PostgreSQL...")

    async with AsyncSessionLocal() as db:
        try:
            # Disable foreign key checks temporarily
            await db.execute(text("SET session_replication_role = 'replica';"))

            # Clear tables in correct order (respecting foreign keys)
            tables = [
                'rightstaff.candidate_skill',
                'rightstaff.candidate_contact',
                'rightstaff.candidate_education',
                'rightstaff.candidate_experience',
                'rightstaff.candidate_resume',
                'rightstaff.application',  # Delete applications before candidates/jobs
                'rightstaff.candidate',
                'rightstaff.job',
                'rightstaff.skill'
            ]

            for table in tables:
                try:
                    result = await db.execute(text(f"DELETE FROM {table}"))
                    await db.commit()
                    print(f"   ✅ Cleared table: {table}")
                except Exception as e:
                    print(f"   ⚠️  Warning: Could not clear {table}: {e}")
                    await db.rollback()

            # Re-enable foreign key checks
            await db.execute(text("SET session_replication_role = 'origin';"))
            await db.commit()

            print("   ✅ PostgreSQL cleared successfully")

        except Exception as e:
            print(f"   ❌ Error clearing PostgreSQL: {e}")
            await db.rollback()


async def clear_minio():
    """Clear all files from MinIO bucket."""

    print("\n2️⃣ Clearing MinIO...")

    try:
        from app.services.s3_client import s3_client

        # List all objects in the bucket
        bucket_name = s3_client.bucket_name
        objects = s3_client.client.list_objects(bucket_name, recursive=True)

        deleted_count = 0
        for obj in objects:
            try:
                s3_client.client.remove_object(bucket_name, obj.object_name)
                deleted_count += 1
            except Exception as e:
                print(f"   ⚠️  Warning: Could not delete {obj.object_name}: {e}")

        print(f"   ✅ MinIO cleared: {deleted_count} objects deleted")

    except ImportError:
        print(f"   ℹ️  MinIO storage service not configured (optional)")
    except Exception as e:
        print(f"   ⚠️  Error clearing MinIO: {e}")
        print(f"   Note: MinIO may not be running")


async def clear_qdrant():
    """Clear all vectors from Qdrant collection."""

    print("\n Clearing Qdrant collection...")

    try:
        # Get collection info
        info = vector_store.get_collection_info()
        vector_count = info.get('vectors_count', 0)
        print(f"   Current vectors: {vector_count}")

        # Delete collection and recreate
        vector_store.client.delete_collection(vector_store.collection_name)
        print(f"   ✅ Deleted collection: {vector_store.collection_name}")

        # Recreate collection
        vector_store.create_collection(vector_size=384)
        print(f"   ✅ Recreated empty collection")

    except Exception as e:
        print(f"   ⚠️  Error clearing collection: {e}")


async def clear_redis():
    """Clear all cached data from Redis."""

    print("\n4️⃣ Clearing Redis cache...")

    try:
        # Clear all keys - use the underlying client
        await redis_client.client.flushdb()
        print("   ✅ Redis cache cleared")

    except Exception as e:
        print(f"   ❌ Error clearing Redis: {e}")


async def clear_all():
    """Clear all data from all systems."""

    print("\n" + "="*70)
    print("  CLEARING ALL DATA")
    print("="*70)
    print("\n⚠️  WARNING: This will delete ALL data from:")
    print("   • PostgreSQL (candidates, jobs, skills)")
    print("   • MinIO (uploaded resumes)")
    print("   • Qdrant (vector embeddings)")
    print("   • Redis (cached rankings)")
    print("\n⏳ Starting in 3 seconds... Press Ctrl+C to cancel")

    try:
        await asyncio.sleep(3)
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        return

    # Clear each system
    await clear_postgresql()
    await clear_minio()
    await clear_qdrant()
    await clear_redis()

    # Summary
    print("\n" + "="*70)
    print("✅ All data cleared successfully!")
    print("="*70)
    print("\n💡 Next step: Run 'python populate_dummy_data.py' to add test data\n")


if __name__ == "__main__":
    asyncio.run(clear_all())
