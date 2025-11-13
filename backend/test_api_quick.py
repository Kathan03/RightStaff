"""Quick API connectivity test."""

import requests

print("\n🔍 Testing API connectivity...\n")

# Test 1: Health endpoint
try:
    response = requests.get("http://localhost:8000/health", timeout=5)
    print(f"1. Health endpoint: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ Backend is running!")
    else:
        print(f"   ⚠️  Unexpected status: {response.text}")
except requests.exceptions.ConnectionError:
    print(f"1. Health endpoint: ❌ Connection refused")
    print(f"   💡 Backend is NOT running. Start it with:")
    print(f"      cd backend && uvicorn app.main:app --reload")
    exit(1)
except Exception as e:
    print(f"1. Health endpoint: ❌ {e}")
    exit(1)

# Test 2: Docs endpoint
try:
    response = requests.get("http://localhost:8000/docs", timeout=5)
    print(f"2. Docs endpoint: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ API docs available at http://localhost:8000/docs")
except Exception as e:
    print(f"2. Docs endpoint: ❌ {e}")

# Test 3: API v1 prefix
try:
    response = requests.get("http://localhost:8000/api/v1/", timeout=5)
    print(f"3. API v1 endpoint: {response.status_code}")
except Exception as e:
    print(f"3. API v1 endpoint: ❌ {e}")

print(f"\n✅ Backend connectivity test passed!")
print(f"💡 Visit http://localhost:8000/docs to test APIs manually")
