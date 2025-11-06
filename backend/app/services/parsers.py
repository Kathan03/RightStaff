"""
Document parsing utilities for resumes and job descriptions.
Supports PDF, DOCX, and plain text formats.
"""

from typing import Optional, Dict, List
import logging
from pathlib import Path

# Document parsing libraries
from PyPDF2 import PdfReader
from docx import Document
from unstructured.partition.auto import partition

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parse resumes and job descriptions from various formats."""

    @staticmethod
    def parse_pdf(file_path: str) -> str:
        """
        Parse PDF file to text.

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text
        """
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            logger.info(f"Successfully parsed PDF: {file_path}")
            return text.strip()
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {e}")
            raise

    @staticmethod
    def parse_docx(file_path: str) -> str:
        """
        Parse DOCX file to text.

        Args:
            file_path: Path to DOCX file

        Returns:
            Extracted text
        """
        try:
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            logger.info(f"Successfully parsed DOCX: {file_path}")
            return text.strip()
        except Exception as e:
            logger.error(f"Error parsing DOCX {file_path}: {e}")
            raise

    @staticmethod
    def parse_with_unstructured(file_path: str) -> str:
        """
        Parse document using Unstructured library (supports many formats).

        Args:
            file_path: Path to document

        Returns:
            Extracted text
        """
        try:
            elements = partition(filename=file_path)
            text = "\n".join([str(el) for el in elements])
            logger.info(f"Successfully parsed with unstructured: {file_path}")
            return text.strip()
        except Exception as e:
            logger.error(f"Error parsing with unstructured {file_path}: {e}")
            raise

    @classmethod
    def parse_document(cls, file_path: str) -> str:
        """
        Auto-detect format and parse document.

        Args:
            file_path: Path to document

        Returns:
            Extracted text
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return cls.parse_pdf(file_path)
        elif suffix in [".docx", ".doc"]:
            return cls.parse_docx(file_path)
        elif suffix == ".txt":
            return path.read_text(encoding="utf-8")
        else:
            # Try unstructured for other formats
            return cls.parse_with_unstructured(file_path)


def chunk_text(
    text: str,
    chunk_size: int = 400,
    chunk_overlap: int = 50
) -> List[Dict[str, any]]:
    """
    Split text into overlapping chunks for embedding.

    Args:
        text: Input text
        chunk_size: Maximum chunk size in characters
        chunk_overlap: Overlap between chunks

    Returns:
        List of chunk dictionaries with text and metadata
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]

        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk_text.rfind(".")
            last_newline = chunk_text.rfind("\n")
            break_point = max(last_period, last_newline)

            if break_point > chunk_size // 2:  # Only if not too short
                end = start + break_point + 1
                chunk_text = text[start:end]

        chunks.append({
            "text": chunk_text.strip(),
            "start_char": start,
            "end_char": end,
            "chunk_index": len(chunks)
        })

        start = end - chunk_overlap

    logger.info(f"Split text into {len(chunks)} chunks")
    return chunks


def extract_metadata(text: str) -> Dict[str, any]:
    """
    Extract metadata from resume text.

    Args:
        text: Resume text

    Returns:
        Dictionary with extracted metadata

    TODO: Implement for Days 5-8
    - Extract name, email, phone using regex
    - Extract education (degrees, universities)
    - Extract work experience (companies, titles, dates)
    - Extract years of experience
    - Extract location
    """
    logger.warning("extract_metadata not yet implemented - returning empty dict")
    return {
        "name": None,
        "email": None,
        "phone": None,
        "location": None,
        "years_experience": None,
        "education": [],
        "work_history": []
    }


async def parse_resume(resume_bytes: bytes, filename: str) -> dict:
    """
    Parse resume PDF/DOCX and extract text.

    Args:
        resume_bytes: File content as bytes
        filename: Original filename (for format detection)

    Returns:
        {"text": str, "metadata": dict}
    """
    try:
        # TODO (Day 3): Implement with Unstructured library
        # For now, return placeholder
        text = f"Placeholder text extracted from {filename}"

        logger.info(f"Parsed {filename} ({len(resume_bytes)} bytes)")

        return {
            "text": text,
            "metadata": {
                "filename": filename,
                "size_bytes": len(resume_bytes)
            }
        }
    except Exception as e:
        logger.error(f"Error parsing {filename}: {e}")
        raise
