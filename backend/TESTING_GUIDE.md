# LLM Parser Testing Guide

## Model Download Location

**Cache Directory:**
```
C:\Users\katha\.cache\huggingface\hub\models--microsoft--Phi-3-mini-4k-instruct\
```

**Model Size:** ~7-8GB (2 shards)

**Files:**
- `blobs/` - Model weight files
- `snapshots/` - Versioned snapshots
- `refs/` - Branch references

---

## Quick Start Testing

### 1. Check Model Download Status

```bash
# Check if model is fully downloaded
ls -lh "C:\Users\katha\.cache\huggingface\hub\models--microsoft--Phi-3-mini-4k-instruct\blobs"

# Look for .incomplete files - if present, download is still in progress
```

### 2. Run Quick Test

```bash
cd backend

# Test with LLM (if model downloaded)
python test_llm_simple.py

# Test with regex fallback (always works)
USE_LLM_PARSING=false python test_llm_simple.py
```

### 3. Run Full Test Suite

```bash
# Unit tests
pytest tests/test_llm_parser.py -v

# Specific test
pytest tests/test_llm_parser.py::TestLLMResumeParsingComplete::test_parse_complete_resume -v
```

---

## Testing Scenarios

### Scenario 1: LLM Parsing (Phi-3-Mini)

**When:** Model is fully downloaded
**Expected:** 85-90% accuracy, 5-10s per resume

```bash
cd backend
export USE_LLM_PARSING=true
python test_llm_simple.py
```

**Expected Output:**
```
[PASS] Name extracted
[PASS] Email correct
[PASS] Years calculated
[PASS] Skills found
[PASS] Time OK (<30s)
```

### Scenario 2: Regex Fallback

**When:** Model not downloaded OR LLM disabled
**Expected:** 60-70% accuracy, <1s per resume

```bash
cd backend
export USE_LLM_PARSING=false
python test_llm_simple.py
```

### Scenario 3: End-to-End API Test

**Test resume upload with parsing:**

```bash
# 1. Start backend
cd backend
uvicorn app.main:app --reload

# 2. Create test resume
cat > /tmp/test_resume.txt << 'EOF'
John Doe
Senior Software Engineer
john.doe@example.com | (555) 123-4567
San Francisco, CA

EXPERIENCE
Google Inc. | Senior Engineer | Jan 2018 - Present
- Led team of 8 engineers
- Built microservices

Microsoft | Engineer | Jun 2015 - Dec 2017
- Developed .NET applications

SKILLS
Python, AWS, Docker, Kubernetes, FastAPI
EOF

# 3. Upload resume
curl -X POST "http://localhost:8000/api/v1/candidates/upload-resume" \
  -F "file=@/tmp/test_resume.txt"

# Expected response includes parsed data
```

### Scenario 4: Performance Test

**Test parsing speed:**

```python
import asyncio
import time
from app.services.llm_parser import get_llm_parser

async def performance_test():
    parser = get_llm_parser()

    resume = "John Doe\njohn@example.com\n10 years experience in Python"

    # First parse (includes model loading)
    start = time.time()
    result1 = await parser.parse_resume(resume)
    first_time = time.time() - start

    # Second parse (model already loaded)
    start = time.time()
    result2 = await parser.parse_resume(resume)
    second_time = time.time() - start

    print(f"First parse: {first_time:.2f}s (includes model loading)")
    print(f"Second parse: {second_time:.2f}s (should be <10s)")

    assert second_time < 10, "Parsing too slow!"

asyncio.run(performance_test())
```

---

## Validation Checklist

### ✅ Implementation Validation

- [ ] `llm_parser.py` created with async methods
- [ ] `config.py` has `use_llm_parsing` flag
- [ ] `ingestion.py` updated with LLM + fallback
- [ ] Tests created in `tests/test_llm_parser.py`
- [ ] Model downloads to correct location

### ✅ Functionality Validation

- [ ] Model loads without errors
- [ ] Parsing completes in <10s (after first load)
- [ ] Name extracted correctly (>90%)
- [ ] Email extracted correctly (>95%)
- [ ] Phone extracted correctly (>85%)
- [ ] Years calculated within ±1 year
- [ ] Skills extracted (>80% of listed skills)
- [ ] Professional summary generated

### ✅ Error Handling Validation

- [ ] Graceful fallback if model download fails
- [ ] Graceful fallback if LLM inference fails
- [ ] Handles empty resumes without crashing
- [ ] Handles corrupted text gracefully
- [ ] Validates email format correctly
- [ ] Validates years of experience range (0-50)

### ✅ Performance Validation

- [ ] First parse <30s (includes model loading)
- [ ] Subsequent parses <10s
- [ ] Memory usage ~8GB (model size)
- [ ] No blocking of async event loop
- [ ] Concurrent requests handled correctly

### ✅ Integration Validation

- [ ] API endpoint works with LLM parsing
- [ ] Redis caching works
- [ ] Skills merge with ontology service
- [ ] Parse-only mode works
- [ ] Full ingestion mode works

---

## Troubleshooting

### Issue: Model download hangs

**Symptoms:** Download stays at 0% for long time

**Solution:**
```bash
# Clear cache and retry
rm -rf "C:\Users\katha\.cache\huggingface\hub\models--microsoft--Phi-3-mini-4k-instruct"

# Try manual download
python -c "
from transformers import AutoTokenizer, AutoModelForCausalLM
tokenizer = AutoTokenizer.from_pretrained('microsoft/Phi-3-mini-4k-instruct', trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained('microsoft/Phi-3-mini-4k-instruct', trust_remote_code=True)
print('Download complete!')
"
```

### Issue: Out of memory

**Symptoms:** "CUDA out of memory" or "RuntimeError: out of memory"

**Solution:**
```python
# Force CPU usage in llm_parser.py
# Line 134: Change device_map
device_map="cpu"  # Instead of "auto"
```

### Issue: Parsing too slow (>30s)

**Solution:**
```python
# Reduce max_new_tokens in llm_parser.py
# Line 209: Change max_new_tokens
max_new_tokens=300  # Instead of 500
```

### Issue: LLM returns invalid JSON

**Symptoms:** "Failed to parse JSON" in logs

**Solution:**
```bash
# Check logs
grep "Failed to parse JSON" logs/rightstaff.log

# If persistent, adjust prompt temperature
# In llm_parser.py line 210:
temperature=0.05  # Lower = more deterministic
```

### Issue: Skills not extracted

**Symptoms:** Empty skills list or missing skills

**Solution:**
- Verify resume contains skills section
- Check if ontology service is working
- LLM skills + ontology skills are merged
- Prompt may need adjustment for skill keywords

---

## Advanced Testing

### Load Testing

```python
# Test with 100 concurrent resume parses
import asyncio
from app.services.llm_parser import get_llm_parser

async def load_test():
    parser = get_llm_parser()

    resumes = [f"Candidate {i}\ncandidate{i}@example.com\n5 years experience"
               for i in range(100)]

    tasks = [parser.parse_resume(r) for r in resumes]
    results = await asyncio.gather(*tasks)

    print(f"Parsed {len(results)} resumes")
    success = sum(1 for r in results if r['email'] is not None)
    print(f"Success rate: {success/len(results)*100:.1f}%")

asyncio.run(load_test())
```

### Accuracy Testing

Create test suite with 50 real resumes and manually verify:
- Name extraction accuracy
- Email extraction accuracy
- Phone extraction accuracy
- Years calculation accuracy
- Skills extraction completeness

Target: >85% across all fields

---

## Next Steps After Testing

1. **Monitor in Production**
   - Track parsing accuracy
   - Monitor performance (latency)
   - Watch error rates

2. **Optimize If Needed**
   - Adjust prompt for better accuracy
   - Tune temperature for determinism
   - Reduce max_new_tokens for speed

3. **A/B Test**
   - Compare LLM vs Regex accuracy
   - Measure user satisfaction
   - Decide on default setting

4. **Scale Considerations**
   - Consider GPU for faster inference
   - Cache parsed results aggressively
   - Rate limit parsing requests

---

## Success Criteria

✅ **All tests pass**
✅ **Accuracy >85%**
✅ **Performance <10s per resume**
✅ **No blocking issues**
✅ **Graceful error handling**

**Implementation complete!** 🎉
