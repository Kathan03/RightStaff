"""
Quick test to verify the health endpoint returns correct format for frontend.
"""
import asyncio
import json
from app.main import app
from fastapi.testclient import TestClient

# Create test client
client = TestClient(app)

def test_health_endpoint():
    """Test health endpoint returns correct format."""
    print("Testing /health endpoint...")
    print("=" * 60)

    response = client.get("/health")

    print(f"\nHTTP Status: {response.status_code}")
    print(f"\nResponse Body:")
    data = response.json()
    print(json.dumps(data, indent=2))

    # Validate format
    print("\n" + "=" * 60)
    print("Validation:")

    required_fields = ["status", "services", "timestamp"]
    for field in required_fields:
        if field in data:
            print(f"  ✓ Has '{field}' field")
        else:
            print(f"  ✗ Missing '{field}' field")

    if "services" in data:
        print(f"\n  Services found: {list(data['services'].keys())}")

        expected_services = ["api", "database", "qdrant", "redis", "minio"]
        for svc in expected_services:
            if svc in data["services"]:
                status = data["services"][svc]
                print(f"    - {svc}: {status}")
            else:
                print(f"    - {svc}: MISSING!")

    # Check status field
    if "status" in data:
        if data["status"] in ["healthy", "unhealthy"]:
            print(f"\n  ✓ Status is valid: '{data['status']}'")
        else:
            print(f"\n  ✗ Status has invalid value: '{data['status']}'")

    print("\n" + "=" * 60)
    if response.status_code == 200 and "status" in data and "services" in data:
        print("✓ PASSED: Endpoint format matches frontend expectations!")
        return True
    else:
        print("✗ FAILED: Endpoint format doesn't match frontend!")
        return False

if __name__ == "__main__":
    success = test_health_endpoint()
    exit(0 if success else 1)
