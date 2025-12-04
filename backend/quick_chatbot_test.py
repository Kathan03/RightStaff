"""
Quick chatbot test - Run specific queries against the chatbot.
Usage: python quick_chatbot_test.py "Your question here"
"""

import asyncio
import sys
sys.path.insert(0, '.')

from app.services.chatbot_langgraph import chatbot

# Alex Chen's job ID (Machine Learning Engineer)
DEFAULT_JOB_ID = "f23abc2f-75f0-4431-a8aa-3de1cb21072c"


async def test_query(question: str, job_id: str = DEFAULT_JOB_ID):
    """Test a single chatbot query"""
    print(f"\n{'='*80}")
    print(f"Question: {question}")
    print(f"Job ID: {job_id}")
    print('='*80)

    try:
        result = await chatbot.chat(
            job_id=job_id,
            question=question,
            history=[]
        )

        print(f"\nResponse:")
        print('-'*80)
        # Use ASCII-safe printing to avoid encoding issues
        response = result['response']
        # Replace common unicode characters
        response = response.replace('✓', '[OK]').replace('✗', '[X]').replace('—', '-')
        print(response)
        print('-'*80)

        if result.get('citations'):
            print(f"\nCitations: {len(result['citations'])} candidates")

        if result.get('error'):
            print(f"\nError: {result['error']}")

        return result

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Run chatbot test"""
    if len(sys.argv) < 2:
        print("Usage: python quick_chatbot_test.py \"Your question here\"")
        print("\nExample questions:")
        print('  "Why is Alex Chen a good fit?"')
        print('  "List all applicants"')
        print('  "How many applicants have Python skills?"')
        print('  "Who is the most experienced candidate?"')
        sys.exit(1)

    question = sys.argv[1]
    job_id = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_JOB_ID

    await test_query(question, job_id)


if __name__ == "__main__":
    asyncio.run(main())
