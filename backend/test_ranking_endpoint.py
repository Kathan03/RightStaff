"""Test the ranking endpoint with proper error handling."""

import requests
import json

# Test configuration
BASE_URL = "http://localhost:8000/api/v1"
JOB_ID = "062cd67d-ac26-4a2c-96bd-fba7dd3dbe8c"

def test_ranking():
    """Test the full ranking endpoint."""

    url = f"{BASE_URL}/jobs/{JOB_ID}/rank_full"
    payload = {"use_cache": False}

    print(f"Testing ranking endpoint...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("-" * 60)

    try:
        response = requests.post(url, json=payload)

        print(f"Status Code: {response.status_code}")
        print(f"\nResponse:")
        print(json.dumps(response.json(), indent=2))

        if response.status_code == 200:
            data = response.json()
            print("\n" + "=" * 60)
            print(f"SUCCESS!")
            print(f"Ranked Candidates: {len(data.get('ranked_candidates', []))}")
            print(f"High Confidence: {data.get('metadata', {}).get('high_confidence', 0)}")
            print(f"Medium Confidence: {data.get('metadata', {}).get('medium_confidence', 0)}")
            print(f"Low Confidence: {data.get('metadata', {}).get('low_confidence', 0)}")
            print("=" * 60)
        else:
            print(f"\nERROR: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to server. Is uvicorn running?")
        print("Start server with: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_ranking()
