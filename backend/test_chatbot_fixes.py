"""
Test script to verify chatbot fixes for:
1. "Alex Chen" context amnesia (should now analyze fit properly)
2. "List all applicants" retrieval limit (should return all 9 candidates)
"""

import asyncio
import sys
sys.path.insert(0, '.')

from app.services.chatbot_langgraph import chatbot

# Alex Chen's job ID (Machine Learning Engineer)
JOB_ID = "f23abc2f-75f0-4431-a8aa-3de1cb21072c"


async def test_alex_chen_fit():
    """Test: Why is Alex Chen a good fit?"""
    print("=" * 80)
    print("TEST 1: Why is Alex Chen a good fit?")
    print("=" * 80)

    result = await chatbot.chat(
        job_id=JOB_ID,
        question="Why is Alex Chen a good fit for this role?",
        history=[]
    )

    print(f"\n[OK] Response:\n{result['response']}")
    print(f"\n[INFO] Citations: {result['citations']}")

    if result.get('error'):
        print(f"\n[ERROR] Error: {result['error']}")

    # Verify response contains expected elements
    response_lower = result['response'].lower()
    checks = {
        "Contains 'Alex Chen'": 'alex chen' in response_lower,
        "Contains 'Python'": 'python' in response_lower,
        "Contains 'PyTorch'": 'pytorch' in response_lower,
        "Not 'Information not provided'": 'information not provided' not in response_lower
    }

    print("\n[CHECK] Verification:")
    for check_name, passed in checks.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {check_name}")

    return all(checks.values())


async def test_list_all_applicants():
    """Test: List all applicants"""
    print("\n" + "=" * 80)
    print("TEST 2: List all applicants")
    print("=" * 80)

    result = await chatbot.chat(
        job_id=JOB_ID,
        question="List all applicants for this job",
        history=[]
    )

    print(f"\n[OK] Response:\n{result['response']}")

    if result.get('error'):
        print(f"\n[ERROR] Error: {result['error']}")

    # Verify response contains all 9 candidates
    expected_candidates = [
        "Sarah Chen", "Michael Rodriguez", "Emily Watson",
        "David Kim", "Priya Patel", "James Thompson",
        "Ana Martinez", "Robert Johnson", "Alex Chen"
    ]

    response_lower = result['response'].lower()
    found_candidates = []

    for candidate in expected_candidates:
        if candidate.lower() in response_lower:
            found_candidates.append(candidate)

    print(f"\n[CHECK] Verification:")
    print(f"  Expected: {len(expected_candidates)} candidates")
    print(f"  Found: {len(found_candidates)} candidates")

    for candidate in expected_candidates:
        status = "[PASS]" if candidate in found_candidates else "[FAIL]"
        print(f"  {status} {candidate}")

    return len(found_candidates) == len(expected_candidates)


async def test_count_applicants():
    """Test: How many applicants?"""
    print("\n" + "=" * 80)
    print("TEST 3: How many applicants?")
    print("=" * 80)

    result = await chatbot.chat(
        job_id=JOB_ID,
        question="How many applicants are there?",
        history=[]
    )

    print(f"\n[OK] Response:\n{result['response']}")

    if result.get('error'):
        print(f"\n[ERROR] Error: {result['error']}")

    # Verify response contains "9"
    checks = {
        "Contains '9'": '9' in result['response'],
        "Not '4'": '4' not in result['response']
    }

    print("\n[CHECK] Verification:")
    for check_name, passed in checks.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {check_name}")

    return all(checks.values())


async def main():
    """Run all tests"""
    print("\n[TEST] CHATBOT FIX VERIFICATION TESTS")
    print("=" * 80)
    print(f"Job ID: {JOB_ID}")
    print(f"Job: Machine Learning Engineer")
    print(f"Expected: 9 total applicants (including Alex Chen)")
    print("=" * 80)

    results = {}

    # Test 1: Alex Chen fit analysis
    try:
        results['alex_chen'] = await test_alex_chen_fit()
    except Exception as e:
        print(f"\n[ERROR] Test 1 failed with error: {e}")
        import traceback
        traceback.print_exc()
        results['alex_chen'] = False

    # Test 2: List all applicants
    try:
        results['list_all'] = await test_list_all_applicants()
    except Exception as e:
        print(f"\n[ERROR] Test 2 failed with error: {e}")
        import traceback
        traceback.print_exc()
        results['list_all'] = False

    # Test 3: Count applicants
    try:
        results['count'] = await test_count_applicants()
    except Exception as e:
        print(f"\n[ERROR] Test 3 failed with error: {e}")
        import traceback
        traceback.print_exc()
        results['count'] = False

    # Summary
    print("\n" + "=" * 80)
    print("[SUMMARY] TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "[PASS] PASSED" if passed else "[FAIL] FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    print("\n" + "=" * 80)
    if all_passed:
        print("[SUCCESS] ALL TESTS PASSED!")
    else:
        print("[WARNING] SOME TESTS FAILED")
    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
