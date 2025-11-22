"""
Cross-encoder re-ranking service for pairwise candidate scoring.
Uses sentence-transformers cross-encoder for improved ranking accuracy.
"""

from sentence_transformers import CrossEncoder
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class RerankerService:
    """Cross-encoder for pairwise candidate re-ranking."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize cross-encoder model.

        Args:
            model_name: HuggingFace model ID (default: ms-marco-MiniLM-L-6-v2)
        """
        try:
            self.model = CrossEncoder(model_name)
            logger.info(f"✅ Cross-encoder loaded: {model_name}")
        except Exception as e:
            logger.error(f"❌ Failed to load cross-encoder model {model_name}: {e}")
            raise

    def rerank(
        self,
        job_description: str,
        candidates: List[Dict],
        top_k: int = 50
    ) -> List[Dict]:
        """
        Re-rank candidates using pairwise scoring.

        Args:
            job_description: Full job description text
            candidates: List of dicts with 'id' and 'professional_summary'
            top_k: Number of top candidates to return

        Returns:
            Sorted list of candidates with 'pairwise_score' added
        """
        if not candidates:
            return []

        if not job_description:
            logger.warning("⚠️ Empty job description provided for re-ranking")
            for candidate in candidates:
                candidate['pairwise_score'] = 0.0
            return candidates[:top_k]

        try:
            # Create (query, document) pairs
            pairs = [
                (job_description, c.get('professional_summary', ''))
                for c in candidates
            ]

            # Predict raw logits (can be negative)
            raw_scores = self.model.predict(pairs)

            # Linear normalization to [0, 1] range
            min_score = float(min(raw_scores))
            max_score = float(max(raw_scores))

            if max_score - min_score > 1e-6:
                # Min-max scaling to [0, 1]
                normalized_scores = [
                    (float(score) - min_score) / (max_score - min_score)
                    for score in raw_scores
                ]
            else:
                # All scores equal - assign neutral 0.5
                normalized_scores = [0.5] * len(raw_scores)

            # Add normalized scores to candidates
            for candidate, score in zip(candidates, normalized_scores):
                candidate['pairwise_score'] = score

            # Sort by score descending
            ranked = sorted(
                candidates,
                key=lambda x: x['pairwise_score'],
                reverse=True
            )

            logger.info(
                f"🔄 Re-ranked {len(candidates)} candidates "
                f"(raw range: {min_score:.2f} to {max_score:.2f}, normalized to [0, 1])"
            )
            return ranked[:top_k]

        except Exception as e:
            logger.error(f"❌ Re-ranking error: {e}")
            # Return candidates with neutral scores on error
            for candidate in candidates:
                candidate['pairwise_score'] = 0.5
            return candidates[:top_k]


# Singleton instance
_reranker_service = None


def get_reranker() -> RerankerService:
    """Get or create singleton reranker instance."""
    global _reranker_service
    if _reranker_service is None:
        try:
            _reranker_service = RerankerService()
        except Exception as e:
            logger.error(f"❌ Failed to initialize reranker service: {e}")
            raise
    return _reranker_service
