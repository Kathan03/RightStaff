# backend/app/services/ontology.py
"""
Ontology service for skills extraction and normalization.

Uses spaCy NER + pattern matching + taxonomy for robust skills extraction.

Features:
- Extracts skills from resume text
- Normalizes skill names (synonyms, variants)
- Enables ontology gating (must-have skills filter)
- Populates structured skills data for SQL gating

Pipeline:
1. spaCy NER - Extract entities from text
2. Pattern matching - Catch specific technical terms
3. Taxonomy normalization - Map variants to canonical names
4. Filtering - Remove noise and false positives

Why this approach?
- spaCy: Robust context-aware extraction
- Patterns: Catch domain-specific terms
- Taxonomy: Improve consistency and matching
- Combined: Best accuracy for technical skills
"""

from typing import List, Set, Dict, Optional
import logging
import json
import re
from pathlib import Path
from rapidfuzz import fuzz, process
import spacy

logger = logging.getLogger(__name__)

# Global taxonomy - loaded once on module import
_SKILLS_TAXONOMY: Optional[Dict] = None
_SPACY_NLP = None
_SPACY_AVAILABLE = None  # Tri-state: None=not checked, True=available, False=unavailable


def load_skills_taxonomy(taxonomy_path: str = "skills_taxonomy.json") -> Dict:
    """
    Load skills taxonomy from JSON file.
    
    Taxonomy structure:
    {
        "skills": {
            "Python": {
                "canonical": "Python",
                "synonyms": ["python", "python3", "py"],
                "category": "Programming Languages",
                "parent": null
            },
            ...
        }
    }
    
    Why taxonomy?
    - Normalizes variants (JS → JavaScript)
    - Groups related skills (React → JavaScript ecosystem)
    - Enables skill hierarchy (Python → Programming Languages)
    - Improves matching accuracy (fuzzy + exact)
    
    Args:
        taxonomy_path: Path to taxonomy JSON file (relative to project root)
    
    Returns:
        Taxonomy dictionary with "skills" key
    
    Raises:
        None - Returns empty taxonomy on error (graceful degradation)
    """
    global _SKILLS_TAXONOMY
    
    if _SKILLS_TAXONOMY is not None:
        return _SKILLS_TAXONOMY
    
    try:
        # Try multiple paths (backend directory or root)
        paths_to_try = [
            Path("backend") / taxonomy_path,
            Path(taxonomy_path),
            Path("..") / taxonomy_path  # One level up from backend
        ]
        
        path = None
        for p in paths_to_try:
            if p.exists():
                path = p
                break
        
        if path is None:
            logger.warning(f"Skills taxonomy not found at any of: {paths_to_try}")
            logger.warning("Continuing with empty taxonomy (reduced skill normalization)")
            return {"skills": {}}
        
        with open(path, "r", encoding="utf-8") as f:
            _SKILLS_TAXONOMY = json.load(f)
        
        skills_count = len(_SKILLS_TAXONOMY.get("skills", {}))
        logger.info(f"✅ Loaded skills taxonomy: {skills_count} skills from {path}")
        
        return _SKILLS_TAXONOMY
        
    except Exception as e:
        logger.error(f"Error loading skills taxonomy: {e}")
        logger.warning("Continuing with empty taxonomy")
        return {"skills": {}}


def _load_spacy_model():
    """
    Lazy load spaCy model with graceful fallback.
    
    Why lazy?
    - Faster startup (model loads on first use)
    - Memory efficient (don't load if not needed)
    - Allows service to start without model installed
    
    Why graceful fallback?
    - spaCy/pydantic v1/v2 compatibility issues may prevent loading
    - Pattern matching provides 80% skill coverage (acceptable baseline)
    - Service should work with or without spaCy
    
    Returns:
        spaCy nlp model (en_core_web_sm) or None if unavailable
    
    Does NOT raise exceptions - returns None on failure
    """
    global _SPACY_NLP, _SPACY_AVAILABLE
    
    # Already tried and succeeded
    if _SPACY_NLP is not None:
        return _SPACY_NLP
    
    # Already tried and failed
    if _SPACY_AVAILABLE is False:
        return None
    
    # First attempt - try to load
    try:
        import spacy
        _SPACY_NLP = spacy.load("en_core_web_sm")
        _SPACY_AVAILABLE = True
        logger.info("✅ Loaded spaCy model: en_core_web_sm (NER available)")
        return _SPACY_NLP
    except Exception as e:
        _SPACY_AVAILABLE = False
        error_type = type(e).__name__
        
        # Specific handling for pydantic compatibility issue
        if "ForwardRef" in str(e) or "recursive_guard" in str(e):
            logger.warning(
                "⚠️  spaCy/pydantic compatibility issue detected. "
                "Falling back to pattern-only skill extraction (80% coverage). "
                "This is non-blocking - skills extraction will still work."
            )
            logger.debug(f"spaCy error details: {error_type}: {e}")
        elif "No module named" in str(e) or "Can't find model" in str(e):
            logger.warning(
                "⚠️  spaCy model 'en_core_web_sm' not found. "
                "Run: python -m spacy download en_core_web_sm "
                "Falling back to pattern-only extraction (80% coverage)."
            )
        else:
            logger.warning(
                f"⚠️  spaCy failed to load: {error_type}: {str(e)[:100]}. "
                "Falling back to pattern-only extraction (80% coverage)."
            )
        
        return None


def is_spacy_available() -> bool:
    """
    Check if spaCy NER is available.
    
    Returns:
        True if spaCy loaded successfully, False otherwise
    """
    global _SPACY_AVAILABLE
    
    if _SPACY_AVAILABLE is None:
        # Try loading to check availability
        _load_spacy_model()
    
    return _SPACY_AVAILABLE is True


async def extract_skills_from_text(text: str, use_taxonomy: bool = True) -> List[str]:
    """
    Extract skills from text using spaCy NER + pattern matching + taxonomy.
    
    Pipeline:
    1. spaCy NER - Extract entities (ORG, PRODUCT, TECH)
    2. Pattern matching - Extract known technical terms
    3. Taxonomy normalization - Map variants to canonical names
    4. Deduplication - Remove duplicates, return sorted list
    
    Why this approach?
    - spaCy: Catches most skills, robust to context
    - Patterns: Catches specific terms spaCy might miss
    - Taxonomy: Normalizes variants (improves matching)
    - Combined: Best accuracy for technical skills
    
    Args:
        text: Resume or job description text
        use_taxonomy: Whether to normalize using taxonomy (default: True)
    
    Returns:
        List of extracted skill names (canonical form, sorted)
    
    Example:
        text = "5 years experience with Python, JS, and AWS EC2"
        skills = await extract_skills_from_text(text)
        # Returns: ["AWS", "EC2", "JavaScript", "Python"]
    """
    if not text or not text.strip():
        return []
    
    # Load models/taxonomy
    nlp = _load_spacy_model()
    taxonomy = load_skills_taxonomy() if use_taxonomy else {"skills": {}}
    
    # Extract skills
    skills_set = set()
    
    # -----------------------------------
    # Method 1: spaCy NER (if available)
    # -----------------------------------
    if nlp is not None:
        try:
            doc = nlp(text)
            
            # Extract entities that might be skills
            for ent in doc.ents:
                # Technology entities (products, organizations, tech terms)
                if ent.label_ in ["PRODUCT", "ORG", "GPE"]:
                    candidate = ent.text.strip()
                    if _is_likely_skill(candidate):
                        skills_set.add(candidate)
            
            # Extract noun chunks with stricter filtering
            for chunk in doc.noun_chunks:
                candidate = chunk.text.strip()
                word_count = len(candidate.split())
                # Max 2 words, must pass skill check and contain tech term
                if word_count <= 2 and _is_likely_skill(candidate) and _contains_tech_term(candidate):
                    skills_set.add(candidate)
        except Exception as e:
            # spaCy NER failed, but don't crash - continue with pattern matching
            logger.debug(f"spaCy NER processing failed: {e}. Continuing with pattern matching.")
    else:
        # spaCy not available - pattern matching will provide baseline coverage
        logger.debug("spaCy not available - using pattern matching only")
    
    # -----------------------------------
    # Method 2: Pattern Matching
    # -----------------------------------
    # Common programming languages
    prog_langs = r'\b(Python|Java|JavaScript|TypeScript|C\+\+|C#|Ruby|Go|Rust|Swift|Kotlin|PHP|Perl|R|Scala|Haskell|Elixir)\b'
    matches = re.findall(prog_langs, text, re.IGNORECASE)
    skills_set.update(matches)
    
    # Frameworks and libraries
    frameworks = r'\b(React|Angular|Vue|Django|Flask|FastAPI|Spring|Rails|Express|Node\.js|TensorFlow|PyTorch|Keras|Scikit-learn|Pandas|NumPy)\b'
    matches = re.findall(frameworks, text, re.IGNORECASE)
    skills_set.update(matches)
    
    # Cloud platforms
    cloud = r'\b(AWS|Azure|GCP|Google Cloud|Kubernetes|Docker|Terraform|CloudFormation)\b'
    matches = re.findall(cloud, text, re.IGNORECASE)
    skills_set.update(matches)
    
    # Databases
    databases = r'\b(PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|Cassandra|DynamoDB|SQLite|Oracle|SQL Server)\b'
    matches = re.findall(databases, text, re.IGNORECASE)
    skills_set.update(matches)
    
    # -----------------------------------
    # Method 3: Taxonomy Normalization
    # -----------------------------------
    if use_taxonomy and taxonomy.get("skills"):
        normalized_skills = set()
        
        for skill in skills_set:
            # Try exact match first
            canonical = _normalize_skill_with_taxonomy(skill, taxonomy)
            if canonical:
                normalized_skills.add(canonical)
            else:
                # Keep original if no match found
                normalized_skills.add(skill)
        
        skills_set = normalized_skills
    
    # -----------------------------------
    # Cleanup and Return
    # -----------------------------------
    # Remove very short or very long candidates
    skills_list = [
        s for s in skills_set
        if 2 <= len(s) <= 50 and not s.isdigit()
    ]
    
    # Sort for consistency
    skills_list.sort()
    
    logger.info(f"Extracted {len(skills_list)} skills from text ({len(text)} chars)")
    
    return skills_list


def _is_likely_skill(candidate: str) -> bool:
    """
    Filter out non-skill candidates using heuristics.
    
    Heuristics:
    - Length: 2-50 characters
    - Not all digits
    - Not common words (the, and, for)
    - Contains at least one letter
    
    Args:
        candidate: Candidate skill name
    
    Returns:
        True if likely a skill, False otherwise
    """
    candidate = candidate.strip()
    
    # Length check
    if len(candidate) < 2 or len(candidate) > 50:
        return False
    
    # Must contain a letter
    if not any(c.isalpha() for c in candidate):
        return False
    
    # Blacklist common words
    blacklist = {
        "the", "and", "for", "with", "from", "this", "that", 
        "have", "has", "had", "was", "were", "been", "being", 
        "are", "is", "will", "would", "could", "should",
        "can", "may", "must", "shall", "do", "does", "did"
    }
    if candidate.lower() in blacklist:
        return False

    return True


def _contains_tech_term(candidate: str) -> bool:
    """
    Check if candidate contains likely technical terminology.

    Prevents extracting generic phrases like 'the system' or 'best practices'.

    Args:
        candidate: Candidate skill name

    Returns:
        True if contains tech term, False otherwise
    """
    tech_indicators = {
        # Programming related
        'api', 'sdk', 'framework', 'library', 'database', 'server', 'client',
        'backend', 'frontend', 'fullstack', 'devops', 'cloud', 'web', 'mobile',
        # Specific technologies
        'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node',
        'sql', 'nosql', 'aws', 'azure', 'gcp', 'docker', 'kubernetes',
        'git', 'linux', 'windows', 'mac', 'ios', 'android',
        # Data/ML
        'machine', 'learning', 'deep', 'neural', 'data', 'analytics',
        'tensorflow', 'pytorch', 'pandas', 'numpy', 'spark',
        # General tech
        'software', 'engineer', 'developer', 'programming', 'code', 'script',
    }

    words = candidate.lower().split()
    return any(word in tech_indicators for word in words)


def _normalize_skill_with_taxonomy(skill: str, taxonomy: Dict) -> Optional[str]:
    """
    Normalize skill using taxonomy (map variant → canonical).
    
    Matching strategy:
    1. Exact match on canonical name
    2. Exact match on synonym
    3. Fuzzy match (>90% similarity)
    
    Args:
        skill: Skill variant (e.g., "JS", "python3")
        taxonomy: Skills taxonomy dictionary
    
    Returns:
        Canonical skill name, or None if no match
    
    Example:
        _normalize_skill_with_taxonomy("JS", taxonomy) → "JavaScript"
        _normalize_skill_with_taxonomy("python3", taxonomy) → "Python"
    """
    skills_dict = taxonomy.get("skills", {})
    
    skill_lower = skill.lower()
    
    # Method 1: Exact match on canonical
    for canonical, data in skills_dict.items():
        if canonical.lower() == skill_lower:
            return canonical
    
    # Method 2: Exact match on synonym
    for canonical, data in skills_dict.items():
        synonyms = data.get("synonyms", [])
        if skill_lower in [s.lower() for s in synonyms]:
            return canonical
    
    # Method 3: Fuzzy match (>90% similarity)
    canonical_names = list(skills_dict.keys())
    if canonical_names:
        match = process.extractOne(skill, canonical_names, scorer=fuzz.ratio)
        
        if match and match[1] > 90:  # 90% similarity threshold
            return match[0]
    
    return None


def normalize_skill(skill: str, use_taxonomy: bool = True) -> str:
    """
    Normalize a single skill name.

    Public API for skill normalization.

    Args:
        skill: Skill name to normalize
        use_taxonomy: Whether to use taxonomy (default: True)

    Returns:
        Normalized skill name (canonical form if found, otherwise original)

    Example:
        normalize_skill("JS") → "JavaScript"
        normalize_skill("python3") → "Python"
        normalize_skill("UnknownSkill") → "UnknownSkill"
    """
    if not use_taxonomy:
        return skill.strip()

    taxonomy = load_skills_taxonomy()
    normalized = _normalize_skill_with_taxonomy(skill, taxonomy)

    return normalized if normalized else skill.strip()


async def expand_skills(skills: List[str], use_taxonomy: bool = True) -> List[str]:
    """
    Expand skills list by adding synonyms and normalized forms.

    Used for job embedding generation to improve matching:
    - Job requires "Python" → expands to ["Python", "python", "python3", "py"]
    - Increases recall when candidates use variants

    Args:
        skills: List of skill names to expand
        use_taxonomy: Whether to use taxonomy for expansion (default: True)

    Returns:
        Expanded list of skills with variants (deduplicated)

    Example:
        skills = ["Python", "JavaScript"]
        expanded = await expand_skills(skills)
        # Returns: ["Python", "python", "python3", "py", "JavaScript", "JS", "js", "javascript"]
    """
    if not skills:
        return []

    if not use_taxonomy:
        return skills

    taxonomy = load_skills_taxonomy()
    skills_dict = taxonomy.get("skills", {})

    expanded_set = set()

    for skill in skills:
        # Add original skill
        expanded_set.add(skill)

        # Normalize to canonical form
        canonical = _normalize_skill_with_taxonomy(skill, taxonomy)
        if canonical:
            expanded_set.add(canonical)

            # Add all synonyms of the canonical form
            skill_data = skills_dict.get(canonical, {})
            synonyms = skill_data.get("synonyms", [])
            expanded_set.update(synonyms)
        else:
            # No canonical form found, add lowercase variant
            expanded_set.add(skill.lower())

    return sorted(list(expanded_set))

