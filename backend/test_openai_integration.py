"""
Quick test script to verify OpenAI integration works.

Run this BEFORE starting the full backend to ensure OpenAI API is accessible.
"""

import asyncio
import os
from app.services.llm_parser import get_openai_parser

# Test resume text
TEST_RESUME = """
John Doe
Software Engineer
john.doe@example.com
+1-555-0123
San Francisco, CA

PROFESSIONAL EXPERIENCE
Senior Python Developer at TechCorp (2020-Present)
- 5 years of Python development experience
- Built REST APIs with FastAPI and Django
- Deployed microservices on AWS using Docker and Kubernetes
- Led team of 4 junior developers

SKILLS
Python, Django, FastAPI, PostgreSQL, AWS, Docker, Kubernetes, React, JavaScript
"""

async def test_openai_parser():
    """Test OpenAI resume parser."""
    print("=" * 60)
    print("TESTING OPENAI API INTEGRATION")
    print("=" * 60)
    print()

    # Get parser instance
    print("1. Initializing OpenAI parser...")
    parser = get_openai_parser()
    print("   OK - Parser created")
    print()

    # Parse test resume
    print("2. Calling OpenAI API to parse resume...")
    print("   (This should take 2-5 seconds)")
    print()

    try:
        result = await parser.parse_resume(TEST_RESUME)

        print("   SUCCESS - Resume parsed!")
        print()
        print("=" * 60)
        print("PARSED RESULT:")
        print("=" * 60)
        print(f"Full Name: {result.get('full_name')}")
        print(f"Email: {result.get('email')}")
        print(f"Phone: {result.get('phone')}")
        print(f"Location: {result.get('location')}")
        print(f"Years Experience: {result.get('years_experience')}")
        print(f"Summary: {result.get('professional_summary', '')[:100]}...")
        print(f"Skills ({len(result.get('skills', []))}): {', '.join(result.get('skills', [])[:10])}")
        print()
        print("=" * 60)
        print("TEST PASSED - OpenAI integration works!")
        print("=" * 60)
        print()
        print("Next step: Start the backend server")
        print("  cd backend")
        print("  ../venv/Scripts/python -m uvicorn app.main:app --reload")

    except Exception as e:
        print(f"   FAILED - {e}")
        print()
        print("Troubleshooting:")
        print("1. Check OPENAI_API_KEY in .env file")
        print("2. Verify API key is valid at https://platform.openai.com/api-keys")
        print("3. Check internet connection")
        print("4. Check OpenAI API status: https://status.openai.com/")


if __name__ == "__main__":
    asyncio.run(test_openai_parser())
