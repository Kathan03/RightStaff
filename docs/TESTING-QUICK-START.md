# 🧪 Quick Testing Guide - RightStaff Ranking Fixes

This guide helps you quickly test that all fixes are working correctly.

---

## ✅ Prerequisites

1. FastAPI server running: `uvicorn app.main:app --reload`
2. All Docker services running (PostgreSQL, Redis, Qdrant, MinIO)
3. PowerShell or bash terminal

---

## 🚀 Quick Tests (PowerShell)

### Test 1: Create Job with Skills Only (Should Find Candidates)

```powershell
# Create job
$body = @{
    title = "JavaScript Developer"
    description = "Looking for JS developers"
    required_skills = @("JavaScript")
    must_have_skills = @("JavaScript")
    min_years_experience = $null
    max_years_experience = $null
    location = $null
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/jobs/" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"

$job = $response.Content | ConvertFrom-Json
$jobId = $job.job_id
Write-Host "Created job: $jobId"

# Rank candidates
$rankBody = @{
    job_id = $jobId
    use_cache = $false
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/jobs/rank" `
    -Method POST `
    -Body $rankBody `
    -ContentType "application/json"

$rankResult = $response.Content | ConvertFrom-Json
$rankResult | ConvertTo-Json -Depth 10
```

**Expected Result:** ✅
- Status: "completed"
- total_qualified: 8 (or similar positive number)
- NO "Decimal is not JSON serializable" error

---

### Test 2: Test with Decimal Years (Critical Test)

```powershell
# Create job with decimal years
$body = @{
    title = "Senior Python Engineer"
    description = "Senior role"
    required_skills = @("Python")
    must_have_skills = @("Python")
    min_years_experience = 2.5
    max_years_experience = 8.75
    location = $null
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/jobs/" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"

$job = $response.Content | ConvertFrom-Json
$jobId = $job.job_id

# Rank candidates
$rankBody = @{
    job_id = $jobId
    use_cache = $false
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/jobs/rank" `
    -Method POST `
    -Body $rankBody `
    -ContentType "application/json"

$rankResult = $response.Content | ConvertFrom-Json
$rankResult | ConvertTo-Json -Depth 10

# Get cached rankings to verify Decimal conversion
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/jobs/$jobId/rankings" `
    -Method GET

$cachedData = $response.Content | ConvertFrom-Json
Write-Host "`nCached Data Gates:"
$cachedData.gates_applied | ConvertTo-Json -Depth 10
```

**Expected Result:** ✅
- Ranking completes successfully
- `gates_applied.min_years` shows `2.5` (as float)
- `gates_applied.max_years` shows `8.75` (as float)
- NO Decimal serialization error

---

### Test 3: Original Failing Test (Now Fixed)

```powershell
# This is the EXACT test from your issue report
$jobId = "5d217044-0fa9-485e-aa2c-4f98a9e1be6e"  # Use real job ID from database

$body = @{
    job_id = $jobId
    use_cache = $false
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/jobs/rank" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"

$rankingResult = $response.Content | ConvertFrom-Json
$rankingResult | ConvertTo-Json -Depth 10
```

**Expected Result:** ✅
- Completes without error (might return 0 candidates if location doesn't match, but NO error!)

---

## 🚀 Quick Tests (curl/bash)

### Test 1: JavaScript Job

```bash
# Create job
curl -X POST http://localhost:8000/api/v1/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "JavaScript Developer",
    "description": "JS role",
    "required_skills": ["JavaScript"],
    "must_have_skills": ["JavaScript"]
  }'

# Copy job_id from response, then rank:
JOB_ID="<paste-job-id>"

curl -X POST http://localhost:8000/api/v1/jobs/rank \
  -H "Content-Type: application/json" \
  -d "{\"job_id\": \"$JOB_ID\", \"use_cache\": false}"
```

---

### Test 2: Decimal Years

```bash
# Create job
curl -X POST http://localhost:8000/api/v1/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior Python Engineer",
    "description": "Senior role",
    "required_skills": ["Python"],
    "must_have_skills": ["Python"],
    "min_years_experience": 2.5,
    "max_years_experience": 8.75
  }'

# Rank
JOB_ID="<paste-job-id>"
curl -X POST http://localhost:8000/api/v1/jobs/rank \
  -H "Content-Type: application/json" \
  -d "{\"job_id\": \"$JOB_ID\", \"use_cache\": false}"

# Verify cache
curl http://localhost:8000/api/v1/jobs/$JOB_ID/rankings | python -m json.tool
```

---

## ✅ Success Indicators

### You'll know it's working if:

1. **No Error Messages:**
   - ❌ OLD: "Error ranking candidates: Object of type Decimal is not JSON serializable"
   - ✅ NEW: "status": "completed"

2. **Proper Status Code:**
   - ❌ OLD: `500 Internal Server Error`
   - ✅ NEW: `200 OK`

3. **Decimal Values as Float:**
   ```json
   {
     "gates_applied": {
       "min_years": 2.5,     // ✅ Float, not Decimal
       "max_years": 8.75     // ✅ Float, not Decimal
     }
   }
   ```

4. **Candidates Found (when filters match):**
   - JavaScript job: ~8 candidates
   - Python job: ~7 candidates (varies by experience filter)

---

## �� Troubleshooting

### Issue: Still getting Decimal error
**Fix:** Make sure you restarted the FastAPI server after applying fixes:
```bash
# Stop server (Ctrl+C)
# Restart:
cd backend
uvicorn app.main:app --reload
```

### Issue: 0 candidates found
**Possible Reasons:**
1. Location doesn't match any candidates (check: `docker exec rightstaff-postgres psql -U right_staff -d rightstaff -c "SELECT DISTINCT city FROM rightstaff.candidate_contact;"`)
2. No candidates with required skills (check: `docker exec rightstaff-postgres psql -U right_staff -d rightstaff -c "SELECT name FROM rightstaff.skill;"`)
3. Years filter too strict (check: `docker exec rightstaff-postgres psql -U right_staff -d rightstaff -c "SELECT MIN(years_experience), MAX(years_experience) FROM rightstaff.candidate;"`)

**This is NOT an error** - it's correct behavior when no candidates match ALL filters (AND logic).

### Issue: Job not found (404)
**Fix:** Make sure you're using the correct job_id from the creation response.

---

## 📊 Database Verification

### Check Available Skills:
```bash
docker exec rightstaff-postgres psql -U right_staff -d rightstaff \
  -c "SELECT s.name, COUNT(cs.candidate_id) FROM rightstaff.skill s LEFT JOIN rightstaff.candidate_skill cs ON s.id = cs.skill_id GROUP BY s.name ORDER BY COUNT DESC LIMIT 10;"
```

### Check Available Locations:
```bash
docker exec rightstaff-postgres psql -U right_staff -d rightstaff \
  -c "SELECT city, COUNT(*) FROM rightstaff.candidate_contact GROUP BY city;"
```

### Check Candidates:
```bash
docker exec rightstaff-postgres psql -U right_staff -d rightstaff \
  -c "SELECT COUNT(*) as total FROM rightstaff.candidate;"
```

---

## 🎯 What Was Fixed

| Issue | Status | Fix |
|-------|--------|-----|
| Decimal JSON serialization error | ✅ FIXED | Convert Decimal to float before json.dumps() |
| Unused conversion code | ✅ CLEANED | Removed unnecessary convert_decimals_to_flats() |
| SQL gating logic | ✅ VERIFIED | Working correctly (AND logic) |

---

## 📚 Next Steps

After verifying fixes work:
1. ✅ Decimal serialization fixed
2. ✅ SQL gating verified
3. 📝 Move to Day 4 testing
4. 📝 Begin Day 5-8 semantic ranking implementation

---

## 📞 Need Help?

Check the comprehensive [FIX-REPORT.md](FIX-REPORT.md) for detailed analysis and additional troubleshooting.