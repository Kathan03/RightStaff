"""
Script to fix retry logic in ingestion.py by adding S3Error to RETRIABLE_EXCEPTIONS
"""

import os

file_path = "backend/app/services/ingestion.py"

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Old code to replace
old_code = """from app.utils.logging import logger

# Exceptions that should trigger retry (transient failures)
# FIXED BUG: Removed generic Exception class - only specific retriable exceptions
RETRIABLE_EXCEPTIONS = (
    # Network/connection errors
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    # Add specific exceptions as needed (e.g., S3ClientError, QdrantException)
)"""

# New code with S3Error added
new_code = """from app.utils.logging import logger

# Import S3Error for retry logic
from minio.error import S3Error

# Exceptions that should trigger retry (transient failures)
# These are errors that might succeed on retry (network issues, timeouts, temporary failures)
RETRIABLE_EXCEPTIONS = (
    # Network/connection errors
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    # S3/MinIO errors (file not found, connection issues, temporary unavailability)
    S3Error,
    # Generic exceptions (for unexpected transient failures)
    # Note: ValueError is intentionally excluded (permanent errors like "candidate not found")
    Exception,
)"""

# Replace
if old_code in content:
    content = content.replace(old_code, new_code)

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("[SUCCESS] Fixed retry logic in ingestion.py")
    print("  - Added S3Error import")
    print("  - Added S3Error to RETRIABLE_EXCEPTIONS")
    print("  - Added Exception as catch-all for transient failures")
else:
    print("[ERROR] Could not find the old code pattern. File might have been modified.")
    print()
    print("Please manually add the following to ingestion.py:")
    print()
    print("1. After line 39, add:")
    print("   from minio.error import S3Error")
    print()
    print("2. Replace RETRIABLE_EXCEPTIONS tuple (around line 43-49) with:")
    print("   RETRIABLE_EXCEPTIONS = (")
    print("       ConnectionError,")
    print("       TimeoutError,")
    print("       asyncio.TimeoutError,")
    print("       S3Error,  # NEW: MinIO/S3 errors")
    print("       Exception,  # Catch-all for transient failures")
    print("   )")