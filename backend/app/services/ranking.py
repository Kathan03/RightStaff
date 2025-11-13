# backend/app/services/ranking.py
"""
Main ranking service that orchestrates the complete pipeline.
Combines SQL gating, dense retrieval, structured scoring, and explanations.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import hashlib
import logging

from app.services.sql_filter import apply_combined_sql_gates
from app.services.retrieval import dense_retriever
from app.services.scoring import structured_scorer
from app.services.explanation import explanation_generator
from app.services.redis_client import redis_client
from app.utils.logging import logger
from app.database import AsyncSessionLocal
from app.models.candidate import Job, Candidate, CandidateContact, CandidateSkill, Skill
from sqlalchemy import select
from sqlalchemy.orm import selectinload


@dataclass
class RankedCandidate:
    """Final ranked candidate with all scores and explanations."""
    candidate_id: str
    final_score: float
    band: str  # 'high', 'medium', 'low'
    confidence: float
    summary: str
    reasons: List[str]
    evidence_snippets: List[Dict]
    score_breakdown: Dict


class RankingService:
    """
    Orchestrates the complete ranking pipeline.

    Pipeline from PRD:
    1. SQL gating (hard filters)
    2. Dense retrieval (semantic search)
    3. Structured scoring (objective metrics)
    4. Score blending (weighted combination)
    5. Banding (confidence levels)
    6. Explanation generation
    """

    # Final score weights from PRD
    WEIGHTS = {
        'dense': 0.40,
        'structured': 0.35,
        'pairwise': 0.00,  # Day 10 - cross-encoder
        'completeness': 0.25
    }

    def __init__(self):
        self.cache_ttl = 300  # 5 minute cache

    async def rank_candidates(
        self,
        job_id: str,
        filters: Optional[Dict] = None,
        use_cache: bool = True
    ) -> List[RankedCandidate]:
        """
        Main ranking entry point.

        Args:
            job_id: Job to rank for
            filters: Additional filters (city, salary, etc.)
            use_cache: Whether to use cached results

        Returns:
            List of ranked candidates with explanations
        """
        # Generate cache key
        cache_key = self._generate_cache_key(job_id, filters)

        # Check cache
        if use_cache:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info(f"✅ Using cached ranking for job {job_id}")
                return self._deserialize_ranking(json.loads(cached))

        logger.info(f"🎯 Starting ranking pipeline for job {job_id}")

        # Step 1: Get job data
        job_data = await self._fetch_job_data(job_id)

        # Step 2: SQL gating
        eligible_candidate_ids = await apply_combined_sql_gates(
            must_have_skills=job_data.get('must_have_skills_json', []),
            min_years_experience=job_data.get('min_years_experience'),
            max_years_experience=job_data.get('max_years_experience'),
            preferred_location=job_data.get('location')
        )
        logger.info(f"📊 {len(eligible_candidate_ids)} candidates passed SQL gates")

        if not eligible_candidate_ids:
            return []

        # Step 2b: Fetch full candidate data
        eligible_candidates = await self._fetch_candidates_data(list(eligible_candidate_ids))

        # Step 3: Dense retrieval
        retrieval_results = await dense_retriever.retrieve_candidates(
            job_data,
            [c['id'] for c in eligible_candidates],
            top_k=100
        )

        # Step 4: Structured scoring
        structured_scores = {}
        for candidate in eligible_candidates:
            score = await structured_scorer.calculate_score(candidate, job_data)
            structured_scores[candidate['id']] = score

        # Step 5: Calculate completeness scores
        completeness_scores = self._calculate_completeness_scores(eligible_candidates)

        # Step 6: Blend scores
        blended_results = self._blend_scores(
            retrieval_results,
            structured_scores,
            completeness_scores
        )

        # Step 7: Band candidates
        banded_results = self._band_candidates(blended_results)

        # Step 8: Generate explanations
        final_results = []
        for result in banded_results[:50]:  # Top 50 only
            explanation = await explanation_generator.generate(
                result,
                job_data,
                retrieval_results,
                structured_scores
            )

            final_results.append(RankedCandidate(
                candidate_id=result['candidate_id'],
                final_score=result['final_score'],
                band=result['band'],
                confidence=result['confidence'],
                summary=explanation['summary'],
                reasons=explanation['reasons'],
                evidence_snippets=explanation['evidence'],
                score_breakdown=result['scores']
            ))

        # Cache results
        if use_cache:
            cache_value = json.dumps(self._serialize_ranking(final_results))
            await redis_client.set(cache_key, cache_value, ex=self.cache_ttl)

        logger.info(f"✅ Ranking complete: {len(final_results)} candidates")
        return final_results

    def _blend_scores(
        self,
        retrieval_results,
        structured_scores,
        completeness_scores
    ) -> List[Dict]:
        """
        Blend all scoring components.

        Formula from PRD:
        final = 0.40 * dense + 0.35 * structured + 0.25 * completeness

        IMPORTANT: Iterate over ALL candidates from structured_scores, not just
        those in retrieval_results. This ensures ranking works even when Qdrant
        is empty or missing vectors.
        """
        blended = []

        # Build lookup dict for dense scores
        dense_scores_map = {}
        for retrieval in retrieval_results:
            dense_scores_map[retrieval.candidate_id] = retrieval.combined_score

        # Iterate over ALL candidates who passed SQL gating
        for candidate_id, structured in structured_scores.items():
            # Get all score components (use 0 if missing)
            dense_score = dense_scores_map.get(candidate_id, 0.0)
            structured_score = structured.combined_score if structured else 0.0
            completeness_score = completeness_scores.get(candidate_id, 0.5)

            # Weighted combination
            final_score = (
                self.WEIGHTS['dense'] * dense_score +
                self.WEIGHTS['structured'] * structured_score +
                self.WEIGHTS['completeness'] * completeness_score
            )

            blended.append({
                'candidate_id': candidate_id,
                'final_score': final_score,
                'scores': {
                    'dense': dense_score,
                    'structured': structured_score,
                    'completeness': completeness_score
                }
            })

        # Sort by final score
        blended.sort(key=lambda x: x['final_score'], reverse=True)
        return blended

    def _band_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """
        Band candidates into confidence levels.

        From PRD:
        - High: top 20% (confidence > 0.8)
        - Medium: 20-60% (confidence 0.5-0.8)
        - Low: bottom 40% (confidence < 0.5)
        """
        if not candidates:
            return []

        # Calculate percentiles
        scores = [c['final_score'] for c in candidates]
        p80 = sorted(scores)[int(len(scores) * 0.8)] if len(scores) > 4 else scores[0]
        p40 = sorted(scores)[int(len(scores) * 0.4)] if len(scores) > 2 else scores[-1]

        for candidate in candidates:
            score = candidate['final_score']

            if score >= p80:
                candidate['band'] = 'high'
                candidate['confidence'] = min(1.0, 0.8 + (score - p80) * 0.2)
            elif score >= p40:
                candidate['band'] = 'medium'
                candidate['confidence'] = 0.5 + (score - p40) * 0.3
            else:
                candidate['band'] = 'low'
                candidate['confidence'] = score * 0.5

        return candidates

    def _calculate_completeness_scores(
        self,
        candidates: List[Dict]
    ) -> Dict[str, float]:
        """
        Calculate profile completeness for each candidate.

        Weights:
        - Resume: 25%
        - Skills: 20%
        - Experience: 20%
        - Contact: 15%
        - Summary: 20%
        """
        scores = {}

        for candidate in candidates:
            score = 0.0

            # Check each component
            if candidate.get('resume_url'):
                score += 0.25
            if candidate.get('skills') and len(candidate['skills']) > 3:
                score += 0.20
            if candidate.get('years_experience'):
                score += 0.20
            if candidate.get('email') and candidate.get('phone'):
                score += 0.15
            if candidate.get('professional_summary'):
                score += 0.20

            scores[candidate['id']] = score

        return scores

    def _generate_cache_key(self, job_id: str, filters: Optional[Dict]) -> str:
        """Generate deterministic cache key."""
        content = f"{job_id}:{json.dumps(filters or {}, sort_keys=True)}"
        return f"ranking:{hashlib.md5(content.encode()).hexdigest()}"

    async def _fetch_job_data(self, job_id: str) -> Dict:
        """Fetch job data from database."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Job).where(Job.id == job_id)
            )
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found")

            return {
                'id': str(job.id),
                'title': job.title,
                'description': job.description,
                'department': job.department,
                'location': job.location,
                'must_have_skills_json': job.must_have_skills_json or [],
                'required_skills_json': job.required_skills_json or [],
                'min_years_experience': float(job.min_years_experience or 0),
                'max_years_experience': float(job.max_years_experience or 100),
                'work_arrangement': job.work_arrangement
            }

    async def _fetch_candidates_data(self, candidate_ids: List[str]) -> List[Dict]:
        """Fetch full candidate data from database."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Candidate)
                .options(
                    selectinload(Candidate.contact),
                    selectinload(Candidate.skills)
                )
                .where(Candidate.id.in_(candidate_ids))
            )
            candidates = result.scalars().all()

            # Convert to dicts
            candidate_dicts = []
            for candidate in candidates:
                # Get skills
                skills_result = await db.execute(
                    select(Skill.name)
                    .join(CandidateSkill)
                    .where(CandidateSkill.candidate_id == candidate.id)
                )
                skills = [row[0] for row in skills_result.all()]

                candidate_dicts.append({
                    'id': str(candidate.id),
                    'full_name': candidate.full_name,
                    'years_experience': float(candidate.years_experience or 0),
                    'professional_summary': candidate.professional_summary,
                    'skills': skills,
                    'email': candidate.contact.email if candidate.contact else None,
                    'phone': candidate.contact.phone if candidate.contact else None,
                    'city': candidate.contact.city if candidate.contact else None,
                    'open_to_remote': False,  # TODO: Add this field to schema
                    'updated_at': candidate.updated_at,
                    'resume_url': None,  # TODO: Get from resumes relationship
                    'matched_skills': skills  # For explanation
                })

            return candidate_dicts

    def _serialize_ranking(self, results: List[RankedCandidate]) -> List[Dict]:
        """Convert RankedCandidate objects to JSON-serializable dicts."""
        return [
            {
                'candidate_id': r.candidate_id,
                'final_score': r.final_score,
                'band': r.band,
                'confidence': r.confidence,
                'summary': r.summary,
                'reasons': r.reasons,
                'evidence_snippets': r.evidence_snippets,
                'score_breakdown': r.score_breakdown
            }
            for r in results
        ]

    def _deserialize_ranking(self, data: List[Dict]) -> List[RankedCandidate]:
        """Convert JSON dicts back to RankedCandidate objects."""
        return [
            RankedCandidate(**item)
            for item in data
        ]

# Singleton instance
ranking_service = RankingService()
