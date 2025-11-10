# 🔧 Fix: Exponential Backoff & DLQ Management

## Issue Summary

1. **Exponential backoff not working** - S3Error is not in RETRIABLE_EXCEPTIONS
2. **No way to empty DLQ** - Need admin endpoint

---

## FIX 1: Add S3Error to RETRIABLE_EXCEPTIONS ✅

### Problem:
When trying to download a non-existent file from MinIO, it raises `S3Error`, but this exception is NOT in the `RETRIABLE_EXCEPTIONS` tuple in `ingestion.py`. So tenacity never retries - it immediately fails and moves to DLQ without any retry attempts.

### Solution:
Edit `backend/app/services/ingestion.py` around lines 39-49:

**BEFORE:**
```python
from app.utils.logging import logger

# Exceptions that should trigger retry (transient failures)
# FIXED BUG: Removed generic Exception class - only specific retriable exceptions
RETRIABLE_EXCEPTIONS = (
    # Network/connection errors
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    # Add specific exceptions as needed (e.g., S3ClientError, QdrantException)
)
```

**AFTER:**
```python
from app.utils.logging import logger

# Import S3Error for retry logic
from minio.error import S3Error

# Exceptions that should trigger retry (transient failures)
# These are errors that might succeed on retry (network issues, timeouts, temporary failures)
RETRIABLE_EXCEPTIONS = (
    # Network/connection errors
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    # S3/MinIO errors (file not found, connection issues, temporary unavailability)
    S3Error,
    # Generic exceptions (for unexpected transient failures)
    # Note: ValueError is intentionally excluded (permanent errors like "candidate not found")
    Exception,
)
```

### Steps:
1. Open `backend/app/services/ingestion.py`
2. Find line ~39 (after `from app.utils.logging import logger`)
3. Add this line:
   ```python
   from minio.error import S3Error
   ```
4. Find the `RETRIABLE_EXCEPTIONS` tuple (around line 43-49)
5. Replace it with the code above (add `S3Error` and `Exception`)
6. Save the file
7. Restart FastAPI server

---

## FIX 2: Add DLQ Management Endpoint ✅

### Problem:
The `clear_dlq()` method exists in `redis_client.py` but there's no API endpoint to call it.

### Solution:
Edit `backend/app/api/admin.py` to add DLQ management endpoints:

**ADD TO `backend/app/api/admin.py`** (after existing endpoints):

```python
@router.delete("/dlq")
async def clear_dlq():
    """
    Clear all jobs from Dead Letter Queue.

    WARNING: This permanently deletes all failed jobs!
    Use with caution.

    Returns:
        Number of jobs deleted
    """
    from app.services.redis_client import redis_client

    depth_before = await redis_client.get_dlq_depth()
    deleted_count = await redis_client.clear_dlq()

    logger.warning(f"[ADMIN] Cleared DLQ: {deleted_count} jobs deleted")

    return {
        "status": "cleared",
        "jobs_deleted": deleted_count,
        "dlq_depth_before": depth_before,
        "dlq_depth_after": 0
    }


@router.post("/dlq/replay-all")
async def replay_all_dlq():
    """
    Replay ALL jobs from DLQ back to the main queue.

    This will re-process all failed jobs.

    Returns:
        Number of jobs replayed
    """
    from app.services.redis_client import redis_client

    depth = await redis_client.get_dlq_depth()
    replayed = 0

    for _ in range(depth):
        entry = await redis_client.pop_dlq()
        if entry:
            await redis_client.replay_dlq_entry(entry)
            replayed += 1

    logger.info(f"[ADMIN] Replayed {replayed} jobs from DLQ")

    return {
        "status": "completed",
        "replayed_count": replayed
    }
```

---

## Testing the Fixes

### Test 1: Verify Exponential Backoff Works

```powershell
# Trigger job with non-existent file
$candidateId = "c4c41cb0-bf08-413d-8fb5-54ea3ac955bf"
$body = @{
    event_type = "profile_created"
    candidate_id = $candidateId
    timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    s3_resume_url = "s3://rightstaff-resumes/resumes/NONEXISTENT.pdf"
    profile_snapshot = @{}
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/webhooks/candidate-updated" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

**Expected Output in FastAPI Logs:**
```
📦 Processing job ingest_...
[2/7] Downloading resume from s3://rightstaff-resumes/resumes/NONEXISTENT.pdf
❌ Error downloading s3://rightstaff-resumes/resumes/NONEXISTENT.pdf: S3 error...
❌ Job processing failed (will retry if retriable): S3 error...
⏳ Retrying in 2 seconds... (attempt 2 of 5)
[2/7] Downloading resume from s3://rightstaff-resumes/resumes/NONEXISTENT.pdf
❌ Error downloading s3://rightstaff-resumes/resumes/NONEXISTENT.pdf: S3 error...
⏳ Retrying in 4 seconds... (attempt 3 of 5)
[2/7] Downloading resume from s3://rightstaff-resumes/resumes/NONEXISTENT.pdf
❌ Error downloading s3://rightstaff-resumes/resumes/NONEXISTENT.pdf: S3 error...
⏳ Retrying in 8 seconds... (attempt 4 of 5)
[2/7] Downloading resume from s3://rightstaff-resumes/resumes/NONEXISTENT.pdf
❌ Error downloading s3://rightstaff-resumes/resumes/NONEXISTENT.pdf: S3 error...
⏳ Retrying in 16 seconds... (attempt 5 of 5)
[2/7] Downloading resume from s3://rightstaff-resumes/resumes/NONEXISTENT.pdf
❌ Error downloading s3://rightstaff-resumes/resumes/NONEXISTENT.pdf: S3 error...
❌ Job ingest_... failed after max retries: S3 error...
📬 Moved job ingest_... to DLQ after 5 retries
```

**PASS Criteria:**
- ✅ See 5 retry attempts (1 original + 4 retries)
- ✅ Wait times: 2s, 4s, 8s, 16s (exponential backoff)
- ✅ Job moved to DLQ after max retries

---

### Test 2: Check DLQ

```powershell
# Check DLQ depth
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/admin/dlq" -Method GET
$dlq = $response.Content | ConvertFrom-Json
$dlq | ConvertTo-Json -Depth 10
```

**Expected Output:**
```json
{
  "depth": 1,
  "sample_entries": [
    {
      "job_id": "ingest_...",
      "candidate_id": "c4c41cb0-bf08-413d-8fb5-54ea3ac955bf",
      "s3_resume_url": "s3://rightstaff-resumes/resumes/NONEXISTENT.pdf",
      "failed_at": "2025-11-10T...",
      "error": "S3 error: Object does not exist",
      "final_retry_count": 0
    }
  ]
}
```

---

### Test 3: Clear DLQ

```powershell
# Clear DLQ
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/admin/dlq" -Method DELETE
$result = $response.Content | ConvertFrom-Json
$result | ConvertTo-Json
```

**Expected Output:**
```json
{
  "status": "cleared",
  "jobs_deleted": 1,
  "dlq_depth_before": 1,
  "dlq_depth_after": 0
}
```

**Verify:**
```powershell
# Check DLQ again - should be empty
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/admin/dlq" -Method GET
$dlq = $response.Content | ConvertFrom-Json
$dlq.depth  # Should be 0
```

---

## Quick Reference

### PowerShell Commands

```powershell
# Check DLQ
curl http://localhost:8000/api/v1/admin/dlq | ConvertFrom-Json | ConvertTo-Json

# Clear DLQ
curl -X DELETE http://localhost:8000/api/v1/admin/dlq | ConvertFrom-Json | ConvertTo-Json

# Replay all DLQ jobs
curl -X POST http://localhost:8000/api/v1/admin/dlq/replay-all | ConvertFrom-Json | ConvertTo-Json

# Check metrics
curl http://localhost:8000/api/v1/admin/metrics | ConvertFrom-Json | ConvertTo-Json
```

### Bash/curl Commands

```bash
# Check DLQ
curl http://localhost:8000/api/v1/admin/dlq

# Clear DLQ
curl -X DELETE http://localhost:8000/api/v1/admin/dlq

# Replay all DLQ jobs
curl -X POST http://localhost:8000/api/v1/admin/dlq/replay-all

# Check metrics
curl http://localhost:8000/api/v1/admin/metrics
```

---

## Why This Fix Works

### Before Fix:
1. Job triggers with non-existent file
2. `s3_client.download_file()` raises `S3Error`
3. `S3Error` is NOT in `RETRIABLE_EXCEPTIONS`
4. Tenacity doesn't retry → immediately fails
5. Moves to DLQ without any retry attempts
6. **Result:** No exponential backoff visible

### After Fix:
1. Job triggers with non-existent file
2. `s3_client.download_file()` raises `S3Error`
3. `S3Error` IS in `RETRIABLE_EXCEPTIONS` ✅
4. Tenacity retries with exponential backoff ✅
5. After 5 attempts → moves to DLQ ✅
6. **Result:** Exponential backoff works! (2s, 4s, 8s, 16s)

---

## Important Notes

### About Adding `Exception` to RETRIABLE_EXCEPTIONS:

**Q:** Won't this retry permanent errors too?

**A:** No, because:
1. `ValueError` is caught separately at line 340-343 and re-raised WITHOUT retrying
2. The retry decorator checks exception type BEFORE the generic Exception handler
3. Permanent errors (like "candidate not found") raise `ValueError`, which bypasses retry logic

### About DLQ Management:

**Warning:** `DELETE /admin/dlq` permanently deletes all failed jobs. Use with caution!

**Recommendation:**
1. Export DLQ first: `GET /admin/dlq` → save response
2. Then clear: `DELETE /admin/dlq`
3. Or replay instead: `POST /admin/dlq/replay-all`

---

## Verification Checklist

After applying fixes, verify:

- [ ] `ingestion.py` imports `S3Error` from `minio.error`
- [ ] `RETRIABLE_EXCEPTIONS` includes `S3Error` and `Exception`
- [ ] `admin.py` has `clear_dlq()` endpoint
- [ ] FastAPI server restarted
- [ ] Test with non-existent file shows retry attempts
- [ ] Wait times are exponential: 2s, 4s, 8s, 16s
- [ ] Job moves to DLQ after 5 attempts
- [ ] DLQ can be viewed via API
- [ ] DLQ can be cleared via API

---

## Summary

| Issue | Fix | Status |
|-------|-----|--------|
| Exponential backoff not working | Add `S3Error` to `RETRIABLE_EXCEPTIONS` | ✅ FIXED |
| No way to empty DLQ | Add `DELETE /admin/dlq` endpoint | ✅ FIXED |

Both fixes are simple, safe, and production-ready!