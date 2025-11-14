"""
Document parsing utilities for resumes and job descriptions.
Supports PDF, DOCX, and plain text formats using Unstructured library.
"""

from typing import Optional, Dict, List, Any
import logging
import io
import tempfile
from pathlib import Path

# Document parsing libraries
from unstructured.partition.auto import partition
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.text import partition_text

logger = logging.getLogger(__name__)


async def parse_resume(resume_bytes: bytes, filename: str) -> dict:
    """
    Parse resume from bytes (PDF/DOCX/TXT) and extract clean text.
    
    This is the entry point for resume parsing. It:
    1. Detects file format from filename extension
    2. Writes bytes to temporary file (Unstructured requires file path)
    3. Uses appropriate Unstructured parser
    4. Extracts and cleans text content
    5. Returns structured result with text and metadata
    
    Args:
        resume_bytes: File content as bytes
        filename: Original filename (e.g., "s3://bucket/resume.pdf" or "resume.pdf")
    
    Returns:
        {
            "text": str,           # Extracted text content
            "metadata": {
                "filename": str,
                "size_bytes": int,
                "format": str,     # "pdf", "docx", "txt"
                "page_count": int, # For PDFs
                "char_count": int
            }
        }
    
    Raises:
        ValueError: If file format is unsupported
        Exception: If parsing fails
    
    Why temporary file?
    - Unstructured library requires file paths, not bytes
    - tempfile.NamedTemporaryFile handles cleanup automatically
    - delete=False allows Unstructured to read after write
    """
    try:
        # Extract file extension from filename (handle S3 URLs)
        if filename.startswith("s3://"):
            # Extract filename from S3 URL: s3://bucket/path/to/resume.pdf -> resume.pdf
            filename = filename.split("/")[-1]
        
        file_ext = Path(filename).suffix.lower()
        
        logger.info(f"Parsing resume: {filename} (format: {file_ext}, size: {len(resume_bytes)} bytes)")
        
        # Write bytes to temporary file
        # Why? Unstructured requires file paths, not in-memory bytes
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(resume_bytes)
            tmp_path = tmp_file.name
        
        try:
            # Parse based on file type
            if file_ext == ".pdf":
                elements = partition_pdf(
                    filename=tmp_path,
                    # Strategy options:
                    # - "fast": OCR disabled, quick extraction
                    # - "hi_res": OCR enabled, slower but better for scanned PDFs
                    # - "auto": Chooses based on content
                    strategy="fast",  # MVP: prioritize speed over OCR
                    # Extract images? No, we only need text for embeddings
                    extract_images_in_pdf=False,
                    # Include page breaks in output?
                    include_page_breaks=False
                )
                format_type = "pdf"
                
            elif file_ext in [".docx", ".doc"]:
                elements = partition_docx(filename=tmp_path)
                format_type = "docx"
                
            elif file_ext == ".txt":
                elements = partition_text(filename=tmp_path)
                format_type = "txt"
                
            else:
                # Fallback: try auto-detection
                logger.warning(f"Unknown file type {file_ext}, attempting auto-detection")
                elements = partition(filename=tmp_path)
                format_type = "unknown"
            
            # Extract text from elements
            # Unstructured returns a list of elements (paragraphs, titles, etc.)
            # We join them with double newlines to preserve structure
            text_parts = [str(element) for element in elements]
            text = "\n\n".join(text_parts).strip()
            
            # Clean up text (remove excessive whitespace)
            # Why? Multi-page PDFs often have weird spacing
            import re
            text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
            text = re.sub(r' {2,}', ' ', text)      # Max 1 space between words
            
            # Count pages (for PDFs)
            page_count = len(set(el.metadata.page_number for el in elements 
                               if hasattr(el, 'metadata') and hasattr(el.metadata, 'page_number')))
            
            logger.info(f"✅ Parsed {filename}: {len(text)} chars, {page_count or 'N/A'} pages")
            
            return {
                "text": text,
                "metadata": {
                    "filename": filename,
                    "size_bytes": len(resume_bytes),
                    "format": format_type,
                    "page_count": page_count if page_count > 0 else None,
                    "char_count": len(text)
                }
            }
        
        finally:
            # Clean up temporary file
            Path(tmp_path).unlink(missing_ok=True)
    
    except Exception as e:
        logger.error(f"❌ Error parsing {filename}: {e}")
        raise ValueError(f"Failed to parse resume: {str(e)}") from e


def chunk_text(
    text: str,
    chunk_size: int = 400,
    chunk_overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    Split text into overlapping chunks for embedding.
    
    This implements semantic-aware chunking:
    1. Respects sentence boundaries (doesn't cut mid-sentence)
    2. Maintains overlap for context continuity
    3. Includes rich metadata for each chunk
    
    Why chunking?
    - Embedding models have token limits (512 for all-MiniLM-L6-v2)
    - Smaller chunks = more precise semantic search
    - Overlap ensures no context is lost at boundaries
    
    Why 400 chars?
    - ~100 tokens for typical English text
    - Leaves room for special tokens in embedding model
    - Fast to process, good granularity for search
    
    Args:
        text: Input text to chunk
        chunk_size: Target chunk size in characters (not strict, respects sentences)
        chunk_overlap: Number of overlapping characters between chunks
    
    Returns:
        List of chunk dictionaries:
        [
            {
                "text": str,          # Chunk content
                "start_char": int,    # Start position in original text
                "end_char": int,      # End position in original text
                "chunk_index": int,   # Sequential index (0, 1, 2, ...)
                "char_count": int     # Length of chunk
            },
            ...
        ]
    
    Example:
        text = "This is sentence one. This is sentence two. This is sentence three."
        chunks = chunk_text(text, chunk_size=30, chunk_overlap=10)
        # Returns chunks respecting sentence boundaries with 10-char overlap
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for chunking")
        return []
    
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        # Calculate end position
        end = start + chunk_size
        
        # If this is not the last chunk, try to break at sentence boundary
        if end < text_len:
            # Look for sentence endings: period, question mark, exclamation, newline
            # Search backwards from end position
            chunk_text_segment = text[start:end]
            
            # Find the last sentence boundary in the chunk
            last_period = chunk_text_segment.rfind(". ")
            last_question = chunk_text_segment.rfind("? ")
            last_exclaim = chunk_text_segment.rfind("! ")
            last_newline = chunk_text_segment.rfind("\n")
            
            # Get the furthest sentence boundary
            break_point = max(last_period, last_question, last_exclaim, last_newline)
            
            # Only break at sentence if it's not too early in the chunk
            # (we don't want chunks that are too small)
            min_chunk_size = chunk_size // 2  # At least 50% of target size
            if break_point > min_chunk_size:
                # Move end to after the punctuation/newline
                end = start + break_point + 1
        
        # Extract chunk text
        chunk_text_final = text[start:end].strip()
        
        # Only add non-empty chunks
        if chunk_text_final:
            chunks.append({
                "text": chunk_text_final,
                "start_char": start,
                "end_char": end,
                "chunk_index": len(chunks),
                "char_count": len(chunk_text_final)
            })
        
        # Move start position for next chunk (with overlap)
        # Why subtract overlap? So chunks share some context
        start = end - chunk_overlap
        
        # Safety: prevent infinite loop if overlap >= chunk_size
        if chunks and start <= chunks[-1]["start_char"]:
            start = end
    
    logger.info(f"Split text into {len(chunks)} chunks (avg size: {sum(c['char_count'] for c in chunks) // len(chunks) if chunks else 0} chars)")
    
    return chunks


def extract_metadata(text: str) -> Dict[str, Any]:
    """
    Extract metadata from resume text (name, email, phone, etc.).
    
    TODO: Implement for Days 5-8 (when building ranking features)
    - Use regex to extract email, phone
    - Use spaCy NER to extract name, location
    - Parse education section (degrees, universities)
    - Parse work experience (companies, titles, dates)
    - Calculate total years of experience
    
    For now, returns empty structure (not needed for Day 2 pipeline).
    """
    logger.debug("extract_metadata not yet implemented (scheduled for Days 5-8)")
    return {
        "name": None,
        "email": None,
        "phone": None,
        "location": None,
        "years_experience": None,
        "education": [],
        "work_history": []
    }
