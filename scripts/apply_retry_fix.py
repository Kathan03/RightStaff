"""
Apply retry logic fix to ingestion.py
Adds S3Error to RETRIABLE_EXCEPTIONS
"""

file_path = "backend/app/services/ingestion.py"

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and modify the relevant lines
output_lines = []
i = 0
while i < len(lines):
    line = lines[i]

    # Add import after "from app.utils.logging import logger"
    if "from app.utils.logging import logger" in line:
        output_lines.append(line)
        # Add blank line and S3Error import
        output_lines.append("\n")
        output_lines.append("# Import S3Error for retry logic\n")
        output_lines.append("from minio.error import S3Error\n")
        i += 1
        continue

    # Replace RETRIABLE_EXCEPTIONS section
    if "RETRIABLE_EXCEPTIONS = (" in line:
        # Skip old definition until we find the closing )
        output_lines.append("# Exceptions that should trigger retry (transient failures)\n")
        output_lines.append("# These are errors that might succeed on retry (network issues, timeouts, temporary failures)\n")
        output_lines.append("RETRIABLE_EXCEPTIONS = (\n")
        output_lines.append("    # Network/connection errors\n")
        output_lines.append("    ConnectionError,\n")
        output_lines.append("    TimeoutError,\n")
        output_lines.append("    asyncio.TimeoutError,\n")
        output_lines.append("    # S3/MinIO errors (file not found, connection issues, temporary unavailability)\n")
        output_lines.append("    S3Error,\n")
        output_lines.append("    # Generic exceptions (for unexpected transient failures)\n")
        output_lines.append("    # Note: ValueError is intentionally excluded (permanent errors like 'candidate not found')\n")
        output_lines.append("    Exception,\n")
        output_lines.append(")\n")

        # Skip until we find the closing )
        i += 1
        while i < len(lines) and not lines[i].strip().startswith(")"):
            i += 1
        i += 1  # Skip the ) line
        continue

    output_lines.append(line)
    i += 1

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(output_lines)

print("[SUCCESS] Applied retry logic fix to ingestion.py")
print("  - Added: from minio.error import S3Error")
print("  - Added S3Error to RETRIABLE_EXCEPTIONS")
print("  - Added Exception as catch-all")
print()
print("Please restart FastAPI server to apply changes:")
print("  1. Stop server (Ctrl+C)")
print("  2. Restart: uvicorn app.main:app --reload")