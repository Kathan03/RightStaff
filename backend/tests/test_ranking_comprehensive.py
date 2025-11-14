"""
Comprehensive test script for RightStaff ranking functionality.
Tests all fixes for the Decimal JSON serialization error and SQL gating logic.

Tests:
1. Create job with matching location (should find candidates)
2. Create job with non-matching location (should return empty set - expected behavior)
3. Create job with skills only (should find candidates with those skills)
4. Create job with experience requirements
5. Verify Decimal values are properly converted to float
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def print_test_header(test_name: str):
    """Print formatted test header"""
    print("\n" + "="*80)
    print(f"TEST: {test_name}")
    print("="*80)

def print_result(success: bool, message: str):
    """Print test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")

def create_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a job posting"""
    print(f"\n📝 Creating job: {job_data['title']}")
    response = requests.post(f"{BASE_URL}/api/v1/jobs/", json=job_data)

    if response.status_code == 201:
        result = response.json()
        print(f"   Created job ID: {result['job_id']}")
        return result
    else:
        print(f"   ❌ Failed to create job: {response.status_code}")
        print(f"   Error: {response.text}")
        return {}

def rank_candidates(job_id: str) -> Dict[str, Any]:
    """Trigger candidate ranking"""
    print(f"\n🎯 Ranking candidates for job: {job_id}")
    response = requests.post(
        f"{BASE_URL}/api/v1/jobs/rank",
        json={"job_id": job_id, "use_cache": False}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"   Status: {result['status']}")
        print(f"   Total qualified: {result['total_qualified']}")
        return result
    else:
        print(f"   ❌ Failed to rank: {response.status_code}")
        print(f"   Error: {response.text}")
        return {}

def get_rankings(job_id: str, top_k: int = 20) -> Dict[str, Any]:
    """Get cached rankings"""
    print(f"\n📊 Fetching rankings for job: {job_id}")
    response = requests.get(f"{BASE_URL}/api/v1/jobs/{job_id}/rankings?top_k={top_k}")

    if response.status_code == 200:
        result = response.json()
        print(f"   Status: {result['status']}")
        if result['status'] == 'found':
            print(f"   Total qualified: {result['total_qualified']}")
            print(f"   Returned: {result['returned_count']}")
            return result
        return result
    else:
        print(f"   ❌ Failed to get rankings: {response.status_code}")
        return {}

def test_health_check():
    """Test 1: Health check"""
    print_test_header("Health Check")

    response = requests.get(f"{BASE_URL}/health")

    if response.status_code == 200:
        health = response.json()
        all_ok = all(service == "ok" for service in health['services'].values())

        if all_ok:
            print_result(True, "All services are healthy")
            return True
        else:
            print_result(False, "Some services are unhealthy")
            for service, status in health['services'].items():
                print(f"   {service}: {status}")
            return False
    else:
        print_result(False, f"Health check failed: {response.status_code}")
        return False

def test_job_with_matching_location():
    """Test 2: Create job with location that has candidates"""
    print_test_header("Job with Matching Location")

    job_data = {
        "title": "Senior Python Developer - San Francisco",
        "description": "Looking for Python developer in San Francisco",
        "required_skills": ["Python"],
        "must_have_skills": ["Python"],
        "min_years_experience": 2.0,
        "max_years_experience": 10.0,
        "location": "San Francisco"  # This location exists in database
    }

    # Create job
    job_result = create_job(job_data)
    if not job_result:
        print_result(False, "Failed to create job")
        return False

    job_id = job_result['job_id']

    # Rank candidates
    time.sleep(1)  # Give time for processing
    rank_result = rank_candidates(job_id)

    if not rank_result:
        print_result(False, "Failed to rank candidates")
        return False

    # Check if we found candidates
    if rank_result['total_qualified'] > 0:
        print_result(True, f"Found {rank_result['total_qualified']} qualified candidates")

        # Verify no Decimal serialization error occurred
        gates_applied = rank_result.get('gates_applied', {})
        if gates_applied:
            print(f"   Gates applied: {gates_applied}")
            print_result(True, "Decimal values properly serialized (no error)")

        return True
    else:
        print_result(False, "No candidates found (expected at least 1)")
        return False

def test_job_with_non_matching_location():
    """Test 3: Create job with location that has no candidates"""
    print_test_header("Job with Non-Matching Location (Expected: Empty Set)")

    job_data = {
        "title": "Python Developer - State College",
        "description": "Looking for Python developer in State College",
        "required_skills": ["Python"],
        "must_have_skills": ["Python"],
        "min_years_experience": 3.0,
        "max_years_experience": 10.0,
        "location": "State College"  # This location does NOT exist in database
    }

    # Create job
    job_result = create_job(job_data)
    if not job_result:
        print_result(False, "Failed to create job")
        return False

    job_id = job_result['job_id']

    # Rank candidates
    time.sleep(1)
    rank_result = rank_candidates(job_id)

    if not rank_result:
        print_result(False, "Failed to rank candidates")
        return False

    # Check that no candidates were found (expected behavior)
    if rank_result['total_qualified'] == 0:
        print_result(True, "Correctly returned empty set for non-matching location")
        print("   This is EXPECTED behavior - no candidates in 'State College'")
        return True
    else:
        print_result(False, f"Unexpected: Found {rank_result['total_qualified']} candidates")
        return False

def test_job_with_skills_only():
    """Test 4: Create job with skills only (no location filter)"""
    print_test_header("Job with Skills Only (No Location Filter)")

    job_data = {
        "title": "JavaScript Developer",
        "description": "Looking for JavaScript developer",
        "required_skills": ["JavaScript"],
        "must_have_skills": ["JavaScript"],
        "min_years_experience": None,
        "max_years_experience": None,
        "location": None  # No location filter
    }

    # Create job
    job_result = create_job(job_data)
    if not job_result:
        print_result(False, "Failed to create job")
        return False

    job_id = job_result['job_id']

    # Rank candidates
    time.sleep(1)
    rank_result = rank_candidates(job_id)

    if not rank_result:
        print_result(False, "Failed to rank candidates")
        return False

    # Should find candidates with JavaScript skill
    if rank_result['total_qualified'] > 0:
        print_result(True, f"Found {rank_result['total_qualified']} candidates with JavaScript")
        return True
    else:
        print_result(False, "No candidates found (expected at least 1)")
        return False

def test_decimal_serialization():
    """Test 5: Verify Decimal values are properly handled"""
    print_test_header("Decimal Serialization Test")

    job_data = {
        "title": "Test Job for Decimal Serialization",
        "description": "Testing Decimal to float conversion",
        "required_skills": ["Python"],
        "must_have_skills": ["Python"],
        "min_years_experience": 2.5,  # Decimal value
        "max_years_experience": 7.75, # Decimal value
        "location": None
    }

    # Create job
    job_result = create_job(job_data)
    if not job_result:
        print_result(False, "Failed to create job")
        return False

    job_id = job_result['job_id']

    # Rank candidates
    time.sleep(1)
    rank_result = rank_candidates(job_id)

    if not rank_result:
        print_result(False, "Ranking failed - might be Decimal serialization error")
        return False

    # Check gates_applied values are floats (not Decimals)
    gates_applied = rank_result.get('gates_applied', {})
    min_years = gates_applied.get('min_years')
    max_years = gates_applied.get('max_years')

    if isinstance(min_years, (int, float)) and isinstance(max_years, (int, float)):
        print_result(True, f"Decimal values properly converted: min={min_years}, max={max_years}")
        return True
    else:
        print_result(False, f"Decimal values not converted: min={type(min_years)}, max={type(max_years)}")
        return False

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("COMPREHENSIVE RANKING TESTS - RightStaff")
    print("="*80)

    results = {}

    # Test 1: Health check
    results['health_check'] = test_health_check()

    # Test 2: Job with matching location
    results['matching_location'] = test_job_with_matching_location()

    # Test 3: Job with non-matching location
    results['non_matching_location'] = test_job_with_non_matching_location()

    # Test 4: Job with skills only
    results['skills_only'] = test_job_with_skills_only()

    # Test 5: Decimal serialization
    results['decimal_serialization'] = test_decimal_serialization()

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "-"*80)
    print(f"TOTAL: {passed_tests}/{total_tests} tests passed")
    print("="*80)

    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("\nKey Fixes Validated:")
        print("  ✅ Decimal JSON serialization error fixed")
        print("  ✅ SQL gating logic working correctly")
        print("  ✅ Location filtering working as expected")
        print("  ✅ Skills filtering working correctly")
        return True
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed")
        return False

if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)