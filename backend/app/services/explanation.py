# backend/app/services/explanation.py
"""
Generates human-readable explanations for ranking decisions.
Provides transparency and builds trust in AI recommendations.
"""

from typing import Dict, List
import logging

from app.utils.logging import logger


class ExplanationGenerator:
    """
    Generates explanations citing evidence from scoring components.

    Why explanations matter:
    - Build trust with staffing agents
    - Enable informed decisions
    - Meet compliance requirements
    - Debug ranking issues
    """

    async def generate(
        self,
        ranking_result: Dict,
        job_data: Dict,
        retrieval_results: List,
        structured_scores: Dict
    ) -> Dict:
        """
        Generate comprehensive explanation for a candidate's ranking.

        Returns:
            {
                'summary': One-line overview,
                'reasons': List of 3-5 bullet points,
                'evidence': List of evidence snippets with citations
            }
        """
        candidate_id = ranking_result['candidate_id']
        scores = ranking_result['scores']

        # Generate summary based on band and score
        summary = self._generate_summary(ranking_result, job_data)

        # Extract top reasons from score components
        reasons = self._extract_reasons(
            candidate_id,
            scores,
            structured_scores,
            job_data
        )

        # Format evidence chunks
        evidence = self._format_evidence(
            candidate_id,
            retrieval_results
        )

        return {
            'summary': summary,
            'reasons': reasons[:5],  # Max 5 reasons
            'evidence': evidence[:2]  # Max 2 evidence chunks
        }

    def _generate_summary(self, result: Dict, job_data: Dict) -> str:
        """Generate one-line summary based on ranking."""
        band = result['band']
        score = result['final_score']
        title = job_data['title']

        if band == 'high':
            return f"Excellent match for {title} with {score:.0%} compatibility"
        elif band == 'medium':
            return f"Good fit for {title} with {score:.0%} compatibility"
        else:
            return f"Potential candidate for {title} with {score:.0%} compatibility"

    def _extract_reasons(
        self,
        candidate_id: str,
        scores: Dict,
        structured_scores: Dict,
        job_data: Dict
    ) -> List[str]:
        """
        Extract top reasons from scoring components.

        Prioritize:
        1. Strong skill matches
        2. Relevant experience
        3. Location/remote match
        4. Recent activity
        5. Domain expertise
        """
        reasons = []

        # Get structured score details
        structured = structured_scores.get(candidate_id)
        if not structured:
            return ["Candidate matches job requirements"]

        details = structured.details

        # Skill match reason
        if structured.nice_to_have_coverage > 0.7:
            matched = details.get('skills_matched', [])
            if matched:
                skills_str = ', '.join(matched[:3])
                reasons.append(f"Strong skills match: {skills_str}")
        elif structured.nice_to_have_coverage > 0.4:
            reasons.append("Partial skills match with growth potential")

        # Experience reason
        years = details.get('years_experience', 0)
        min_years = job_data.get('min_years_experience', 0)
        if years >= min_years:
            reasons.append(f"{years} years of relevant experience")
        elif years > 0:
            reasons.append(f"{years} years experience (building towards {min_years}+ requirement)")

        # Location reason
        if structured.location_score >= 1.0:
            if details.get('remote_eligible'):
                reasons.append("Open to remote work")
            else:
                reasons.append(f"Located in {details.get('location', 'preferred location')}")

        # Recency reason
        if structured.recency_score > 0.8:
            reasons.append("Recently updated profile (active candidate)")

        # Semantic match reason
        if scores.get('dense', 0) > 0.7:
            reasons.append("Strong semantic match to job description")

        return reasons

    def _format_evidence(
        self,
        candidate_id: str,
        retrieval_results: List
    ) -> List[Dict]:
        """
        Format evidence chunks with proper citations.

        Returns chunks that support the ranking decision.
        """
        evidence = []

        # Find retrieval result for this candidate
        for result in retrieval_results:
            if result.candidate_id == candidate_id:
                for chunk in result.evidence_chunks:
                    evidence.append({
                        'text': chunk['text'][:200] + '...',  # Truncate
                        'skills_found': chunk.get('skills_detected', []),
                        'relevance_score': chunk['score'],
                        'location': f"Resume chunk {chunk.get('chunk_index', '?')}"
                    })
                break

        return evidence

# Singleton instance
explanation_generator = ExplanationGenerator()
