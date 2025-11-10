# 🚀 Quick Start: Add Dummy Data

## Option 1: Fresh Start (Recommended)
```powershell
# Navigate to docker folder
cd docker

# Stop and remove database (⚠️ deletes all data)
docker-compose down -v

# Start fresh with dummy data automatically loaded
docker-compose up -d postgres

# Watch the magic happen
docker logs rightstaff-postgres -f
```
✅ **Result**: 10 candidates + 5 jobs + 7 applications automatically loaded!

---

## Option 2: Add to Existing Database
```powershell
# Navigate to project root
cd C:\Users\katha\OneDrive - The Pennsylvania State University\Documents\Desktop\RightStaff

# Execute the dummy data script
docker exec -i rightstaff-postgres psql -U right_staff -d rightstaff < database\scripts\05_dummy_data.sql
```
✅ **Result**: Dummy data added without losing existing data!

---

## Verify It Worked
```powershell
# Connect to database
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff

# Inside psql, run:
SET search_path = rightstaff, public;
SELECT COUNT(*) FROM candidate;  -- Should show 11 (1 original + 10 new)
SELECT full_name FROM candidate; -- See all candidates
\q  # Exit
```

---

## What You Got
- 👤 **10 New Candidates** (diverse roles and experience levels)
- 💼 **5 Job Postings** (various departments and locations)
- 📝 **7 Applications** (candidates applied to different jobs)
- 🎯 **15+ Skills** (Python, Java, React, AWS, etc.)
- ❤️ **6 Interests** (AI, Blockchain, HealthTech, etc.)

---

## Candidates Added
1. Sarah Johnson - Full Stack Developer (5 yrs)
2. Michael Chen - Data Scientist (7.5 yrs)
3. Emily Rodriguez - DevOps Engineer (6 yrs)
4. David Kim - Java Backend Developer (8 yrs)
5. Jessica Williams - Product Manager (9 yrs)
6. Robert Martinez - UI/UX Designer (4.5 yrs)
7. Amanda Lee - Frontend Developer (3.5 yrs)
8. Christopher Brown - Blockchain Developer (5.5 yrs)
9. Nina Patel - Database Administrator (10 yrs)
10. James Thompson - Mobile Developer (6.5 yrs)

---

## File Locations
```
📁 RightStaff/
├── 📁 database/
│   └── 📁 scripts/
│       └── 📄 05_dummy_data.sql ← The magic file!
├── 📁 docker/
│   └── 📄 docker-compose.yml ← Defines auto-load behavior
└── 📁 data/
    └── 📁 postgres/ ← Physical data storage
```

---

## Need More Details?
📖 Read the full guide: **DUMMY-DATA-SETUP-GUIDE.md**

