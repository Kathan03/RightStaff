"""
Simplified skill extraction service.

ARCHITECTURE CHANGE (2025-11-24):
- REMOVED: "Hybrid" mode (LLM + spaCy merging)
- SIMPLIFIED: OpenAI API (primary) → Spacy (fallback)

Usage:
    from app.services.skill_extractor import extract_skills

    # Try OpenAI, fallback to spaCy
    skills = await extract_skills(text, use_openai=True)

    # Use spaCy only
    skills = await extract_skills(text, use_openai=False)
"""

from typing import List
import logging
from app.services.ontology import extract_skills_from_text, normalize_skill

logger = logging.getLogger(__name__)


async def extract_skills(
    text: str,
    use_openai: bool = True,
    normalize: bool = True
) -> List[str]:
    """
    Extract skills from text using OpenAI API (with spaCy fallback).

    Simple logic:
    1. If use_openai=True: Try OpenAI API
    2. If OpenAI fails or use_openai=False: Use spaCy
    3. Normalize all skills through ontology

    Args:
        text: Resume or job description text
        use_openai: Whether to attempt OpenAI API (default: True)
        normalize: Whether to normalize through ontology (default: True)

    Returns:
        List of canonical skill names (normalized, deduplicated, sorted)

    Example:
        skills = await extract_skills(text, use_openai=True)
        # Returns: ["AWS", "Docker", "JavaScript", "Python", "React"]
    """
    if not text or not text.strip():
        return []

    logger.info(f"Extracting skills (use_openai={use_openai})")

    # ═══════════════════════════════════════════════════════════════
    # STEP 1: Extract raw skills
    # ═══════════════════════════════════════════════════════════════
    raw_skills = []

    if use_openai:
        # Try OpenAI API first
        try:
            from app.config import settings
            if settings.use_llm_parsing and settings.openai_api_key:
                raw_skills = await _extract_openai(text)
                logger.info(f"✅ OpenAI extracted {len(raw_skills)} skills")
            else:
                logger.info("⚠️ OpenAI not configured, using spaCy")
                raw_skills = await _extract_spacy(text)
        except Exception as e:
            logger.error(f"❌ OpenAI skill extraction failed: {e}")
            logger.info("⚠️ Falling back to spaCy")
            raw_skills = await _extract_spacy(text)
    else:
        # Use spaCy directly
        raw_skills = await _extract_spacy(text)

    # ═══════════════════════════════════════════════════════════════
    # STEP 2: Normalize all skills through ontology
    # ═══════════════════════════════════════════════════════════════
    if normalize:
        normalized_skills = _normalize_skills(raw_skills)
    else:
        normalized_skills = list(set(raw_skills))
        normalized_skills.sort()

    logger.info(
        f"Extracted {len(raw_skills)} raw skills, "
        f"normalized to {len(normalized_skills)} unique skills"
    )

    return normalized_skills


async def _extract_openai(text: str) -> List[str]:
    """
    Extract skills using OpenAI API.

    Uses the OpenAI parser's skill extraction capability.
    """
    from app.services.llm_parser import get_openai_parser

    parser = get_openai_parser()

    # Parse resume (includes skills field)
    parsed = await parser.parse_resume(text)

    # Extract skills from parsed result
    skills = parsed.get("skills", [])

    if not skills:
        logger.warning("OpenAI returned no skills")

    return skills


async def _extract_spacy(text: str) -> List[str]:
    """
    Extract skills using spaCy NER + pattern matching.

    This is the baseline extraction method from ontology.py.
    """
    import asyncio

    # Run in thread pool since spaCy is CPU-bound
    skills = await asyncio.to_thread(extract_skills_from_text, text)

    if not skills:
        logger.warning("spaCy returned no skills")

    return skills


def _normalize_skills(raw_skills: List[str]) -> List[str]:
    """
    Normalize skills through ontology.

    - Maps variants to canonical names (e.g., "JS" → "JavaScript")
    - Deduplicates
    - Sorts alphabetically
    """
    normalized = set()

    for skill in raw_skills:
        if not skill or not skill.strip():
            continue

        canonical = normalize_skill(skill)
        if canonical:
            normalized.add(canonical)

    return sorted(list(normalized))
