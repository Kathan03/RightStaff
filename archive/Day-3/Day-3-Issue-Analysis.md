# 🔍 Day 3 Issues - Root Cause Analysis

**Analyst:** Senior Meta Developer Approach  
**Date:** November 8, 2025

---

## Issue #1: spaCy/Pydantic Compatibility

### 🎯 WHAT is the problem?

**Error:**
```python
TypeError: ForwardRef._evaluate() missing 1 required keyword-only argument: 'recursive_guard'
```

**Symptom:** spaCy model fails to load when trying to import `en_core_web_sm`

### 🤔 WHY is this happening?

**Root Cause:** Pydantic v1 → v2 Breaking Change

1. **Current State:**
   - spaCy 3.7.2 uses pydantic v1 internally
   - FastAPI 0.121.0 requires pydantic v2 (2.5.3)
   - Environment has pydantic 2.5.3

2. **The Conflict:**
   - spaCy's internal code calls `ForwardRef._evaluate()` with old signature
   - Pydantic v2 changed the signature to require `recursive_guard` parameter
   - This is a hard incompatibility

3. **Why It Matters:**
   - spaCy NER provides ~90% skill extraction accuracy
   - Without it, we rely on pattern matching (~80% coverage)
   - 10% accuracy loss is acceptable but not ideal

### 📍 WHERE is it occurring?

**Call Stack:**
```
spacy/__init__.py → pipeline/__init__.py → language.py → 
tokens/__init__.py → vocab.pyx → schemas.py (TokenPatternString)
→ pydantic/v1/main.py → pydantic/v1/typing.py → ForwardRef._evaluate()
```

**Problem Location:** spaCy's internal use of pydantic v1 compatibility layer

---

## Issue #2: Async Event Loop Cleanup

### 🎯 WHAT is the problem?

**Error:**
```python
AttributeError: 'NoneType' object has no attribute 'send'
RuntimeError: Event loop is closed
```

**Symptom:** Test fails when trying to create/query Job model in test suite

### 🤔 WHY is this happening?

**Root Cause:** Multiple Event Loop Lifecycle Issue

1. **Test Structure:**
   ```python
   asyncio.run(test_dlq())        # Creates loop 1, closes it
   asyncio.run(test_sql_filters()) # Creates loop 2, closes it
   asyncio.run(test_job_model())   # Creates loop 3, closes it
   ```

2. **The Problem:**
   - Each `asyncio.run()` creates a NEW event loop
   - Database connection pool is created in first test
   - Connection pool references the FIRST loop
   - When job model test runs (loop 3), connection pool still references loop 1
   - Loop 1 is closed, so `_proactor.send()` fails (proactor is None)

3. **Why Database Connections Matter:**
   - SQLAlchemy async uses persistent connection pool
   - Pool isn't properly cleaned up between test runs
   - Connections try to close but event loop is gone

### 📍 WHERE is it occurring?

**Call Stack:**
```
test_job_model() → AsyncSessionLocal() → 
connection pool checkout → pool ping check → 
asyncpg connection ping → proactor.send() → 
AttributeError (loop._proactor is None)
```

**Problem Location:** Connection pool lifecycle not aligned with event loop lifecycle

---

## 🎯 Solution Strategy (Meta Approach)

### Principle 1: Don't Break What Works
- Pattern matching provides 80% coverage (acceptable baseline)
- Core functionality should never depend on spaCy working

### Principle 2: Graceful Degradation
- App should work with or without spaCy
- Clear logging when features are degraded
- User should know what's available

### Principle 3: Proper Resource Management
- Event loops should be reused in tests
- Database connections should be cleaned up properly
- No resources should outlive their event loop

### Principle 4: Future-Proof
- Solutions should work with future upgrades
- Minimal version pinning (allows flexibility)
- Feature flags for optional components

---

## 📋 Solution Plan

### Solution 1: spaCy/Pydantic Compatibility

**Option A: Lazy Loading with Fallback** ⭐ RECOMMENDED
- Wrap spaCy loading in try-except
- Gracefully degrade to pattern-only matching
- Add clear warning logs
- Don't crash the app

**Option B: Pydantic Compatibility Bridge**
- Install `spacy[pydantic2]` if available
- Or use pydantic v1 compatibility layer
- May require version constraints

**Option C: Alternative NER Library**
- Use transformers-based NER (Hugging Face)
- Heavier but more flexible
- Overkill for current needs

**Chosen Approach:** Option A (Lazy Loading with Fallback)

**Why?**
- Zero risk to existing functionality
- Works immediately without version conflicts
- Pattern matching already provides good coverage
- Can upgrade spaCy later when v4.0 releases (with pydantic v2)

---

### Solution 2: Async Cleanup

**Option A: Single Event Loop for Tests** ⭐ RECOMMENDED
- Create one loop at test start
- Reuse for all async tests
- Close at test end
- Use `pytest-asyncio` properly

**Option B: Proper Connection Cleanup**
- Add connection pool disposal between tests
- Use try-finally blocks
- Close sessions explicitly

**Option C: Mock Database in Tests**
- Use in-memory SQLite for tests
- Faster, no async issues
- Doesn't test real PostgreSQL

**Chosen Approach:** Option A + Option B (Combined)

**Why?**
- Single loop prevents the root cause
- Explicit cleanup prevents resource leaks
- Tests real database behavior
- Production-like testing

---

## 🔧 Implementation Steps

### Step 1: Fix spaCy Loading (5 min)
1. Update `ontology.py` to wrap spaCy in try-except
2. Add feature flag for spaCy availability
3. Log warning when degraded to pattern-only
4. Ensure extract_skills_from_text() works without spaCy

### Step 2: Fix Async Tests (10 min)
1. Update test suite to use single event loop
2. Add proper connection cleanup
3. Use pytest-asyncio fixtures
4. Add explicit session disposal

### Step 3: Verify (5 min)
1. Run test suite
2. Verify 100% pass rate
3. Test with and without spaCy
4. Confirm no resource leaks

---

## 📊 Expected Outcome

### Before Fix:
- ❌ spaCy fails to load (hard crash)
- ⚠️ Test suite: 28/29 passed (96.6%)
- Skills extraction: Pattern-only (80% coverage)

### After Fix:
- ✅ spaCy loads gracefully (or falls back)
- ✅ Test suite: 29/29 passed (100%)
- ✅ Skills extraction: Pattern + spaCy NER (90% coverage) OR Pattern-only (80%)
- ✅ Clear logging of feature availability

---

## 🎯 Success Criteria

1. ✅ App starts without errors (with or without spaCy)
2. ✅ Skills extraction works (pattern matching minimum)
3. ✅ Test suite passes 100% (29/29)
4. ✅ No async event loop errors
5. ✅ Clear logs indicate feature status
6. ✅ No breaking changes to existing code

---

## 🚀 Ready to Implement

This analysis provides:
- Clear understanding of root causes
- Multiple solution options evaluated
- Recommended approach with reasoning
- Step-by-step implementation plan
- Success criteria defined

**Next:** Execute the implementation plan.

