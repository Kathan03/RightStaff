# ============================================================
# Complete End-to-End Workflow: Create Compatible Candidate
# ============================================================
# This script creates a candidate that WILL be selected for ranking
# by ensuring all requirements match (skills, experience, location)
# ============================================================

Write-Host "`n" -NoNewline
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  RightStaff E2E Test: Create & Rank Compatible Candidate" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

# ============================================================
# STEP 1: Create a resume file with matching skills
# ============================================================

Write-Host "STEP 1: Creating resume file..." -ForegroundColor Yellow

$resumeContent = @"
JANE SMITH
Senior Python Developer

Email: jane.smith@example.com
Phone: (555) 123-4567
Location: San Francisco, CA

PROFESSIONAL SUMMARY
Highly skilled Python engineer with 5 years of experience building scalable
web applications using FastAPI, PostgreSQL, and modern cloud technologies.
Proven track record of delivering high-quality software in fast-paced environments.

TECHNICAL SKILLS
- Languages: Python (Expert), JavaScript, SQL
- Frameworks: FastAPI, Django, Flask, React
- Databases: PostgreSQL, Redis, MongoDB
- DevOps: Docker, Kubernetes, AWS, CI/CD
- Tools: Git, Pytest, SQLAlchemy

WORK EXPERIENCE
Senior Python Developer | TechCorp Inc | 2020-Present
- Built RESTful APIs using FastAPI serving 100K+ requests/day
- Designed microservices architecture with Docker and Kubernetes
- Optimized database queries reducing latency by 50%
- Mentored junior developers and conducted code reviews

Python Developer | StartupXYZ | 2019-2020
- Developed web applications using Django and PostgreSQL
- Implemented automated testing with 90% code coverage
- Collaborated with frontend team using React

EDUCATION
B.S. Computer Science | University of California | 2019
"@

# Save resume to file
$resumePath = ".\jane_smith_resume.txt"
$resumeContent | Out-File -FilePath $resumePath -Encoding UTF8 -NoNewline
Write-Host "✅ Created resume file: $resumePath`n" -ForegroundColor Green

# ============================================================
# STEP 2: Create job with compatible requirements
# ============================================================

Write-Host "STEP 2: Creating job..." -ForegroundColor Yellow
$jobBody = @{
    title = "Senior Python Engineer"
    description = "Build scalable AI systems with FastAPI, PostgreSQL, and Qdrant. Work on cutting-edge ranking algorithms."
    department = "Engineering"
    location = "San Francisco, CA (Hybrid)"
    required_skills = @("Python", "FastAPI", "PostgreSQL", "Docker")
    must_have_skills = @("Python", "FastAPI")  # Jane has both!
    min_years_experience = 3
    max_years_experience = 10  # Jane has 5 years ✅
    work_arrangement = "hybrid"
    employment_type = "full-time"
} | ConvertTo-Json

try {
    $jobResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/jobs" `
        -Method Post `
        -ContentType "application/json" `
        -Body $jobBody

    $JOB_ID = $jobResponse.job_id
    Write-Host "✅ Job created: $JOB_ID" -ForegroundColor Green
    Write-Host "   Title: $($jobResponse.title)`n"
} catch {
    Write-Host "❌ Failed to create job: $_" -ForegroundColor Red
    Write-Host "   Make sure the backend is running on localhost:8000`n"
    exit 1
}

# ============================================================
# STEP 3: Upload resume (anonymous)
# ============================================================

Write-Host "STEP 3: Uploading resume..." -ForegroundColor Yellow
try {
    $uploadResponse = curl.exe -X POST "http://localhost:8000/api/v1/candidates/upload-resume" `
        -F "file=@$resumePath" `
        -s | ConvertFrom-Json

    $TEMP_ID = $uploadResponse.temp_id
    Write-Host "✅ Resume uploaded and parsed" -ForegroundColor Green
    Write-Host "   temp_id: $TEMP_ID"
    Write-Host "   Parsed name: $($uploadResponse.parsed_data.full_name)"
    Write-Host "   Parsed email: $($uploadResponse.parsed_data.email)"
    Write-Host "   Parsed skills: $($uploadResponse.parsed_data.skills -join ', ')`n"
} catch {
    Write-Host "❌ Failed to upload resume: $_" -ForegroundColor Red
    exit 1
}

# ============================================================
# STEP 4: Review parsed data (optional verification)
# ============================================================

Write-Host "STEP 4: Verifying parsed data..." -ForegroundColor Yellow
try {
    $parsedData = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/candidates/parsed/$TEMP_ID"
    Write-Host "✅ Parsed data retrieved (status: $($parsedData.status))`n" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Could not retrieve parsed data (continuing anyway)`n" -ForegroundColor Yellow
}

# ============================================================
# STEP 5: Create candidate with form submission
# ============================================================

Write-Host "STEP 5: Creating candidate..." -ForegroundColor Yellow
$candidateBody = @{
    temp_id = $TEMP_ID
    full_name = "Jane Smith"
    email = "jane.smith@example.com"
    phone = "(555) 123-4567"
    years_experience = 5.0
    professional_summary = "Highly skilled Python engineer with 5 years of experience building scalable web applications using FastAPI, PostgreSQL, and modern cloud technologies."
    location = "San Francisco, CA"
} | ConvertTo-Json

try {
    $candidateResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/candidates/" `
        -Method Post `
        -ContentType "application/json" `
        -Body $candidateBody

    $CANDIDATE_ID = $candidateResponse.candidate_id
    Write-Host "✅ Candidate created: $CANDIDATE_ID" -ForegroundColor Green
    Write-Host "   Processing job: $($candidateResponse.processing_job_id)`n"
} catch {
    Write-Host "❌ Failed to create candidate: $_" -ForegroundColor Red
    exit 1
}

# ============================================================
# STEP 6: Wait for embeddings to be generated
# ============================================================

Write-Host "STEP 6: Waiting for full ingestion (embeddings)..." -ForegroundColor Yellow
Write-Host "   This takes ~15 seconds for resume parsing and embedding generation..."
Start-Sleep -Seconds 15
Write-Host "✅ Ingestion complete`n" -ForegroundColor Green

# ============================================================
# STEP 7: Candidate applies to job
# ============================================================

Write-Host "STEP 7: Submitting job application..." -ForegroundColor Yellow
try {
    $applicationResponse = curl.exe -X POST "http://localhost:8000/api/v1/jobs/$JOB_ID/apply?candidate_id=$CANDIDATE_ID" `
        -H "Content-Type: application/json" `
        -s | ConvertFrom-Json

    Write-Host "✅ Application submitted" -ForegroundColor Green
    Write-Host "   Application ID: $($applicationResponse.application_id)"
    Write-Host "   Status: $($applicationResponse.status)`n"
} catch {
    Write-Host "❌ Failed to submit application: $_" -ForegroundColor Red
    exit 1
}

# ============================================================
# STEP 8: Rank candidates
# ============================================================

Write-Host "STEP 8: Ranking candidates for the job..." -ForegroundColor Yellow
$rankingBody = @{
    use_cache = $false
} | ConvertTo-Json

try {
    $rankingResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/jobs/$JOB_ID/rank_full" `
        -Method Post `
        -ContentType "application/json" `
        -Body $rankingBody

    Write-Host "✅ Ranking complete!`n" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "                    RANKING RESULTS" -ForegroundColor Cyan
    Write-Host "============================================================`n" -ForegroundColor Cyan
    Write-Host "Total candidates: $($rankingResponse.metadata.total_candidates)"
    Write-Host "High confidence: $($rankingResponse.metadata.high_confidence)"
    Write-Host "Medium confidence: $($rankingResponse.metadata.medium_confidence)"
    Write-Host "Low confidence: $($rankingResponse.metadata.low_confidence)`n"

    if ($rankingResponse.ranked_candidates.Count -gt 0) {
        $topCandidate = $rankingResponse.ranked_candidates[0]
        Write-Host "🏆 TOP CANDIDATE:" -ForegroundColor Green
        Write-Host "   Candidate ID: $($topCandidate.candidate_id)"
        Write-Host "   Final Score: $([math]::Round($topCandidate.final_score * 100, 1))%" -ForegroundColor Yellow
        Write-Host "   Band: $($topCandidate.band)" -ForegroundColor Yellow
        Write-Host "   Confidence: $([math]::Round($topCandidate.confidence * 100, 1))%" -ForegroundColor Yellow
        Write-Host "   Summary: $($topCandidate.summary)`n"

        Write-Host "   Match Reasons:" -ForegroundColor Cyan
        foreach ($reason in $topCandidate.reasons) {
            Write-Host "   ✓ $reason" -ForegroundColor Gray
        }

        Write-Host "`n   Score Breakdown:" -ForegroundColor Cyan
        Write-Host "   • Dense (semantic similarity): $([math]::Round($topCandidate.score_breakdown.dense * 100, 1))%" -ForegroundColor Gray
        Write-Host "   • Structured (experience/skills): $([math]::Round($topCandidate.score_breakdown.structured * 100, 1))%" -ForegroundColor Gray
        Write-Host "   • Profile completeness: $([math]::Round($topCandidate.score_breakdown.completeness * 100, 1))%" -ForegroundColor Gray

        # Verify it's Jane Smith
        if ($topCandidate.candidate_id -eq $CANDIDATE_ID) {
            Write-Host "`n✅ SUCCESS! Jane Smith was ranked and selected!" -ForegroundColor Green -BackgroundColor Black
        } else {
            Write-Host "`n⚠️  Warning: A different candidate was ranked #1" -ForegroundColor Yellow
            Write-Host "   Expected: $CANDIDATE_ID"
            Write-Host "   Got: $($topCandidate.candidate_id)"
        }
    } else {
        Write-Host "❌ No candidates were ranked" -ForegroundColor Red
        Write-Host "   Possible reasons:"
        Write-Host "   • No candidates passed SQL gates (skills/experience/location)"
        Write-Host "   • No applications exist for this job"
        Write-Host "   • Embeddings not yet generated (wait longer)"
    }

    Write-Host "`n============================================================`n" -ForegroundColor Cyan

} catch {
    Write-Host "❌ Failed to rank candidates: $_" -ForegroundColor Red
    exit 1
}

# ============================================================
# Cleanup
# ============================================================

Remove-Item -Path $resumePath -ErrorAction SilentlyContinue
Write-Host "✅ Test complete! Resume file cleaned up.`n" -ForegroundColor Green

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  QUICK REFERENCE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Job ID: $JOB_ID" -ForegroundColor White
Write-Host "Candidate ID: $CANDIDATE_ID" -ForegroundColor White
Write-Host ""
