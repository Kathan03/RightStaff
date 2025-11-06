"""
S3-compatible client for MinIO (MVP) / AWS S3 (production).
Handles resume file uploads and downloads.
"""
from minio import Minio
from minio.error import S3Error
from app.config import settings
from app.utils.logging import logger
import io

class S3Client:
    """MinIO/S3 client for resume file storage."""

    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl
        )
        self.bucket_name = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Create bucket if it doesn't exist (idempotent)."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
            else:
                logger.info(f"MinIO bucket exists: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket: {e}")
            raise

    async def download_file(self, s3_url: str) -> bytes:
        """
        Download a file from MinIO/S3.

        Args:
            s3_url: Format s3://bucket-name/path/to/file.pdf

        Returns:
            File content as bytes

        Raises:
            S3Error: If download fails
        """
        try:
            # Parse S3 URL: s3://bucket/key/path
            if not s3_url.startswith("s3://"):
                raise ValueError(f"Invalid S3 URL format: {s3_url}")

            parts = s3_url.replace("s3://", "").split("/", 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else ""

            logger.info(f"Downloading from bucket={bucket}, key={key}")

            response = self.client.get_object(bucket, key)
            data = response.read()
            response.close()
            response.release_conn()

            logger.info(f"Downloaded {len(data)} bytes from {s3_url}")
            return data

        except S3Error as e:
            logger.error(f"Error downloading {s3_url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading {s3_url}: {e}")
            raise

    async def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/pdf"
    ) -> str:
        """
        Upload a file to MinIO/S3.

        Args:
            file_data: File content as bytes
            object_name: Path/filename in bucket (e.g., "resumes/candidate_123.pdf")
            content_type: MIME type

        Returns:
            S3 URL of uploaded file
        """
        try:
            self.client.put_object(
                self.bucket_name,
                object_name,
                io.BytesIO(file_data),
                length=len(file_data),
                content_type=content_type
            )
            s3_url = f"s3://{self.bucket_name}/{object_name}"
            logger.info(f"Uploaded {object_name} to MinIO ({len(file_data)} bytes)")
            return s3_url
        except S3Error as e:
            logger.error(f"Error uploading {object_name}: {e}")
            raise

# Singleton instance
s3_client = S3Client()
