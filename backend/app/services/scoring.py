# backend/app/services/scoring.py
"""
Structured scoring service for objective candidate metrics.
Calculates scores based on database fields (experience, skills, recency, etc.)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import math
import logging

from app.utils.logging import logger


@dataclass
class StructuredScore:
    """Structured scoring components."""
    nice_to_have_coverage: float  # 0-1
    experience_score: float        # 0-1
    recency_score: float          # 0-1
    domain_score: float           # 0-1
    location_score: float         # 0-1
    combined_score: float         # 0-1
    details: Dict                 # For explanations


class StructuredScorer:
    """
    Calculates objective scores from candidate data.

    Weights from PRD (page 8):
    - Nice-to-have coverage: 35%
    - Years experience: 20%
    - Recency: 15%
    - Domain match: 10%
    - Location: 20%
    """

    WEIGHTS = {
        'nice_to_have': 0.35,
        'experience': 0.20,
        'recency': 0.15,
        'domain': 0.10,
        'location': 0.20
    }

    async def calculate_score(
        self,
        candidate_data: Dict,
        job_data: Dict
    ) -> StructuredScore:
        """
        Calculate all structured scoring components.

        Why structured scoring?
        - Complements semantic similarity with objective facts
        - Ensures experienced candidates rank higher
        - Rewards fresh profiles and relevant domains
        """

        # Calculate individual components
        nice_to_have = self._score_nice_to_have_skills(candidate_data, job_data)
        experience = self._score_experience(candidate_data, job_data)
        recency = self._score_recency(candidate_data)
        domain = self._score_domain(candidate_data, job_data)
        location = self._score_location(candidate_data, job_data)

        # Weighted combination
        combined = (
            self.WEIGHTS['nice_to_have'] * nice_to_have +
            self.WEIGHTS['experience'] * experience +
            self.WEIGHTS['recency'] * recency +
            self.WEIGHTS['domain'] * domain +
            self.WEIGHTS['location'] * location
        )

        return StructuredScore(
            nice_to_have_coverage=nice_to_have,
            experience_score=experience,
            recency_score=recency,
            domain_score=domain,
            location_score=location,
            combined_score=combined,
            details={
                'skills_matched': candidate_data.get('matched_skills', []),
                'years_experience': candidate_data.get('years_experience', 0),
                'last_updated': candidate_data.get('updated_at'),
                'location': candidate_data.get('city'),
                'remote_eligible': candidate_data.get('open_to_remote', False)
            }
        )

    def _score_nice_to_have_skills(
        self,
        candidate_data: Dict,
        job_data: Dict
    ) -> float:
        """
        Score based on nice-to-have skills coverage.

        Formula: (matched_skills / total_nice_to_haves)
        """
        nice_to_haves = job_data.get('required_skills_json', []) or []
        if not nice_to_haves:
            return 1.0  # No requirements = perfect score

        candidate_skills = set(candidate_data.get('skills', []))
        matched = len(candidate_skills.intersection(nice_to_haves))

        return matched / len(nice_to_haves)

    def _score_experience(
        self,
        candidate_data: Dict,
        job_data: Dict
    ) -> float:
        """
        Score based on years of experience with diminishing returns.

        Formula from PRD: sqrt(years) / sqrt(10), capped at 1.0

        Why diminishing returns?
        - Difference between 1-3 years is huge
        - Difference between 10-12 years is minimal
        - Prevents over-indexing on tenure
        """
        years = candidate_data.get('years_experience', 0)
        if years is None:
            years = 0

        min_years = job_data.get('min_years_experience', 0)
        max_years = job_data.get('max_years_experience', 20)

        # Penalty if below minimum
        if years < min_years:
            return max(0, years / min_years * 0.5) if min_years > 0 else 0.5

        # Penalty if way over maximum (overqualified)
        if max_years and years > max_years * 1.5:
            return 0.7

        # Normal scoring with diminishing returns
        return min(1.0, math.sqrt(years) / math.sqrt(10))

    def _score_recency(self, candidate_data: Dict) -> float:
        """
        Score based on profile freshness.

        Formula: exp(-days_ago / 30)

        Why recency matters:
        - Fresh profiles = active job seekers
        - Stale profiles = may have found job
        - Exponential decay models engagement probability
        """
        updated_str = candidate_data.get('updated_at')
        if not updated_str:
            return 0.5  # Unknown = neutral score

        try:
            # Handle both datetime objects and ISO strings
            if isinstance(updated_str, datetime):
                updated = updated_str
            else:
                updated = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))

            days_ago = (datetime.utcnow().replace(tzinfo=updated.tzinfo) - updated).days

            # Exponential decay with 30-day half-life
            return math.exp(-days_ago / 30)
        except:
            return 0.5

    def _score_domain(self, candidate_data: Dict, job_data: Dict) -> float:
        """
        Score based on industry/domain match.

        Simple implementation - can be enhanced with:
        - Industry taxonomy
        - Previous company matching
        - Role progression analysis
        """
        # For MVP, check if department matches previous experience
        job_dept = (job_data.get('department') or '').lower()
        candidate_summary = (candidate_data.get('professional_summary') or '').lower()

        if not job_dept or not candidate_summary:
            return 0.5  # Neutral if no data

        # Simple keyword matching (enhance in production)
        domain_keywords = {
            'engineering': ['software', 'developer', 'programmer', 'engineer'],
            'sales': ['sales', 'account', 'business development', 'revenue'],
            'marketing': ['marketing', 'brand', 'campaign', 'growth'],
            'finance': ['finance', 'accounting', 'budget', 'financial'],
        }

        dept_keywords = domain_keywords.get(job_dept, [job_dept])
        matches = sum(1 for kw in dept_keywords if kw in candidate_summary)

        return min(1.0, matches / max(1, len(dept_keywords)))

    def _score_location(self, candidate_data: Dict, job_data: Dict) -> float:
        """
        Score based on location match or remote eligibility.

        Logic:
        - Same city = 1.0
        - Remote job + remote-open candidate = 1.0
        - Different city + not remote = 0.3
        """
        job_location = (job_data.get('location') or '').lower()
        job_remote = (job_data.get('work_arrangement') or '').lower() == 'remote'

        candidate_city = (candidate_data.get('city') or '').lower()
        candidate_remote = candidate_data.get('open_to_remote', False)

        # Perfect match scenarios
        if job_location == candidate_city:
            return 1.0
        if job_remote and candidate_remote:
            return 1.0

        # Partial match - candidate open to remote but job is hybrid
        if candidate_remote and 'hybrid' in (job_data.get('work_arrangement') or '').lower():
            return 0.7

        # Mismatch
        return 0.3

# Singleton instance
structured_scorer = StructuredScorer()
