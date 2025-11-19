"""
Simple LLM parser test (no emojis for Windows compatibility).
"""

import asyncio
import time


async def main():
    """Test LLM parser."""
    print("\n" + "=" * 80)
    print("LLM PARSER TEST")
    print("=" * 80 + "\n")

    sample_resume = """
    John Doe
    Senior Software Engineer
    john.doe@example.com | (555) 123-4567
    San Francisco, CA 94105

    SUMMARY
    Experienced software engineer with 10+ years in Python development.

    EXPERIENCE
    Google Inc. | Senior Engineer | January 2018 - Present
    - Led microservices team

    Microsoft | Engineer | June 2015 - December 2017
    - Developed enterprise applications

    SKILLS
    Python, JavaScript, AWS, Docker, Kubernetes, FastAPI
    """

    try:
        print("[1/3] Importing LLM parser...")
        from app.services.llm_parser import get_llm_parser
        print("      SUCCESS - Import complete\n")

        print("[2/3] Getting parser instance...")
        parser = get_llm_parser()
        print("      SUCCESS - Parser ready\n")

        print("[3/3] Parsing resume (may take 20-30s for first run)...")
        start_time = time.time()
        result = await parser.parse_resume(sample_resume)
        elapsed = time.time() - start_time
        print(f"      SUCCESS - Parsed in {elapsed:.2f}s\n")

        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(f"Full Name:     {result.get('full_name')}")
        print(f"Email:         {result.get('email')}")
        print(f"Phone:         {result.get('phone')}")
        print(f"Location:      {result.get('location')}")
        print(f"Years Exp:     {result.get('years_experience')}")
        print(f"Skills:        {len(result.get('skills', []))} found")
        print(f"               {', '.join(result.get('skills', [])[:5])}")
        print()

        # Validation
        print("=" * 80)
        print("VALIDATION")
        print("=" * 80)
        checks = [
            ("Name extracted", result.get('full_name') is not None),
            ("Email correct", result.get('email') == "john.doe@example.com"),
            ("Years calculated", result.get('years_experience') is not None),
            ("Skills found", len(result.get('skills', [])) > 0),
            ("Time OK (<30s)", elapsed < 30),
        ]

        for name, passed in checks:
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status} {name}")

        print()
        if all(p for _, p in checks):
            print("ALL CHECKS PASSED!")
            return 0
        else:
            print("SOME CHECKS FAILED")
            return 1

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
