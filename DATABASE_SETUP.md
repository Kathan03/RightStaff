# Database Setup & Data Management Guide

## Overview

This document explains how to initialize the database and manage test data for the RightStaff application.

---

## Architecture

The application uses **SQL scripts** for schema creation and **Python scripts** for data management:

| Component | Method | Purpose |
|-----------|--------|---------|
| **Schema** | SQL scripts (`database/scripts/01_schema.sql`) | Create tables, enums, constraints |
| **Data** | Python (`populate_dummy_data.py`) | Insert test data into PostgreSQL, Qdrant, MinIO |
| **Cleanup** | Python (`clear_all_data.py`) | Delete all data from all systems |

---

## Complete Setup Process (Step-by-Step)

### **Prerequisites**

Ensure Docker services are running:
```bash
cd docker
docker-compose up -d
# This starts: PostgreSQL, Qdrant, Redis, MinIO
```

Verify services are healthy:
```bash
docker ps
# All containers should show "Up" status
```

---

### **Step 1: Create Database Schema**

Use SQL scripts to create all tables:

```bash
cd database

# Run schema creation
psql -U right_staff -h localhost -p 5432 -d rightstaff -f scripts/01_schema.sql
```

**What this creates:**
- `rightstaff` schema
- 20 tables (candidate, job, skill, etc.)
- Enums (job_status_enum)
- Foreign key constraints
- Indexes

---

### **Step 2: Populate with Dummy Data**

Run the Python script to insert test data:

```bash
cd ../backend
python populate_dummy_data.py
```

**What this does:**
1. **PostgreSQL**:
   - Creates 8 diverse candidates (Sarah Chen, Michael Rodriguez, etc.)
   - Creates 49 skills (Python, Java, AWS, etc.)
   - Links candidates to skills with proficiency levels

2. **Qdrant** (Vector Database):
   - Generates embeddings for all 8 candidate profiles
   - Stores 384-dimensional vectors for semantic search

3. **MinIO** (File Storage):
   - Uploads 5 resume files from `resumes/` directory
   - Creates database records linking candidates to S3 URLs
   - **Note**: 3 candidates (David Kim, Ana Martinez, Robert Johnson) intentionally have NO resumes for testing edge cases

4. **Candidate-Resume Mapping**:
   | Candidate | Has Resume? | Purpose |
   |-----------|-------------|---------|
   | Sarah Chen | ✅ Yes | Full profile testing |
   | Michael Rodriguez | ✅ Yes | Full profile testing |
   | Emily Watson | ✅ Yes | Full profile testing |
   | Priya Patel | ✅ Yes | Full profile testing |
   | James Thompson | ✅ Yes | Full profile testing |
   | David Kim | ❌ No | Test candidate without resume |
   | Ana Martinez | ❌ No | Test candidate without resume |
   | Robert Johnson | ❌ No | Test candidate without resume |

---

### **Step 3: Verify Setup**

Check that data was created correctly:

```bash
# Check database contents
python check_database.py

# Run comprehensive diagnostic
python diagnose_all.py
```

**Expected output:**
- ✅ PostgreSQL: 8 candidates, 49 skills, 55 candidate-skill mappings
- ✅ Qdrant: 8 vectors
- ✅ Redis: Healthy
- ✅ Embedding service: Working

---

### **Step 4: Test the System**

Run end-to-end test of the ranking pipeline:

```bash
# Ensure backend is running
uvicorn app.main:app --reload

# In another terminal, run tests
python test_day4_e2e_adaptive.py
```

---

## Data Management Commands

### **Clear All Data** (Fresh Start)

```bash
python clear_all_data.py
```

**What this deletes:**
- ✅ PostgreSQL: All candidates, jobs, skills
- ✅ Qdrant: All vector embeddings
- ✅ Redis: All cached rankings
- ✅ MinIO: All uploaded resumes

**Safety:** 3-second countdown before deletion (Ctrl+C to cancel)

---

### **Repopulate Data**

```bash
python populate_dummy_data.py
```

**Note:** This assumes tables already exist (from Step 1). If tables are missing, re-run the SQL schema script first.

---

## File Structure

```
RightStaff/
├── database/
│   └── scripts/
│       ├── 00_rollback.sql          # Drop all tables
│       └── 01_schema.sql            # Create all tables ⭐ PRIMARY SCHEMA
│
├── backend/
│   ├── populate_dummy_data.py       # ⭐ Create test data
│   ├── clear_all_data.py            # ⭐ Delete all data
│   ├── check_database.py            # Verify data
│   ├── diagnose_all.py              # System health check
│   ├── test_day4_e2e_adaptive.py    # E2E ranking tests
│   ├── test_day4_quick.py           # Quick service tests
│   └── test_api_quick.py            # API connectivity test
│
└── resumes/                          # ⭐ Resume files for upload
    ├── sarah_chen_resume.txt
    ├── michael_rodriguez_resume.txt
    ├── emily_watson_resume.txt
    ├── priya_patel_resume.txt
    └── james_thompson_resume.txt
```

---

## Common Scenarios

### **Scenario 1: First-time Setup**

```bash
# 1. Start services
cd docker && docker-compose up -d

# 2. Create schema
cd ../database
psql -U right_staff -h localhost -p 5432 -d rightstaff -f scripts/01_schema.sql

# 3. Populate data
cd ../backend
python populate_dummy_data.py

# 4. Verify
python diagnose_all.py
```

---

### **Scenario 2: Reset Everything**

```bash
cd backend

# Clear all data
python clear_all_data.py

# Repopulate
python populate_dummy_data.py
```

---

### **Scenario 3: Data Corruption / Schema Changes**

```bash
# 1. Drop everything
cd database
psql -U right_staff -h localhost -p 5432 -d rightstaff -f scripts/00_rollback.sql

# 2. Recreate schema
psql -U right_staff -h localhost -p 5432 -d rightstaff -f scripts/01_schema.sql

# 3. Repopulate data
cd ../backend
python populate_dummy_data.py
```

---

## Troubleshooting

### **Problem: "relation does not exist"**

**Cause:** Tables haven't been created yet

**Solution:**
```bash
cd database
psql -U right_staff -h localhost -p 5432 -d rightstaff -f scripts/01_schema.sql
```

---

### **Problem: "No candidates in database"**

**Cause:** Data hasn't been populated

**Solution:**
```bash
cd backend
python populate_dummy_data.py
```

---

### **Problem: "Qdrant collection 'candidates_v1' does not exist"**

**Cause:** Vector store hasn't been initialized

**Solution:**
```bash
cd backend
python populate_dummy_data.py  # This creates the collection automatically
```

---

### **Problem: "Resume file not found"**

**Cause:** Resume files missing from `resumes/` directory

**Solution:**
Resume files already exist in `resumes/` directory. If missing, they're auto-created by populate_dummy_data.py.

---

## Why This Approach?

### **SQL Scripts for Schema**
✅ Production-ready
✅ Version controlled
✅ DBA-friendly
✅ No ORM abstraction layer

### **Python Scripts for Data**
✅ Handles multiple systems (PostgreSQL + Qdrant + MinIO)
✅ Easy to customize test data
✅ Validates connections
✅ Provides detailed feedback

---

## Quick Reference

| Task | Command |
|------|---------|
| Create schema | `psql -U right_staff -h localhost -p 5432 -d rightstaff -f database/scripts/01_schema.sql` |
| Populate data | `python backend/populate_dummy_data.py` |
| Clear data | `python backend/clear_all_data.py` |
| Check data | `python backend/check_database.py` |
| System health | `python backend/diagnose_all.py` |
| Test ranking | `python backend/test_day4_e2e_adaptive.py` |
| Drop schema | `psql -U right_staff -h localhost -p 5432 -d rightstaff -f database/scripts/00_rollback.sql` |

---

## Changes Made

### **Deleted Files** (Redundant)
- ❌ `init_db.py` - Replaced by SQL scripts
- ❌ `add_test_candidate.py` - Replaced by populate_dummy_data.py
- ❌ `diagnose_qdrant.py` - Covered by diagnose_all.py
- ❌ `populate_qdrant.py` - Integrated into populate_dummy_data.py
- ❌ `test_day4_e2e.py` - Replaced by test_day4_e2e_adaptive.py

### **Created Files**
- ✅ `resumes/` - Directory with 5 sample resume files
- ✅ `DATABASE_SETUP.md` - This documentation

### **Modified Files**
- ✅ `populate_dummy_data.py` - Now uploads resumes to MinIO
- ✅ `clear_all_data.py` - Clears MinIO resumes

### **Code Changes**
- ✅ Added `CandidateResume` import
- ✅ Added `s3_client` import
- ✅ Added `populate_minio()` function
- ✅ Updated summary statistics

---

## Need Help?

1. **Check logs**: `docker logs <container_name>`
2. **Verify connections**: `python backend/diagnose_all.py`
3. **Database issues**: Re-run schema script
4. **Data issues**: Re-run populate script

---

**Last Updated:** 2025-11-12
