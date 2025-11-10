"""
Clean up ingestion.py - remove duplicates and ensure proper formatting
"""

file_path = "backend/app/services/ingestion.py"

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove duplicate S3Error imports
while "from minio.error import S3Error\n\n# Import S3Error for retry logic\nfrom minio.error import S3Error" in content:
    content = content.replace(
        "from minio.error import S3Error\n\n# Import S3Error for retry logic\nfrom minio.error import S3Error",
        "from minio.error import S3Error"
    )

# Remove duplicate RETRIABLE_EXCEPTIONS comments
content = content.replace(
    "# Exceptions that should trigger retry (transient failures)\n# These are errors that might succeed on retry (network issues, timeouts, temporary failures)\n# Exceptions that should trigger retry (transient failures)\n# These are errors that might succeed on retry (network issues, timeouts, temporary failures)",
    "# Exceptions that should trigger retry (transient failures)\n# These are errors that might succeed on retry (network issues, timeouts, temporary failures)"
)

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("[SUCCESS] Cleaned up ingestion.py")
print("  - Removed duplicate imports")
print("  - File is ready to use")
