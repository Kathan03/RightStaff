# 🎯 PROMPT 1: ENHANCED RESUME PARSING WITH LIGHTWEIGHT LLM

**Estimated Time:** 6-8 hours
**Priority:** 🔴 CRITICAL
**Prerequisites:** Day-5 complete, ingestion.py working

---

## 📋 OBJECTIVE

Replace regex-based resume parsing with a **lightweight LLM (Phi-3-Mini)** for 85%+ field extraction accuracy.

**Current Problem:**
- Regex-based parsing has 60-70% accuracy
- Fails on complex date formats
- Misses context-dependent information
- Cannot generate summaries

**After This Prompt:**
- LLM-based parsing with 85-90% accuracy
- Handles all resume formats (PDF, DOCX, TXT)
- Auto-generates professional summaries
- Intelligent years of experience calculation
- Better location extraction

---

## 🎯 IMPLEMENTATION CHECKLIST

### Files to Create/Modify
- [ ] `backend/app/services/llm_parser.py` (NEW)
- [ ] `backend/app/services/parsers.py` (update extract_text function)
- [ ] `backend/app/services/ingestion.py` (update parse-only mode)
- [ ] `requirements.txt` (add transformers, torch, PyPDF2, python-docx)

### Success Criteria
- [ ] Phi-3-Mini loads in < 30 seconds
- [ ] Parsing accuracy > 85% for name, email, phone
- [ ] Years calculation accuracy ± 1 year
- [ ] Parsing completes in < 10 seconds per resume
- [ ] All tests pass

---

## 📝 STEP 1: INSTALL DEPENDENCIES

### Requirements

**File:** `requirements.txt`

**Add these lines:**
```txt
# Lightweight LLM for resume parsing (Day-6 Prompt 1)
transformers>=4.36.0
torch>=2.1.0
accelerate>=0.25.0

# Document parsing
PyPDF2>=3.0.0
python-docx>=1.1.0
```

### Install Dependencies

```bash
cd /home/user/RightStaff/backend

# Install packages
pip install transformers torch accelerate PyPDF2 python-docx

# Verify installation
python -c "import transformers; import torch; print('✅ LLM dependencies installed')"
```

**Expected output:**
```
✅ LLM dependencies installed
```

---

## 📝 STEP 2: CREATE LLM PARSER SERVICE

### File: `backend/app/services/llm_parser.py` (NEW)

**Create this new file with complete implementation:**

```python
"""
LLM-based resume parser using Phi-3-Mini.

Why Phi-3-Mini?
- Small: 3.8B parameters (~8GB RAM)
- Fast: 50-100 tokens/sec on CPU
- Accurate: 85-90% for structured extraction
- Runs on: CPU (no GPU needed)
"""

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import json
import logging
from typing import Dict, Optional
import re

logger = logging.getLogger(__name__)


class LLMResumeParser:
    """
    Lightweight LLM for resume parsing.

    Uses microsoft/Phi-3-mini-4k-instruct for structured field extraction.
    """

    def __init__(self, model_name: str = "microsoft/Phi-3-mini-4k-instruct"):
        """
        Initialize LLM parser.

        Args:
            model_name: HuggingFace model ID
        """
        logger.info(f"🤖 Loading LLM parser: {model_name}")

        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True
            )

            # Load model with float16 for efficiency
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                device_map="auto",  # Auto CPU/GPU placement
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )

            logger.info("✅ LLM parser loaded successfully")

        except Exception as e:
            logger.error(f"❌ Failed to load LLM parser: {e}")
            raise

    def parse_resume(self, resume_text: str) -> Dict:
        """
        Extract structured fields from resume using LLM.

        Args:
            resume_text: Raw resume text

        Returns:
            {
                "full_name": str,
                "email": str,
                "phone": str,
                "location": {"city": str, "state": str, "country": str},
                "years_experience": float,
                "professional_summary": str,
                "skills": List[str]
            }
        """
        logger.info("📄 Starting LLM-based resume parsing")

        # Truncate to 2000 chars (fits in 4k context)
        resume_snippet = resume_text[:2000]

        # Construct prompt
        prompt = f"""Extract information from this resume and return ONLY valid JSON.

Resume:
{resume_snippet}

Extract these fields:
1. full_name (string) - Candidate's full name
2. email (string) - Email address
3. phone (string) - Phone number
4. location (object) - {{"city": "...", "state": "...", "country": "..."}}
5. years_experience (number) - Total years calculated from employment dates
6. professional_summary (string) - 2-3 sentence summary
7. skills (array) - List of technical skills

IMPORTANT:
- Return ONLY valid JSON, no explanation
- If field not found, use null
- Calculate years_experience from dates in resume

JSON:
{{"""

        # Tokenize
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=3000
        )

        # Move to same device as model
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        # Generate
        try:
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=500,
                    temperature=0.1,  # Low temp for deterministic output
                    do_sample=False,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            logger.debug(f"LLM response: {response[:200]}...")

            # Extract JSON from response
            parsed_data = self._extract_json(response)

            # Post-process and validate
            parsed_data = self._validate_and_clean(parsed_data)

            logger.info(f"✅ Parsed resume: {parsed_data.get('full_name', 'Unknown')}")
            logger.info(f"   Email: {parsed_data.get('email', 'N/A')}")
            logger.info(f"   Years: {parsed_data.get('years_experience', 'N/A')}")
            logger.info(f"   Skills: {len(parsed_data.get('skills', []))} found")

            return parsed_data

        except Exception as e:
            logger.error(f"❌ LLM parsing failed: {e}")
            return self._empty_structure()

    def _extract_json(self, response: str) -> Dict:
        """
        Extract JSON from LLM response.

        Handles cases where LLM adds text before/after JSON.
        """
        try:
            # Find JSON boundaries
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                logger.warning("No JSON found in response")
                return self._empty_structure()

            json_str = response[json_start:json_end]

            # Parse JSON
            parsed = json.loads(json_str)
            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response: {response[:500]}")
            return self._empty_structure()

    def _validate_and_clean(self, data: Dict) -> Dict:
        """
        Validate and clean extracted data.

        - Ensure all expected keys exist
        - Clean phone/email formats
        - Validate years_experience is numeric
        - Ensure skills is a list
        """
        cleaned = {
            "full_name": self._clean_string(data.get("full_name")),
            "email": self._clean_email(data.get("email")),
            "phone": self._clean_phone(data.get("phone")),
            "location": self._clean_location(data.get("location")),
            "years_experience": self._clean_years(data.get("years_experience")),
            "professional_summary": self._clean_string(data.get("professional_summary")),
            "skills": self._clean_skills(data.get("skills"))
        }

        return cleaned

    def _clean_string(self, value) -> Optional[str]:
        """Clean string value."""
        if not value or value == "null":
            return None
        return str(value).strip()

    def _clean_email(self, value) -> Optional[str]:
        """Validate and clean email."""
        if not value:
            return None

        email = str(value).strip().lower()

        # Basic email validation
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return email

        return None

    def _clean_phone(self, value) -> Optional[str]:
        """Clean phone number."""
        if not value:
            return None

        return str(value).strip()

    def _clean_location(self, value) -> Dict[str, Optional[str]]:
        """Clean location object."""
        if not value or not isinstance(value, dict):
            return {"city": None, "state": None, "country": None}

        return {
            "city": self._clean_string(value.get("city")),
            "state": self._clean_string(value.get("state")),
            "country": self._clean_string(value.get("country"))
        }

    def _clean_years(self, value) -> Optional[float]:
        """Clean years of experience."""
        if not value:
            return None

        try:
            years = float(value)
            # Sanity check: 0-50 years
            if 0 <= years <= 50:
                return round(years, 1)
        except (ValueError, TypeError):
            pass

        return None

    def _clean_skills(self, value) -> list:
        """Clean skills list."""
        if not value:
            return []

        if isinstance(value, list):
            return [str(s).strip() for s in value if s]

        if isinstance(value, str):
            # Split by comma if single string
            return [s.strip() for s in value.split(',') if s.strip()]

        return []

    def _empty_structure(self) -> Dict:
        """Return empty structure when parsing fails."""
        return {
            "full_name": None,
            "email": None,
            "phone": None,
            "location": {"city": None, "state": None, "country": None},
            "years_experience": None,
            "professional_summary": None,
            "skills": []
        }


# ═══════════════════════════════════════════════════════════════
# Singleton instance
# ═══════════════════════════════════════════════════════════════

# Initialize once on module import
llm_parser = None


def get_llm_parser() -> LLMResumeParser:
    """Get or create singleton LLM parser instance."""
    global llm_parser

    if llm_parser is None:
        llm_parser = LLMResumeParser()

    return llm_parser
```

**Test the parser:**

```bash
cd /home/user/RightStaff/backend

# Test LLM parser
python -c "
from app.services.llm_parser import get_llm_parser

# Sample resume
text = '''
John Doe
Senior Software Engineer
john.doe@example.com | (555) 123-4567
San Francisco, CA 94105

SUMMARY
Experienced software engineer with 10+ years in Python development and cloud architecture.

EXPERIENCE
Google Inc. | Senior Engineer | January 2018 - Present
- Led microservices development team
- Architected cloud solutions on AWS

Microsoft | Software Engineer | June 2015 - December 2017
- Developed enterprise applications

SKILLS
Python, AWS, Docker, Kubernetes, FastAPI, PostgreSQL
'''

parser = get_llm_parser()
result = parser.parse_resume(text)

print('Parsed Data:')
print(f'Name: {result[\"full_name\"]}')
print(f'Email: {result[\"email\"]}')
print(f'Phone: {result[\"phone\"]}')
print(f'Years: {result[\"years_experience\"]}')
print(f'Skills: {result[\"skills\"]}')
"
```

**Expected output:**
```
🤖 Loading LLM parser: microsoft/Phi-3-mini-4k-instruct
✅ LLM parser loaded successfully
📄 Starting LLM-based resume parsing
✅ Parsed resume: John Doe
   Email: john.doe@example.com
   Years: 7.5
   Skills: 6 found

Parsed Data:
Name: John Doe
Email: john.doe@example.com
Phone: (555) 123-4567
Years: 7.5
Skills: ['Python', 'AWS', 'Docker', 'Kubernetes', 'FastAPI', 'PostgreSQL']
```

---

## 📝 STEP 3: UPDATE TEXT EXTRACTION

### File: `backend/app/services/parsers.py`

**Add this function (if not exists):**

```python
def extract_text(file_bytes: bytes, file_type: str) -> str:
    """
    Extract text from resume file (PDF, DOCX, or TXT).

    Args:
        file_bytes: Raw file bytes
        file_type: File extension (.pdf, .docx, .txt)

    Returns:
        Extracted text

    Example:
        >>> pdf_bytes = open('resume.pdf', 'rb').read()
        >>> text = extract_text(pdf_bytes, '.pdf')
    """
    import io

    file_type = file_type.lower()

    if file_type == '.pdf':
        # Extract from PDF
        import PyPDF2

        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"

            logger.info(f"✅ Extracted {len(text)} chars from PDF")
            return text

        except Exception as e:
            logger.error(f"❌ PDF extraction failed: {e}")
            return ""

    elif file_type in ['.docx', '.doc']:
        # Extract from DOCX
        from docx import Document

        try:
            doc = Document(io.BytesIO(file_bytes))
            text = "\n".join([para.text for para in doc.paragraphs])

            logger.info(f"✅ Extracted {len(text)} chars from DOCX")
            return text

        except Exception as e:
            logger.error(f"❌ DOCX extraction failed: {e}")
            return ""

    else:  # .txt or unknown
        # Extract as plain text
        try:
            text = file_bytes.decode('utf-8', errors='ignore')
            logger.info(f"✅ Extracted {len(text)} chars from TXT")
            return text

        except Exception as e:
            logger.error(f"❌ Text extraction failed: {e}")
            return ""
```

---

## 📝 STEP 4: UPDATE INGESTION PIPELINE

### File: `backend/app/services/ingestion.py`

**FIND the parse-only mode section (around line 200):**

```python
if mode == "parse_only":
    # OLD: regex-based parsing
    from app.services.parsers import parse_resume
    parsed_data = parse_resume(resume_bytes, file_type=".pdf")
```

**REPLACE WITH:**

```python
if mode == "parse_only":
    # ══════════════════════════════════════════════════════════════
    # STAGE 1-3: LLM-Based Resume Parsing
    # ══════════════════════════════════════════════════════════════

    logger.info(f"📄 Starting parse-only mode for {candidate_id}")

    # Download resume from MinIO
    resume_bytes = await s3_client.download_file(s3_url)
    logger.info(f"📥 Downloaded {len(resume_bytes)} bytes from MinIO")

    # Extract text from PDF/DOCX/TXT
    from app.services.parsers import extract_text

    # Detect file type from s3_url
    if '.pdf' in s3_url.lower():
        file_type = '.pdf'
    elif '.docx' in s3_url.lower() or '.doc' in s3_url.lower():
        file_type = '.docx'
    else:
        file_type = '.txt'

    resume_text = extract_text(resume_bytes, file_type)

    if not resume_text:
        logger.error(f"❌ Failed to extract text from resume")
        return

    logger.info(f"📝 Extracted {len(resume_text)} chars from resume")

    # Parse using LLM
    from app.services.llm_parser import get_llm_parser

    llm_parser = get_llm_parser()
    parsed_data = llm_parser.parse_resume(resume_text)

    # Add raw text to parsed data
    parsed_data["text"] = resume_text

    # Cache in Redis with 1-hour TTL
    await redis_client.set(
        f"parsed_candidate:{candidate_id}",
        json.dumps(parsed_data, default=str),  # default=str for serialization
        ex=3600  # 1 hour
    )

    logger.info(f"✅ LLM parsing complete for {candidate_id}")
    logger.info(f"   Name: {parsed_data.get('full_name', 'Unknown')}")
    logger.info(f"   Email: {parsed_data.get('email', 'N/A')}")
    logger.info(f"   Phone: {parsed_data.get('phone', 'N/A')}")
    logger.info(f"   Years: {parsed_data.get('years_experience', 'N/A')}")
    logger.info(f"   Location: {parsed_data.get('location', {}).get('city', 'N/A')}")
    logger.info(f"   Skills: {len(parsed_data.get('skills', []))} found")

    return  # STOP HERE - no embeddings, no Qdrant, no PostgreSQL
```

---

## 🧪 VALIDATION & TESTING

### Step 1: Unit Tests

**File:** `backend/tests/test_llm_parser.py` (NEW)

```python
import pytest
from app.services.llm_parser import get_llm_parser


def test_llm_parser_loads():
    """Test that LLM parser loads successfully."""
    parser = get_llm_parser()
    assert parser is not None
    assert parser.model is not None
    assert parser.tokenizer is not None


def test_parse_complete_resume():
    """Test parsing a complete resume."""
    parser = get_llm_parser()

    resume_text = """
    John Doe
    Senior Software Engineer
    john.doe@example.com | (555) 123-4567
    San Francisco, CA 94105

    SUMMARY
    10+ years of experience in Python development and cloud architecture.

    EXPERIENCE
    Google Inc. | Senior Engineer | January 2018 - Present (6 years)
    - Led microservices team

    Microsoft | Engineer | June 2015 - December 2017 (2.5 years)
    - Developed applications

    SKILLS
    Python, AWS, Docker, Kubernetes
    """

    result = parser.parse_resume(resume_text)

    # Validate all fields extracted
    assert result["full_name"] == "John Doe"
    assert result["email"] == "john.doe@example.com"
    assert result["phone"] == "(555) 123-4567"
    assert result["location"]["city"] == "San Francisco"
    assert result["location"]["state"] == "CA"
    assert 6.0 <= result["years_experience"] <= 10.0  # Allow some variance
    assert "Python" in result["skills"]
    assert len(result["professional_summary"]) > 0


def test_parse_minimal_resume():
    """Test parsing a minimal resume (only name and email)."""
    parser = get_llm_parser()

    resume_text = """
    Jane Smith
    jane.smith@example.com
    """

    result = parser.parse_resume(resume_text)

    assert result["full_name"] == "Jane Smith"
    assert result["email"] == "jane.smith@example.com"
    # Other fields may be None
    assert result["years_experience"] is None or result["years_experience"] >= 0


def test_parse_with_special_chars():
    """Test parsing resume with special characters."""
    parser = get_llm_parser()

    resume_text = """
    José García-López
    jose.garcia@example.com
    Madrid, Spain
    """

    result = parser.parse_resume(resume_text)

    assert "José" in result["full_name"] or "Jose" in result["full_name"]
    assert result["email"] == "jose.garcia@example.com"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### Step 2: Integration Test

```bash
cd /home/user/RightStaff/backend

# Run unit tests
pytest tests/test_llm_parser.py -v

# Expected: All tests pass
```

### Step 3: End-to-End Test

```bash
# 1. Start backend
cd /home/user/RightStaff/backend
uvicorn app.main:app --reload &

# Wait for startup
sleep 5

# 2. Upload resume
curl -X POST "http://localhost:8000/api/v1/candidates/upload-resume" \
  -F "file=@sample_resume.pdf"

# Expected response:
# {
#   "temp_id": "uuid-...",
#   "parsed_data": {
#     "full_name": "John Doe",
#     "email": "john.doe@example.com",
#     "phone": "(555) 123-4567",
#     "years_experience": 7.5,
#     "location": {"city": "San Francisco", "state": "CA", "country": "USA"},
#     "professional_summary": "Experienced software engineer...",
#     "skills": ["Python", "AWS", "Docker"]
#   }
# }
```

---

## 🚨 TROUBLESHOOTING

### Issue 1: "Model download fails"

**Symptoms:**
```
OSError: We couldn't connect to 'https://huggingface.co' to load this model
```

**Solution:**
```bash
# Download model manually
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained(
    "microsoft/Phi-3-mini-4k-instruct",
    trust_remote_code=True,
    cache_dir="/home/user/.cache/huggingface"
)

model = AutoModelForCausalLM.from_pretrained(
    "microsoft/Phi-3-mini-4k-instruct",
    trust_remote_code=True,
    cache_dir="/home/user/.cache/huggingface"
)
```

### Issue 2: "Out of memory"

**Symptoms:**
```
RuntimeError: CUDA out of memory
```

**Solution:**
```python
# Use CPU instead of GPU
model = AutoModelForCausalLM.from_pretrained(
    "microsoft/Phi-3-mini-4k-instruct",
    torch_dtype=torch.float16,
    device_map="cpu",  # Force CPU
    trust_remote_code=True
)
```

### Issue 3: "Parsing too slow (> 30 seconds)"

**Solution:**
```python
# Reduce max_new_tokens
outputs = self.model.generate(
    **inputs,
    max_new_tokens=300,  # Reduce from 500
    temperature=0.1,
    do_sample=False
)
```

### Issue 4: "LLM returns invalid JSON"

**Solution:**
Already handled in `_extract_json()` method. Check logs:
```bash
# Check logs for JSON errors
grep "Failed to parse JSON" /var/log/rightstaff.log
```

If persistent, adjust prompt to be more explicit about JSON format.

---

## ✅ SUCCESS CRITERIA CHECKLIST

- [ ] Phi-3-Mini loads in < 30 seconds
- [ ] Name extraction accuracy > 90%
- [ ] Email extraction accuracy > 95%
- [ ] Years calculation within ± 1 year
- [ ] Skills extraction finds 80%+ of listed skills
- [ ] Parsing completes in < 10 seconds per resume
- [ ] All unit tests pass: `pytest tests/test_llm_parser.py -v`
- [ ] API returns parsed data: `POST /api/v1/candidates/upload-resume`
- [ ] Redis cache populated: `redis-cli GET "parsed_candidate:*"`
- [ ] No errors in server logs

---

## 🎓 WHAT YOU LEARNED

1. **Lightweight LLMs** - Phi-3-Mini runs on CPU with good performance
2. **Structured Extraction** - Using LLMs for JSON extraction
3. **Prompt Engineering** - Crafting prompts for deterministic output
4. **Error Handling** - Graceful fallbacks when LLM fails
5. **Performance Optimization** - Low temperature, small token limits
6. **Document Parsing** - PyPDF2 and python-docx for text extraction

---

## 🚀 NEXT STEPS

After completing Prompt 1:
1. Verify all tests pass
2. Test with 5-10 real resumes
3. Check parsing accuracy
4. Monitor performance (< 10s per resume)
5. Move to **Prompt 2: Cross-Encoder + RAG with LangGraph**

---

**Estimated Completion Time:** 6-8 hours
**Complexity:** Medium-High
**Impact:** 🔴 CRITICAL (Foundation for high-quality data)

**Ready to build intelligent resume parsing! 🎯**
