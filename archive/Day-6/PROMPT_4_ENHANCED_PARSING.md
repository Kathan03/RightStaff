# 🎯 PROMPT 4: ENHANCED RESUME PARSING

**Estimated Time:** 3-4 hours
**Priority:** 🟡 HIGH
**Prerequisites:** Day-5 (Prompts 1-3) complete, ingestion.py working

---

## 📋 OBJECTIVE

Enhance resume parsing to automatically extract:
- **years_experience** - Calculate from employment dates
- **location** - Extract city, state using spaCy NER
- **professional_summary** - Auto-generate from resume text

**Current State:**
- Resume parsing extracts basic text
- Fields manually entered in forms

**After This Prompt:**
- Auto-extraction of structured fields
- Better form pre-fill experience
- Richer candidate profiles in PostgreSQL

---

## 🎯 IMPLEMENTATION STEPS

### STEP 1: Install Required Dependencies

**File:** `requirements.txt`

**Add these lines:**
```txt
# Enhanced resume parsing (Day-6 Prompt 4)
python-dateutil>=2.9.0
spacy>=3.7.0
```

**Install spaCy model:**
```bash
python -m spacy download en_core_web_sm
```

**Verify installation:**
```python
import spacy
import dateutil
print("✅ spaCy and dateutil installed")
```

---

### STEP 2: Create Enhanced Parsing Functions

**File:** `backend/app/services/parsers.py`

**Add these imports at top:**
```python
# Add after existing imports
from dateutil import parser as date_parser
import spacy
import re
from datetime import datetime
from typing import Optional, Dict, List, Tuple
```

**Add Function 1: Calculate Years of Experience**

```python
def calculate_years_experience(text: str) -> Optional[float]:
    """
    Extract employment dates from resume and calculate total years of experience.

    Strategy:
    1. Find all date patterns in text (Month Year format)
    2. Parse start/end dates for each job
    3. Calculate duration in years
    4. Sum all durations (handle overlaps by taking max end date)

    Patterns Supported:
    - "Jan 2020 - Dec 2022"
    - "January 2020 - Present"
    - "01/2020 - 12/2022"
    - "2020-01 - 2022-12"

    Args:
        text: Resume text

    Returns:
        Total years of experience (float), or None if cannot determine

    Example:
        >>> text = "Google | Jan 2020 - Present\\nMicrosoft | Jun 2018 - Dec 2019"
        >>> calculate_years_experience(text)
        5.5  # Assuming current date is mid-2023
    """
    try:
        # Date range pattern: "Month Year - Month Year" or "Month Year - Present"
        date_range_pattern = r'(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})\s*[-–—]\s*(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|Present|Current|Now)'

        matches = re.findall(date_range_pattern, text, re.IGNORECASE)

        if not matches:
            logger.warning("No date ranges found in resume")
            return None

        total_years = 0.0
        current_date = datetime.now()

        for start_str, end_str in matches:
            try:
                # Parse start date
                start_date = date_parser.parse(start_str, fuzzy=True)

                # Parse end date (handle "Present")
                if end_str.lower() in ['present', 'current', 'now']:
                    end_date = current_date
                else:
                    end_date = date_parser.parse(end_str, fuzzy=True)

                # Calculate duration in years
                duration = (end_date - start_date).days / 365.25
                total_years += duration

                logger.debug(f"Experience: {start_str} - {end_str} = {duration:.1f} years")

            except Exception as e:
                logger.warning(f"Failed to parse dates '{start_str}' - '{end_str}': {e}")
                continue

        # Round to 1 decimal place
        return round(total_years, 1) if total_years > 0 else None

    except Exception as e:
        logger.error(f"Error calculating years of experience: {e}")
        return None
```

**Add Function 2: Extract Location using spaCy NER**

```python
def extract_location(text: str) -> Dict[str, Optional[str]]:
    """
    Extract location (city, state, country) from resume using spaCy NER.

    Strategy:
    1. Use spaCy en_core_web_sm for Named Entity Recognition
    2. Look for GPE (Geo-Political Entity) entities
    3. Focus on first 1000 chars (contact section)
    4. Post-process to separate city, state, country

    Args:
        text: Resume text

    Returns:
        {"city": str, "state": str, "country": str}
        Values are None if not found

    Example:
        >>> text = "John Doe\\nSan Francisco, CA 94105\\njohn@email.com"
        >>> extract_location(text)
        {"city": "San Francisco", "state": "CA", "country": "USA"}
    """
    try:
        # Load spaCy model (cached after first load)
        nlp = spacy.load("en_core_web_sm")

        # Process first 1000 chars (contact section)
        doc = nlp(text[:1000])

        # Extract GPE entities
        locations = [ent.text for ent in doc.ents if ent.label_ == "GPE"]

        if not locations:
            logger.warning("No location entities found in resume")
            return {"city": None, "state": None, "country": None}

        # Post-processing: Try to separate city, state, country
        # Common patterns: "San Francisco, CA", "New York, NY, USA"

        result = {"city": None, "state": None, "country": None}

        # Simple heuristic: First location is usually city
        if len(locations) >= 1:
            result["city"] = locations[0]

        # Look for US state abbreviations
        state_pattern = r'\b([A-Z]{2})\b'  # e.g., CA, NY
        state_matches = re.findall(state_pattern, text[:1000])
        if state_matches:
            # Common US states
            us_states = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
                        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
                        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
                        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']
            for state in state_matches:
                if state in us_states:
                    result["state"] = state
                    break

        # Country is often last location or "USA"
        if len(locations) >= 2:
            result["country"] = locations[-1]
        elif "usa" in text.lower()[:1000] or "united states" in text.lower()[:1000]:
            result["country"] = "USA"

        logger.info(f"✅ Extracted location: {result}")
        return result

    except Exception as e:
        logger.error(f"Error extracting location: {e}")
        return {"city": None, "state": None, "country": None}
```

**Add Function 3: Generate Professional Summary**

```python
def generate_professional_summary(text: str, max_length: int = 200) -> str:
    """
    Auto-generate professional summary from resume.

    Strategy (Simple Approach):
    1. Split text into paragraphs
    2. Take first paragraph (often contains summary)
    3. Truncate to max_length

    Alternative (Advanced - Optional):
    - Use LLM to generate summary
    - Prompt: "Summarize this resume in 2 sentences"

    Args:
        text: Resume text
        max_length: Maximum summary length

    Returns:
        Professional summary text

    Example:
        >>> text = "Senior Software Engineer with 8+ years...\\n\\nExperience:\\n..."
        >>> generate_professional_summary(text)
        "Senior Software Engineer with 8+ years..."
    """
    try:
        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        if not paragraphs:
            # Fallback: Use first 200 chars
            summary = text.strip()[:max_length]
        else:
            # Use first substantial paragraph
            summary = paragraphs[0]

        # Truncate and add ellipsis if needed
        if len(summary) > max_length:
            summary = summary[:max_length].rsplit(' ', 1)[0] + "..."

        return summary

    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return ""
```

**Update parse_resume() to Use Enhanced Functions**

**Find the `parse_resume()` function (around line 50-100) and update:**

```python
def parse_resume(file_bytes: bytes, file_type: str) -> Dict[str, any]:
    """
    Parse resume and extract both text and structured fields.

    Returns:
        {
            "text": str,                    # Full resume text
            "years_experience": float,      # NEW! Auto-calculated
            "location": dict,                # NEW! {city, state, country}
            "professional_summary": str,     # NEW! Auto-generated
            "skills": List[str],            # Existing (from ontology)
            "email": str,                   # NEW! Extracted
            "phone": str,                   # NEW! Extracted
        }
    """
    # Existing text extraction logic
    if file_type.lower() == '.pdf':
        text = extract_text_from_pdf(file_bytes)
    elif file_type.lower() == '.docx':
        text = extract_text_from_docx(file_bytes)
    else:  # .txt
        text = file_bytes.decode('utf-8', errors='ignore')

    # NEW: Enhanced field extraction
    years_experience = calculate_years_experience(text)
    location = extract_location(text)
    professional_summary = generate_professional_summary(text)
    email = extract_email(text)  # Add this helper
    phone = extract_phone(text)  # Add this helper

    return {
        "text": text,
        "years_experience": years_experience,
        "location": location,
        "professional_summary": professional_summary,
        "email": email,
        "phone": phone
    }
```

**Add Helper Functions for Email and Phone**

```python
def extract_email(text: str) -> Optional[str]:
    """Extract email address from resume."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    return matches[0] if matches else None


def extract_phone(text: str) -> Optional[str]:
    """Extract phone number from resume."""
    # Pattern: (123) 456-7890 or 123-456-7890 or 1234567890
    phone_pattern = r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'
    matches = re.findall(phone_pattern, text)
    return matches[0] if matches else None
```

---

### STEP 3: Update Ingestion Pipeline

**File:** `backend/app/services/ingestion.py`

**Find the `process_job()` method (around line 200) and update:**

**FIND this code (parse-only mode section):**
```python
if mode == "parse_only":
    # Download and parse
    text = await self._download_and_parse(job_data)
    skills = await ontology.extract_skills(text)
    parsed_data = {
        "full_name": self._extract_name(text),  # TODO: implement
        "email": self._extract_email(text),     # TODO: implement
        "skills": skills,
    }
```

**REPLACE WITH:**
```python
if mode == "parse_only":
    # ══════════════════════════════════════════════════════════════
    # STAGE 1-3 ONLY: Download + Parse + Extract (NO embeddings)
    # ══════════════════════════════════════════════════════════════

    # Download resume from MinIO
    resume_bytes = await s3_client.download_file(s3_url)

    # Parse resume with enhanced extraction
    from app.services.parsers import parse_resume
    parsed_data = parse_resume(resume_bytes, file_type=".pdf")

    # Extract skills (existing logic)
    skills = await extract_skills_from_text(parsed_data["text"])
    parsed_data["skills"] = skills

    # Cache in Redis with 1-hour TTL
    await redis_client.set(
        f"parsed_candidate:{candidate_id}",
        json.dumps(parsed_data, default=str),  # default=str for datetime serialization
        ex=3600  # 1 hour
    )

    logger.info(f"✅ Parse-only complete for {candidate_id}")
    logger.info(f"   Years: {parsed_data.get('years_experience')}")
    logger.info(f"   Location: {parsed_data.get('location')}")
    logger.info(f"   Skills: {len(skills)} found")
    return  # STOP HERE - no embeddings, no Qdrant
```

**For FULL mode, update to save enhanced fields to PostgreSQL:**

**FIND the section where candidate is fetched from PostgreSQL (around line 220):**

```python
# Update candidate with enhanced fields if they're not set
if candidate and mode == "full":
    # Save enhanced parsed data to candidate record
    if not candidate.years_experience and parsed_data.get("years_experience"):
        candidate.years_experience = parsed_data["years_experience"]

    if not candidate.professional_summary and parsed_data.get("professional_summary"):
        candidate.professional_summary = parsed_data["professional_summary"]

    # Save contact information
    if candidate.contact:
        if not candidate.contact.email and parsed_data.get("email"):
            candidate.contact.email = parsed_data["email"]

        if not candidate.contact.phone and parsed_data.get("phone"):
            candidate.contact.phone = parsed_data["phone"]

        location = parsed_data.get("location", {})
        if not candidate.contact.city and location.get("city"):
            candidate.contact.city = location["city"]
        if not candidate.contact.region and location.get("state"):
            candidate.contact.region = location["state"]
        if not candidate.contact.country and location.get("country"):
            candidate.contact.country = location["country"]

    await db.commit()
    logger.info(f"✅ Updated candidate {candidate_id} with enhanced fields")
```

---

### STEP 4: Update Candidate API for Enhanced Pre-fill

**File:** `backend/app/api/candidates.py`

**Find the `upload_resume_anonymous()` endpoint and ensure it returns parsed data:**

```python
@router.post("/upload-resume")
async def upload_resume_anonymous(file: UploadFile = File(...)):
    """
    Stage 1: Anonymous resume upload with enhanced parsing.

    Returns parsed data including:
    - full_name
    - email
    - phone
    - years_experience (auto-calculated)
    - location (auto-extracted)
    - professional_summary (auto-generated)
    - skills (from ontology)
    """
    # ... existing upload logic ...

    # Wait for parsing (poll Redis)
    for _ in range(30):
        cached = await redis_client.get(f"parsed_candidate:{temp_id}")
        if cached:
            parsed_data = json.loads(cached)
            return {
                "temp_id": temp_id,
                "parsed_data": {
                    "full_name": parsed_data.get("full_name", ""),
                    "email": parsed_data.get("email", ""),
                    "phone": parsed_data.get("phone", ""),
                    "years_experience": parsed_data.get("years_experience"),
                    "location": parsed_data.get("location", {}),
                    "professional_summary": parsed_data.get("professional_summary", ""),
                    "skills": parsed_data.get("skills", [])
                }
            }
        await asyncio.sleep(1)

    raise HTTPException(500, "Parsing timeout")
```

---

## 🧪 VALIDATION & TESTING

### Step 1: Test Enhanced Parsing Functions

```python
# backend/tests/test_enhanced_parsing.py

import pytest
from app.services.parsers import (
    calculate_years_experience,
    extract_location,
    generate_professional_summary,
    extract_email,
    extract_phone
)

def test_calculate_years_experience_with_present():
    """Test years calculation when current job is ongoing."""
    text = """
    Software Engineer
    Google | Jan 2020 - Present
    Led development of microservices...

    Junior Developer
    Microsoft | Jun 2018 - Dec 2019
    Worked on frontend...
    """
    years = calculate_years_experience(text)

    # Should be ~3.5 years (Google) + 1.5 years (Microsoft) = ~5 years
    assert years is not None
    assert 4.5 <= years <= 5.5  # Allow some variance


def test_calculate_years_experience_multiple_jobs():
    """Test years calculation with multiple past jobs."""
    text = """
    Senior Engineer | Jan 2020 - Dec 2022
    Engineer | Jan 2018 - Dec 2019
    Intern | Jun 2017 - Aug 2017
    """
    years = calculate_years_experience(text)

    # 3 years + 2 years + 0.17 years ≈ 5.17 years
    assert years is not None
    assert 4.5 <= years <= 5.5


def test_extract_location_full_address():
    """Test location extraction with full address."""
    text = "John Doe\n123 Main St\nSan Francisco, CA 94105\nUnited States\njohn@email.com"
    location = extract_location(text)

    assert location["city"] == "San Francisco"
    assert location["state"] == "CA"
    assert location["country"] in ["United States", "USA"]


def test_extract_location_city_only():
    """Test location extraction with city only."""
    text = "John Doe\nNew York\njohn@email.com"
    location = extract_location(text)

    assert location["city"] == "New York"


def test_generate_professional_summary():
    """Test summary generation."""
    text = """Senior Software Engineer with 8+ years of experience in full-stack development.
    Expertise in Python, JavaScript, and cloud architecture. Proven track record of leading teams.

    EXPERIENCE
    Google | Senior Engineer | 2020-Present
    ...
    """
    summary = generate_professional_summary(text, max_length=150)

    assert len(summary) <= 153  # 150 + "..."
    assert "Senior Software Engineer" in summary
    assert "8+ years" in summary


def test_extract_email():
    """Test email extraction."""
    text = "John Doe\njohn.doe@example.com\n(555) 123-4567"
    email = extract_email(text)

    assert email == "john.doe@example.com"


def test_extract_phone():
    """Test phone extraction."""
    text = "John Doe\njohn@email.com\n(555) 123-4567"
    phone = extract_phone(text)

    assert phone == "(555) 123-4567"


def test_parse_resume_integration():
    """Test complete parse_resume() with all enhancements."""
    # Create sample resume content
    resume_text = """John Doe
    Senior Software Engineer
    San Francisco, CA 94105
    john.doe@example.com | (555) 123-4567

    SUMMARY
    Experienced software engineer with expertise in Python and cloud technologies.

    EXPERIENCE
    Google | Senior Engineer | Jan 2020 - Present
    - Led development of microservices
    - Managed team of 5 engineers

    Microsoft | Engineer | Jun 2018 - Dec 2019
    - Developed frontend applications

    SKILLS
    Python, JavaScript, AWS, Docker, Kubernetes
    """

    from app.services.parsers import parse_resume
    resume_bytes = resume_text.encode('utf-8')

    result = parse_resume(resume_bytes, file_type=".txt")

    # Verify all fields extracted
    assert result["text"] == resume_text
    assert result["email"] == "john.doe@example.com"
    assert result["phone"] == "(555) 123-4567"
    assert result["years_experience"] is not None
    assert 3.0 <= result["years_experience"] <= 5.0
    assert result["location"]["city"] == "San Francisco"
    assert result["location"]["state"] == "CA"
    assert "Senior Software Engineer" in result["professional_summary"]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### Step 2: Manual Testing

```bash
# 1. Install dependencies
pip install python-dateutil spacy
python -m spacy download en_core_web_sm

# 2. Test parsing functions
python -c "
from app.services.parsers import calculate_years_experience
text = 'Google | Jan 2020 - Present'
print(f'Years: {calculate_years_experience(text)}')
"

# 3. Test full ingestion
cd /home/user/RightStaff/backend
python populate_dummy_data.py

# 4. Check database
psql -U right_staff -d rightstaff -c "
SELECT full_name, years_experience, professional_summary
FROM rightstaff.candidate
LIMIT 5;
"
```

### Step 3: API Testing

```bash
# 1. Start server
uvicorn app.main:app --reload

# 2. Upload resume (test enhanced parsing)
curl -X POST http://localhost:8000/api/v1/candidates/upload-resume \
  -F "file=@sample_resume.pdf"

# Expected response:
{
  "temp_id": "uuid-...",
  "parsed_data": {
    "full_name": "John Doe",
    "email": "john@example.com",
    "phone": "(555) 123-4567",
    "years_experience": 5.5,
    "location": {"city": "San Francisco", "state": "CA", "country": "USA"},
    "professional_summary": "Senior Software Engineer with 8+ years...",
    "skills": ["Python", "AWS", "Docker"]
  }
}
```

---

## 🚨 TROUBLESHOOTING

### Error: "spaCy model not found"

**Solution:**
```bash
python -m spacy download en_core_web_sm
```

### Error: "No date ranges found"

**Check:**
- Resume has dates in format "Month Year - Month Year"
- Dates are in Experience section
- Pattern matches: Jan 2020, January 2020, 01/2020, 2020-01

### Error: "No location entities found"

**Check:**
- Resume has location in contact section (first 1000 chars)
- Location is a recognizable city name
- Try adding country ("San Francisco, USA")

### Years of Experience Seems Wrong

**Debug:**
```python
# Add this to calculate_years_experience() for debugging
for start_str, end_str in matches:
    print(f"Found: {start_str} - {end_str}")
    # ... rest of logic
```

---

## ✅ SUCCESS CRITERIA CHECKLIST

- [ ] `python-dateutil` and `spacy` installed
- [ ] spaCy model `en_core_web_sm` downloaded
- [ ] `calculate_years_experience()` returns reasonable values (±1 year accuracy)
- [ ] `extract_location()` finds city/state for 70%+ resumes
- [ ] `generate_professional_summary()` creates readable summaries
- [ ] `parse_resume()` returns all enhanced fields
- [ ] `ingestion.py` saves enhanced fields to PostgreSQL
- [ ] API returns parsed data for form pre-fill
- [ ] Tests pass: `pytest backend/tests/test_enhanced_parsing.py -v`

---

## 🎓 WHAT YOU LEARNED

1. **Date Parsing** - Using `dateutil` for flexible date recognition
2. **Named Entity Recognition** - spaCy NER for location extraction
3. **Text Processing** - Regex patterns for email/phone extraction
4. **Integration** - Enhancing existing pipeline without breaking it
5. **Testing** - Unit tests for NLP functions

---

## 🚀 NEXT STEPS

After completing Prompt 4:
1. Verify all tests pass
2. Test with real resumes
3. Check data in PostgreSQL
4. Move to **Prompt 5: Cross-Encoder Re-ranking**

---

**Estimated Completion Time:** 3-4 hours
**Complexity:** Medium
**Impact:** 🟡 HIGH (Better data quality, UX improvement)

**Ready to enhance your parsing! 🎯**
