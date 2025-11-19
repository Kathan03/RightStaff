# backend/app/services/retrieval.py
"""
Dense retrieval service for semantic candidate search.
Performs vector similarity search in Qdrant with proper scoring.
"""

from typing import List, Dict, Optional, Tuple
import logging
from dataclasses import dataclass
import numpy as np

from app.services.vector_store import vector_store
from app.services.job_embeddings import job_embedding_service
from app.utils.logging import logger


@dataclass
class DenseRetrievalResult:
    """Result from dense retrieval with evidence."""
    candidate_id: str
    profile_score: float
    skills_score: float
    chunk_score: float
    combined_score: float
    evidence_chunks: List[Dict]  # Top matching chunks with text


class DenseRetriever:
    """
    Performs semantic search for candidates using vector similarity.

    Architecture per PRD:
    1. Query with job embeddings
    2. Search candidate vectors (profile, skills, chunks)
    3. Combine scores with weights
    4. Return top-k with evidence
    """

    # Weights from PRD (page 8)
    WEIGHTS = {
        'profile': 0.5,
        'skills': 0.3,
        'chunks': 0.2
    }

    async def retrieve_candidates(
        self,
        job_data: Dict,
        candidate_ids: List[str],
        top_k: int = 100
    ) -> List[DenseRetrievalResult]:
        """
        Retrieve semantically similar candidates for a job.

        Args:
            job_data: Job with embeddings
            candidate_ids: Pre-filtered candidates from SQL gate
            top_k: Number of candidates to return

        Returns:
            List of candidates with similarity scores and evidence

        Why pre-filter with SQL?
        - Reduces vector search space (performance)
        - Applies hard constraints (location, salary, visa)
        - Vector search only ranks eligible candidates
        """
        if not candidate_ids:
            return []

        logger.info(f"🔍 Dense retrieval for {len(candidate_ids)} candidates")

        # ════════════════════════════════════════════════════════
        # CRITICAL CHANGE: Fetch pre-computed job embeddings
        # (Don't generate them on-the-fly!)
        # ════════════════════════════════════════════════════════
        job_id = job_data["id"]

        # STEP 1: Check Redis cache
        from app.services.redis_client import redis_client
        import json

        cached = await redis_client.get(f"job_embeddings:{job_id}")

        if cached:
            embeddings = json.loads(cached)
            profile_emb = embeddings["profile_vector"]
            skills_emb = embeddings["skills_vector"]
            logger.info(f"✅ Using cached job embeddings for {job_id}")

        else:
            # STEP 2: Fetch from Qdrant jobs_v1 collection
            logger.info(f"🔍 Fetching job embeddings from Qdrant for {job_id}")

            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue

                results = vector_store.client.scroll(
                    collection_name="jobs_v1",
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="job_id",
                                match=MatchValue(value=str(job_id))
                            )
                        ]
                    ),
                    limit=10,
                    with_vectors=True  # CRITICAL: Must fetch vectors!
                )

                # Extract vectors from points
                profile_emb = None
                skills_emb = None

                for point in results[0]:
                    if point.payload["type"] == "profile":
                        profile_emb = point.vector
                    elif point.payload["type"] == "skills":
                        skills_emb = point.vector

                # STEP 3: Validate embeddings found
                if not profile_emb or not skills_emb:
                    raise ValueError(
                        f"Job embeddings not found for {job_id}. "
                        f"Run job ingestion webhook first: POST /api/v1/webhooks/job-ingestion"
                    )

                # STEP 4: Cache for future requests
                await redis_client.set(
                    f"job_embeddings:{job_id}",
                    json.dumps({
                        "profile_vector": profile_emb,
                        "skills_vector": skills_emb
                    }),
                    ex=3600  # 1 hour TTL
                )

                logger.info(f"✅ Fetched job embeddings from Qdrant for {job_id}")

            except Exception as e:
                logger.warning(f"⚠️  Job embeddings not found for {job_id}: {e}")
                logger.warning(f"⚠️  Falling back to generating embeddings on-the-fly")

                # FALLBACK: Generate embeddings on-the-fly
                from app.services.job_embeddings import generate_job_embeddings

                try:
                    embeddings = await generate_job_embeddings(
                        job_id=str(job_id),
                        title=job_data.get("title", ""),
                        description=job_data.get("description", ""),
                        required_skills=job_data.get("required_skills_json", [])
                    )

                    profile_emb = embeddings["profile_vector"]
                    skills_emb = embeddings["skills_vector"]

                    # Cache for future requests
                    await redis_client.set(
                        f"job_embeddings:{job_id}",
                        json.dumps({
                            "profile_vector": profile_emb,
                            "skills_vector": skills_emb
                        }),
                        ex=3600
                    )

                    logger.info(f"✅ Generated job embeddings on-the-fly for {job_id}")

                except Exception as gen_error:
                    logger.error(f"❌ Failed to generate embeddings on-the-fly: {gen_error}")
                    raise ValueError(
                        f"Job embeddings not available and could not be generated for {job_id}"
                    )

        # Search each vector type
        profile_results = await self._search_profiles(profile_emb, candidate_ids, top_k)
        skills_results = await self._search_skills(skills_emb, candidate_ids, top_k)
        chunk_results = await self._search_chunks(profile_emb, candidate_ids, top_k)
        print(f"Chunk results: {chunk_results}")
        print(f"Profile results: {profile_results}")    
        print(f"Skills results: {skills_results}")
        # Combine and rank
        combined_results = self._combine_scores(
            profile_results,
            skills_results,
            chunk_results
        )
        print(f"Combined results: {combined_results}")

        # Sort by combined score
        combined_results.sort(key=lambda x: x.combined_score, reverse=True)

        return combined_results[:top_k]

    async def _search_profiles(
        self,
        job_embedding: List[float],
        candidate_ids: List[str],
        limit: int
    ) -> Dict[str, float]:
        """Search candidate profile vectors."""
        try:
            results = vector_store.search(
                query_vector=job_embedding,
                filter_dict={
                    "must": [
                        {"key": "kind", "match": {"value": "profile"}},
                        {"key": "candidate_id", "match": {"any": candidate_ids}}
                    ]
                },
                top_k=limit
            )

            # Map candidate_id -> score
            scores = {}
            for point in results:
                candidate_id = point.payload.get('candidate_id')
                if candidate_id:
                    scores[candidate_id] = point.score

            return scores

        except Exception as e:
            logger.warning(f"Profile search failed: {e}. Returning empty results.")
            return {}

    async def _search_skills(
        self,
        job_embedding: List[float],
        candidate_ids: List[str],
        limit: int
    ) -> Dict[str, float]:
        """Search candidate skills vectors."""
        try:
            results = vector_store.search(
                query_vector=job_embedding,
                filter_dict={
                    "must": [
                        {"key": "kind", "match": {"value": "skills"}},
                        {"key": "candidate_id", "match": {"any": candidate_ids}}
                    ]
                },
                top_k=limit
            )

            scores = {}
            for point in results:
                candidate_id = point.payload.get('candidate_id')
                if candidate_id:
                    scores[candidate_id] = point.score

            return scores

        except Exception as e:
            logger.warning(f"Skills search failed: {e}. Returning empty results.")
            return {}

    async def _search_chunks(
        self,
        job_embedding: List[float],
        candidate_ids: List[str],
        limit: int
    ) -> Dict[str, Tuple[float, List[Dict]]]:
        """
        Search candidate chunk vectors and return evidence.

        Why chunks matter:
        - Provide evidence for explanations
        - Capture specific experiences/projects
        - Enable citation in explanations
        """
        try:
            results = vector_store.search(
                query_vector=job_embedding,
                filter_dict={
                    "must": [
                        {"key": "kind", "match": {"value": "chunk"}},
                        {"key": "candidate_id", "match": {"any": candidate_ids}}
                    ]
                },
                top_k=limit * 3,  # Get more chunks for evidence
                with_payload=True
            )

            # Group by candidate and keep top chunks
            candidate_chunks = {}
            for point in results:
                candidate_id = point.payload.get('candidate_id')
                if not candidate_id:
                    continue

                if candidate_id not in candidate_chunks:
                    candidate_chunks[candidate_id] = []

                candidate_chunks[candidate_id].append({
                    'score': point.score,
                    'text': point.payload.get('chunk_text', ''),
                    'chunk_index': point.payload.get('chunk_index', 0),
                    'skills_detected': point.payload.get('skills_detected', [])
                })

            # Keep top 2 chunks per candidate for evidence
            scores_and_evidence = {}
            for candidate_id, chunks in candidate_chunks.items():
                chunks.sort(key=lambda x: x['score'], reverse=True)
                top_chunks = chunks[:2]
                avg_score = float(np.mean([c['score'] for c in top_chunks]))
                scores_and_evidence[candidate_id] = (avg_score, top_chunks)

            return scores_and_evidence

        except Exception as e:
            logger.warning(f"Chunk search failed: {e}. Returning empty results.")
            return {}

    def _combine_scores(
        self,
        profile_scores: Dict[str, float],
        skills_scores: Dict[str, float],
        chunk_scores: Dict[str, Tuple[float, List[Dict]]]
    ) -> List[DenseRetrievalResult]:
        """
        Combine scores from different vector types.

        Formula from PRD (page 8):
        dense_score = 0.5 * profile + 0.3 * skills + 0.2 * chunks
        """
        all_candidate_ids = set()
        all_candidate_ids.update(profile_scores.keys())
        all_candidate_ids.update(skills_scores.keys())
        all_candidate_ids.update(chunk_scores.keys())

        results = []
        for candidate_id in all_candidate_ids:
            # Get individual scores (default to 0 if missing)
            profile_score = profile_scores.get(candidate_id, 0.0)
            skills_score = skills_scores.get(candidate_id, 0.0)
            chunk_data = chunk_scores.get(candidate_id, (0.0, []))
            chunk_score = chunk_data[0]
            evidence = chunk_data[1] if len(chunk_data) > 1 else []

            # Weighted combination
            combined = (
                self.WEIGHTS['profile'] * profile_score +
                self.WEIGHTS['skills'] * skills_score +
                self.WEIGHTS['chunks'] * chunk_score
            )

            results.append(DenseRetrievalResult(
                candidate_id=candidate_id,
                profile_score=profile_score,
                skills_score=skills_score,
                chunk_score=chunk_score,
                combined_score=combined,
                evidence_chunks=evidence
            ))

        return results

# Singleton instance
dense_retriever = DenseRetriever()
