"""
Quick validation script for LLM parser.

Usage:
    python test_llm_parser_quick.py
"""

import asyncio
import sys
import time


async def test_llm_parser():
    """Test LLM parser with sample resume."""
    print("=" * 80)
    print("LLM PARSER VALIDATION TEST")
    print("=" * 80)
    print()

    # Sample resume
    sample_resume = """
    John Doe
    Senior Software Engineer
    john.doe@example.com | (555) 123-4567
    San Francisco, CA 94105

    SUMMARY
    Experienced software engineer with 10+ years in Python development and cloud architecture.
    Proven track record of building scalable systems and leading engineering teams.

    EXPERIENCE
    Google Inc. | Senior Software Engineer | January 2018 - Present
    - Led microservices development team of 8 engineers
    - Architected cloud solutions on AWS and GCP
    - Improved system performance by 40%

    Microsoft | Software Engineer | June 2015 - December 2017
    - Developed enterprise applications using .NET and Azure
    - Implemented CI/CD pipelines

    Amazon | Junior Engineer | May 2013 - May 2015
    - Built e-commerce backend services
    - Worked with large-scale distributed systems

    SKILLS
    Python, JavaScript, AWS, Docker, Kubernetes, FastAPI, PostgreSQL, React, Redis, CI/CD
    """

    try:
        print("📦 Importing LLM parser...")
        from app.services.llm_parser import get_llm_parser

        print("✅ Import successful\n")

        print("🤖 Getting LLM parser instance (lazy loading)...")
        parser = get_llm_parser()
        print(f"✅ Parser instance created: {type(parser).__name__}\n")

        print("🔄 Parsing sample resume...")
        print("   (This may take 20-30 seconds on first run due to model loading)")
        print()

        start_time = time.time()
        result = await parser.parse_resume(sample_resume)
        elapsed_time = time.time() - start_time

        print("=" * 80)
        print("PARSING RESULTS")
        print("=" * 80)
        print(f"⏱️  Parse time: {elapsed_time:.2f} seconds")
        print()

        print(f"Full Name: {result.get('full_name')}")
        print(f"Email: {result.get('email')}")
        print(f"Phone: {result.get('phone')}")
        print(f"Location: {result.get('location')}")
        print(f"Years Experience: {result.get('years_experience')}")
        print(f"Professional Summary: {result.get('professional_summary', 'N/A')[:100]}...")
        print(f"Skills ({len(result.get('skills', []))}): {', '.join(result.get('skills', [])[:10])}")
        if len(result.get('skills', [])) > 10:
            print(f"          ... and {len(result.get('skills', [])) - 10} more")
        print()

        # Validation checks
        print("=" * 80)
        print("VALIDATION CHECKS")
        print("=" * 80)

        checks = []
        checks.append(("Full name extracted", result.get('full_name') is not None))
        checks.append(("Email extracted correctly", result.get('email') == "john.doe@example.com"))
        checks.append(("Phone extracted", result.get('phone') is not None))
        checks.append(("Years of experience calculated", result.get('years_experience') is not None))
        if result.get('years_experience') is not None:
            checks.append((
                "Years in reasonable range (8-12)",
                8 <= result.get('years_experience') <= 12
            ))
        checks.append(("Skills extracted", len(result.get('skills', [])) > 0))
        checks.append(("Professional summary generated", result.get('professional_summary') is not None))
        checks.append(("Parse time acceptable (<30s)", elapsed_time < 30))

        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"{status} {check_name}")

        print()

        all_passed = all(passed for _, passed in checks)
        if all_passed:
            print("=" * 80)
            print("🎉 ALL VALIDATION CHECKS PASSED!")
            print("=" * 80)
            return 0
        else:
            print("=" * 80)
            print("⚠️  SOME VALIDATION CHECKS FAILED")
            print("=" * 80)
            return 1

    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\nMissing dependencies. Install with:")
        print("  pip install transformers torch accelerate")
        return 1

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


async def test_config():
    """Test configuration settings."""
    print("\n" + "=" * 80)
    print("CONFIGURATION CHECK")
    print("=" * 80)

    try:
        from app.config import settings

        print(f"USE_LLM_PARSING: {settings.use_llm_parsing}")
        print(f"LLM_PARSER_MODEL: {settings.llm_parser_model}")
        print()

        if not settings.use_llm_parsing:
            print("⚠️  WARNING: LLM parsing is disabled in config!")
            print("   Set USE_LLM_PARSING=true to enable")

        return 0

    except Exception as e:
        print(f"❌ Config check failed: {e}")
        return 1


async def main():
    """Run all validation tests."""
    print("\n")
    print("=" * 80)
    print(" " * 20 + "RightStaff LLM Parser Validation")
    print("=" * 80)
    print()

    # Test 1: Configuration
    config_result = await test_config()

    # Test 2: LLM Parser
    parser_result = await test_llm_parser()

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    if config_result == 0 and parser_result == 0:
        print("✅ All tests passed!")
        print("\nNext steps:")
        print("1. Run full test suite: pytest tests/test_llm_parser.py -v")
        print("2. Test with real resumes via API")
        print("3. Monitor performance and accuracy")
        return 0
    else:
        print("❌ Some tests failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
