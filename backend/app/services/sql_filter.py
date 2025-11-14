# backend/app/services/sql_filter.py
"""
SQL-based candidate filtering (Phase 1 of ranking pipeline).

This service filters candidates using PostgreSQL BEFORE expensive vector search:
- Must-have skills filtering (ontology gate)
- Years of experience requirements
- Location preferences

Why SQL first?
- PostgreSQL indexes make filtering fast (< 10ms for 100K candidates)
- Reduces Qdrant search space (only search qualified candidates)
- Exact matching for structured requirements

Performance:
- Must-have skills: O(N) with index, < 50ms for 10K candidates
- Combined gates: < 100ms total
"""

from typing import List, Set, Optional
import logging
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from app.models.candidate import Candidate, CandidateSkill, Skill, CandidateContact
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

async def filter_candidates_by_must_have_skills(
    must_have_skills: List[str],
    db: Optional[AsyncSession] = None
) -> Set[str]:
    """
    Filter candidates who have ALL must-have skills (AND logic).
    
    This is the ONTOLOGY GATE - critical for ranking quality.
    
    SQL Query Strategy:
    - JOIN candidate_skill → skill tables
    - Filter where skill.name IN must_have_skills
    - GROUP BY candidate_id
    - HAVING COUNT(DISTINCT skill_id) = len(must_have_skills)
    
    Why GROUP BY + HAVING?
    - Ensures candidate has ALL skills (not just some)
    - Efficient with proper indexes
    - Single query (no N+1 problem)
    
    Args:
        must_have_skills: List of required skill names (e.g., ["Python", "AWS"])
        db: Optional database session (creates new if not provided)
    
    Returns:
        Set of candidate UUIDs (as strings) who pass the gate
    
    Example:
        skills = ["Python", "AWS"]
        qualified = await filter_candidates_by_must_have_skills(skills)
        # Returns: {"uuid-1", "uuid-2", ...}
    """
    if not must_have_skills:
        logger.info("No must-have skills specified - skipping skill gate")
        return set()
    
    close_db = False
    if db is None:
        db = AsyncSessionLocal()
        close_db = True
    
    try:
        logger.info(f"Applying must-have skills gate: {must_have_skills}")
        
        query = (
            select(CandidateSkill.candidate_id)
            .join(Skill, CandidateSkill.skill_id == Skill.id)
            .where(Skill.name.in_(must_have_skills))
            .group_by(CandidateSkill.candidate_id)
            .having(func.count(func.distinct(CandidateSkill.skill_id)) == len(must_have_skills))
        )
        
        result = await db.execute(query)
        candidate_ids = {str(row[0]) for row in result.all()}
        
        logger.info(f"✅ {len(candidate_ids)} candidates passed must-have skills gate")
        
        return candidate_ids
        
    finally:
        if close_db:
            await db.close()



async def filter_candidates_by_years_experience(
    min_years: Optional[float] = None,
    max_years: Optional[float] = None,
    db: Optional[AsyncSession] = None
) -> Set[str]:
    """
    Filter candidates by years of experience range.
    
    Args:
        min_years: Minimum years of experience (inclusive)
        max_years: Maximum years of experience (inclusive)
        db: Optional database session
    
    Returns:
        Set of candidate UUIDs who meet the criteria
    
    Example:
        # Find candidates with 3-7 years experience
        qualified = await filter_candidates_by_years_experience(min_years=3, max_years=7)
    """
    if min_years is None and max_years is None:
        logger.info("No years filter specified - skipping")
        return set()
    
    close_db = False
    if db is None:
        db = AsyncSessionLocal()
        close_db = True
    
    try:
        conditions = []
        
        # Convert input parameters to Decimal for database query
        # but ensure output is clean float/string
        if min_years is not None:
            conditions.append(Candidate.years_experience >= Decimal(str(min_years)))
        
        if max_years is not None:
            conditions.append(Candidate.years_experience <= Decimal(str(max_years)))
        
        query = select(Candidate.id).where(and_(*conditions))
        
        result = await db.execute(query)
        
        # Convert all results to strings immediately to avoid Decimal issues
        candidate_ids = {str(row[0]) for row in result.all()}
        
        logger.info(f"✅ {len(candidate_ids)} candidates passed years filter (min={min_years}, max={max_years})")
        
        return candidate_ids
        
    finally:
        if close_db:
            await db.close()


async def filter_candidates_by_location(
    preferred_location: Optional[str] = None,
    db: Optional[AsyncSession] = None
) -> Set[str]:
    """
    Filter candidates by location (city).
    
    Case-insensitive matching.
    
    Args:
        preferred_location: City name (e.g., "New York")
        db: Optional database session
    
    Returns:
        Set of candidate UUIDs in that location
    
    Example:
        qualified = await filter_candidates_by_location("San Francisco")
    """
    if not preferred_location:
        logger.info("No location filter specified - skipping")
        return set()
    
    close_db = False
    if db is None:
        db = AsyncSessionLocal()
        close_db = True
    
    try:
        query = (
            select(CandidateContact.candidate_id)
            .where(func.lower(CandidateContact.city) == preferred_location.lower())
        )
        
        result = await db.execute(query)
        candidate_ids = {str(row[0]) for row in result.all()}
        
        logger.info(f"✅ {len(candidate_ids)} candidates in location: {preferred_location}")
        
        return candidate_ids
        
    finally:
        if close_db:
            await db.close()



async def apply_combined_sql_gates(
    must_have_skills: Optional[List[str]] = None,
    min_years_experience: Optional[float] = None,
    max_years_experience: Optional[float] = None,
    preferred_location: Optional[str] = None,
    db: Optional[AsyncSession] = None
) -> Set[str]:
    """
    Apply multiple SQL gates and return intersection (AND logic).
    
    Combines: must-have skills, years of experience, location
    Returns only candidates who pass ALL gates.
    
    Why intersection?
    - All filters must pass (stricter matching)
    - Reduces false positives
    - Better candidate quality
    
    Args:
        must_have_skills: Required skills (e.g., ["Python", "AWS"])
        min_years_experience: Minimum years
        max_years_experience: Maximum years
        preferred_location: City name
        db: Optional database session
    
    Returns:
        Set of candidate UUIDs who pass ALL gates
    
    Example:
        qualified = await apply_combined_sql_gates(
            must_have_skills=["Python", "AWS"],
            min_years_experience=3.0,
            preferred_location="San Francisco"
        )
    """
    close_db = False
    if db is None:
        db = AsyncSessionLocal()
        close_db = True
    
    try:
        qualified_sets = []
        
        # Gate 1: Must-have skills
        if must_have_skills:
            skills_set = await filter_candidates_by_must_have_skills(must_have_skills, db)
            if skills_set:
                qualified_sets.append(skills_set)
            else:
                logger.warning("No candidates passed skills gate - returning empty set")
                return set()
        
        # Gate 2: Years of experience
        if min_years_experience is not None or max_years_experience is not None:
            years_set = await filter_candidates_by_years_experience(
                min_years_experience, max_years_experience, db
            )
            if years_set:
                qualified_sets.append(years_set)
            else:
                logger.warning("No candidates passed years filter - returning empty set")
                return set()
        
        # Gate 3: Location
        if preferred_location:
            location_set = await filter_candidates_by_location(preferred_location, db)
            if location_set:
                qualified_sets.append(location_set)
            else:
                logger.warning("No candidates in preferred location - returning empty set")
                return set()
        
        # Intersection (AND logic)
        if not qualified_sets:
            logger.warning("No SQL gates applied - returning empty set")
            return set()
        
        # Start with first set, then intersect with others
        qualified_candidates = qualified_sets[0]
        for candidate_set in qualified_sets[1:]:
            qualified_candidates &= candidate_set
        
        logger.info(
            f"✅✅✅ SQL Gating Complete: {len(qualified_candidates)} candidates qualified "
            f"(applied {len(qualified_sets)} gate(s))"
        )

        # qualified_candidates is already a set of UUID strings, no conversion needed
        return qualified_candidates

    finally:
        if close_db:
            await db.close()

