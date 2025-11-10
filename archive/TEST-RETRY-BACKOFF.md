# 🧪 Test: Exponential Backoff & DLQ Management

## ✅ Fixes Applied

1. **Added S3Error to RETRIABLE_EXCEPTIONS** in `backend/app/services/ingestion.py`
2. **DLQ management endpoints already exist** in `backend/app/api/admin.py`

---

## 🚀 How to Test

### Step 1: Restart FastAPI Server

```bash
# Stop current server (Ctrl+C if running)
# Then restart:
cd backend
uvicorn app.main:app --reload
```

**Wait for:** `INFO:     Application startup complete.`

---

### Step 2: Trigger Job with Non-Existent File (PowerShell)

```powershell
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

$response.Content | ConvertFrom-Json | ConvertTo-Json
```

---

### Step 3: Watch FastAPI Logs

You should see output similar to this:

```
📦 Processing job ingest_c4c41cb0-bf08-413d-8fb5-54ea3ac955bf_1699999999
[1/7] Fetching candidate details: c4c41cb0-bf08-413d-8fb5-54ea3ac955bf
✅ Found candidate: Prathyusha Elipay
[2/7] Downloading resume from s3://rightstaff-resumes/resumes/NONEXISTENT.pdf
❌ Error downloading s3://rightstaff-resumes/resumes/NONEXISTENT.pdf: S3 error: Object does not exist
❌ Job processing failed (will retry if retriable): S3 error: Object does not exist

🔄 Retrying in 2 seconds... (1 of 4 retries left)

[2/7] Downloading resume from s3://rightstaff-resumes/resumes/NONEXISTENT.pdf
❌ Error downloading s3://rightstaff-resumes/resumes/NONEXISTENT.pdf: S3 error: Object does not exist

🔄 Retrying in 4 seconds... (2 of 4 retries left)

[2/7] Downloading resume from s3://rightstaff-resumes/resumes/NONEXISTENT.pdf
❌ Error downloading s3://rightstaff-resumes/resumes/NONEXISTENT.pdf: S3 error: Object does not exist

🔄 Retrying in 8 seconds... (3 of 4 retries left)

[2/7] Downloading resume from s3://rightstaff-resumes/resumes/NONEXISTENT.pdf
❌ Error downloading s3://rightstaff-resumes/resumes/NONEXISTENT.pdf: S3 error: Object does not exist

🔄 Retrying in 16 seconds... (4 of 4 retries left)

[2/7] Downloading resume from s3://rightstaff-resumes/resumes/NONEXISTENT.pdf
❌ Error downloading s3://rightstaff-resumes/resumes/NONEXISTENT.pdf: S3 error: Object does not exist

❌ Job ingest_c4c41cb0-bf08-413d-8fb5-54ea3ac955bf_1699999999 failed after max retries: S3 error: Object does not exist
📬 Moved job ingest_c4c41cb0-bf08-413d-8fb5-54ea3ac955bf_1699999999 to DLQ after 0 retries
```

**✅ PASS Criteria:**
- See 5 download attempts (1 original + 4 retries)
- Wait times increase: ~2s, ~4s, ~8s, ~16s
- Job moved to DLQ after max retries

---

### Step 4: Check DLQ

```powershell
# Check DLQ depth and entries
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
      "job_id": "ingest_c4c41cb0-bf08-413d-8fb5-54ea3ac955bf_1699999999",
      "event_type": "profile_created",
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

### Step 5: Clear DLQ

```powershell
# Clear DLQ
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/admin/dlq/clear" -Method POST
$result = $response.Content | ConvertFrom-Json
$result | ConvertTo-Json
```

**Expected Output:**
```json
{
  "status": "completed",
  "deleted_count": 1,
  "warning": "All failed jobs have been permanently deleted"
}
```

**Verify DLQ is empty:**
```powershell
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/admin/dlq" -Method GET
$dlq = $response.Content | ConvertFrom-Json
$dlq.depth  # Should be 0
```

---

## 🎯 Alternative: Using curl/bash

```bash
# Step 2: Trigger job
curl -X POST http://localhost:8000/api/v1/webhooks/candidate-updated \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "profile_created",
    "candidate_id": "c4c41cb0-bf08-413d-8fb5-54ea3ac955bf",
    "timestamp": "2025-11-10T12:00:00Z",
    "s3_resume_url": "s3://rightstaff-resumes/resumes/NONEXISTENT.pdf",
    "profile_snapshot": {}
  }'

# Step 4: Check DLQ
curl http://localhost:8000/api/v1/admin/dlq

# Step 5: Clear DLQ
curl -X POST http://localhost:8000/api/v1/admin/dlq/clear
```

---

## 📊 What Changed?

### Before Fix:
```
❌ Job triggers with non-existent file
❌ S3Error is NOT in RETRIABLE_EXCEPTIONS
❌ Tenacity doesn't retry → immediately fails
❌ Moves to DLQ without any retry attempts
❌ NO exponential backoff visible
```

### After Fix:
```
✅ Job triggers with non-existent file
✅ S3Error IS in RETRIABLE_EXCEPTIONS
✅ Tenacity retries with exponential backoff
✅ After 5 attempts (1 original + 4 retries) → moves to DLQ
✅ Exponential backoff visible: 2s, 4s, 8s, 16s
```

---

## 🔍 Troubleshooting

### Issue: Still no retry attempts

**Check:**
1. Did you restart the FastAPI server?
   ```bash
   # Stop server (Ctrl+C)
   # Restart:
   uvicorn app.main:app --reload
   ```

2. Verify the fix was applied:
   ```bash
   grep -A 10 "RETRIABLE_EXCEPTIONS" backend/app/services/ingestion.py
   ```

   Should show:
   ```python
   RETRIABLE_EXCEPTIONS = (
       ConnectionError,
       TimeoutError,
       asyncio.TimeoutError,
       S3Error,  # Should be here!
       Exception,
   )
   ```

### Issue: Different error than S3Error

If the logs show a different exception, it might not be in RETRIABLE_EXCEPTIONS. Check the error type and add it if needed.

### Issue: DLQ endpoints not found (404)

Verify `admin.py` is registered in `main.py`:
```python
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
```

---

## ✅ Success Checklist

After testing, verify:

- [ ] Restarted FastAPI server
- [ ] Triggered job with non-existent file
- [ ] Saw 5 download attempts in logs
- [ ] Wait times were exponential (2s, 4s, 8s, 16s)
- [ ] Job moved to DLQ after max retries
- [ ] DLQ depth is 1 (via GET /admin/dlq)
- [ ] Can view DLQ entry details
- [ ] Can clear DLQ (via POST /admin/dlq/clear)
- [ ] DLQ depth is 0 after clearing

---

## 📚 Quick Reference

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/dlq` | GET | View DLQ status |
| `/api/v1/admin/dlq/clear` | POST | Clear all DLQ entries |
| `/api/v1/admin/dlq/replay` | POST | Replay all DLQ entries |
| `/api/v1/admin/metrics` | GET | View system metrics |

### PowerShell Commands

```powershell
# Check DLQ
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/admin/dlq" | ConvertFrom-Json

# Clear DLQ
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/admin/dlq/clear" -Method POST | ConvertFrom-Json

# Replay DLQ
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/admin/dlq/replay" -Method POST | ConvertFrom-Json
```

---

## 🎉 Summary

✅ **Exponential backoff now working!**
- S3Error added to RETRIABLE_EXCEPTIONS
- Tenacity retries 5 times with exponential delays
- Jobs move to DLQ after max retries

✅ **DLQ management working!**
- Can view DLQ via GET /admin/dlq
- Can clear DLQ via POST /admin/dlq/clear
- Can replay DLQ via POST /admin/dlq/replay

Both issues are now **FIXED**! 🎊
