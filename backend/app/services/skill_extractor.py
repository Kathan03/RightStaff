"""
Unified skill extraction service.

Provides consistent skill extraction interface that can use:
- LLM (Qwen/Phi-2) for context-aware extraction
- spaCy NER + patterns for traditional extraction
- Hybrid mode (both LLM + spaCy)

All methods return the same normalized, deduplicated, sorted skill list.

Usage:
    from app.services.skill_extractor import extract_skills

    # Hybrid (LLM + spaCy)
    skills = await extract_skills(text, method="hybrid")

    # LLM only
    skills = await extract_skills(text, method="llm")

    # spaCy only
    skills = await extract_skills(text, method="spacy")
"""

from typing import List, Literal
import logging
from app.services.ontology import extract_skills_from_text, normalize_skill

logger = logging.getLogger(__name__)

# Type hint for extraction methods
SkillExtractionMethod = Literal["hybrid", "llm", "spacy"]


async def extract_skills(
    text: str,
    method: SkillExtractionMethod = "hybrid",
    normalize: bool = True
) -> List[str]:
    """
    Extract skills from text using specified method.

    This is the UNIFIED interface for skill extraction.
    All methods return the same format: List[str] of normalized, sorted skills.

    Args:
        text: Resume or job description text
        method: Extraction method
            - "hybrid": LLM + spaCy (best accuracy, slower)
            - "llm": LLM only (good accuracy, fast)
            - "spacy": spaCy + patterns only (baseline, fastest)
        normalize: Whether to normalize through ontology (default: True)

    Returns:
        List of canonical skill names (normalized, deduplicated, sorted)

    Example:
        skills = await extract_skills(text, method="hybrid")
        # Returns: ["AWS", "Docker", "JavaScript", "Python", "React"]
    """
    if not text or not text.strip():
        return []

    logger.info(f"Extracting skills using method: {method}")

    # ═══════════════════════════════════════════════════════════════
    # STEP 1: Extract raw skills based on method
    # ═══════════════════════════════════════════════════════════════
    raw_skills = []

    if method == "hybrid":
        # Use both LLM and spaCy
        raw_skills = await _extract_hybrid(text)

    elif method == "llm":
        # Use LLM only
        raw_skills = await _extract_llm(text)

    elif method == "spacy":
        # Use spaCy + patterns only
        raw_skills = await _extract_spacy(text)

    else:
        logger.error(f"Unknown method: {method}. Falling back to spaCy.")
        raw_skills = await _extract_spacy(text)

    # ═══════════════════════════════════════════════════════════════
    # STEP 2: Normalize all skills through ontology (same for all methods)
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


async def _extract_hybrid(text: str) -> List[str]:
    """
    Extract skills using both LLM and spaCy.

    Workflow:
    1. LLM extracts context-aware skills
    2. spaCy extracts pattern-based skills
    3. Merge both lists

    Returns:
        Raw list of skills (may have duplicates, variants)
    """
    from app.config import settings

    skills = []

    # Get LLM skills
    try:
        from app.services.llm_parser import get_llm_parser

        llm_parser = get_llm_parser()
        llm_result = await llm_parser.parse_resume(text)
        llm_skills = llm_result.get("skills", [])

        logger.debug(f"LLM extracted {len(llm_skills)} skills")
        skills.extend(llm_skills)
    except Exception as e:
        logger.warning(f"LLM skill extraction failed: {e}")

    # Get spaCy skills
    spacy_skills = await extract_skills_from_text(text)
    logger.debug(f"spaCy extracted {len(spacy_skills)} skills")
    skills.extend(spacy_skills)

    return skills


async def _extract_llm(text: str) -> List[str]:
    """
    Extract skills using LLM only.

    Returns:
        Raw list of skills from LLM
    """
    try:
        from app.services.llm_parser import get_llm_parser

        llm_parser = get_llm_parser()
        llm_result = await llm_parser.parse_resume(text)
        llm_skills = llm_result.get("skills", [])

        logger.debug(f"LLM extracted {len(llm_skills)} skills")
        return llm_skills
    except Exception as e:
        logger.error(f"LLM skill extraction failed: {e}")
        return []


async def _extract_spacy(text: str) -> List[str]:
    """
    Extract skills using spaCy + patterns only.

    Returns:
        Raw list of skills from spaCy
    """
    spacy_skills = await extract_skills_from_text(text)
    logger.debug(f"spaCy extracted {len(spacy_skills)} skills")
    return spacy_skills


def _normalize_skills(raw_skills: List[str]) -> List[str]:
    """
    Normalize skills through ontology taxonomy.

    This is the SHARED normalization pipeline for ALL extraction methods.

    Workflow:
    1. For each raw skill, get canonical form from taxonomy
    2. Deduplicate canonical skills
    3. Sort alphabetically

    Args:
        raw_skills: Raw skill list (may have duplicates, variants)

    Returns:
        Normalized skill list (canonical forms, deduplicated, sorted)

    Example:
        raw = ["Python", "python3", "JS", "javascript", "AWS", "aws"]
        normalized = _normalize_skills(raw)
        # Returns: ["AWS", "JavaScript", "Python"]
    """
    if not raw_skills:
        return []

    normalized = []
    seen_canonical = set()

    for skill in raw_skills:
        # Get canonical form through ontology taxonomy
        canonical = normalize_skill(skill, use_taxonomy=True)

        # Add to result if not seen before
        if canonical not in seen_canonical:
            normalized.append(canonical)
            seen_canonical.add(canonical)

    # Sort for consistency
    normalized.sort()

    logger.debug(
        f"Normalized {len(raw_skills)} raw skills to "
        f"{len(normalized)} canonical skills"
    )

    return normalized


# ═══════════════════════════════════════════════════════════════
# Configuration helpers
# ═══════════════════════════════════════════════════════════════

def get_default_method() -> SkillExtractionMethod:
    """
    Get default skill extraction method from config.

    Returns:
        "hybrid" if LLM enabled, "spacy" otherwise
    """
    from app.config import settings

    if settings.use_llm_parsing:
        return "hybrid"
    else:
        return "spacy"


async def extract_skills_auto(text: str, normalize: bool = True) -> List[str]:
    """
    Extract skills using method from config.

    Convenience function that reads USE_LLM_PARSING from config
    and chooses the appropriate method automatically.

    Args:
        text: Resume or job description text
        normalize: Whether to normalize (default: True)

    Returns:
        List of canonical skill names

    Example:
        # Automatically uses config setting
        skills = await extract_skills_auto(text)
    """
    method = get_default_method()
    return await extract_skills(text, method=method, normalize=normalize)
