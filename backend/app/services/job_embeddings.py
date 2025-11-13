# backend/app/services/job_embeddings.py
"""
Job embedding generation service.
Creates and manages embeddings for job descriptions and skills.
This is REQUIRED for semantic matching - candidates are matched against job vectors!
"""

import json
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import hashlib

from app.services.embeddings import embedding_service
from app.services.vector_store import vector_store
from app.services.ontology import expand_skills
from app.services.redis_client import redis_client
from app.utils.logging import logger


class JobEmbeddingService:
    """
    Generates and manages job embeddings for ranking.

    Why separate service?
    - Jobs change less frequently than candidates
    - Job embeddings are reused across many ranking requests
    - Can cache aggressively (TTL: 1 hour)
    """

    def __init__(self):
        self.cache_ttl = 3600  # 1 hour cache for job embeddings

    async def get_or_create_job_embeddings(
        self,
        job_data: Dict
    ) -> Tuple[List[float], List[float], str]:
        """
        Get cached or create new embeddings for a job.

        Args:
            job_data: Job dictionary with title, description, skills

        Returns:
            (profile_embedding, skills_embedding, job_hash)

        Why two embeddings?
        - Profile: Captures role, responsibilities, culture (weight: 0.5)
        - Skills: Captures technical requirements (weight: 0.3)
        - Allows weighted semantic search per PRD
        """
        # Generate deterministic hash of job content
        job_hash = self._generate_job_hash(job_data)
        cache_key = f"job_embeddings:{job_data['id']}:{job_hash}"

        # Check cache first
        cached = await redis_client.get(cache_key)
        if cached:
            logger.info(f"✅ Using cached job embeddings for {job_data['id']}")
            result = json.loads(cached)
            return result['profile'], result['skills'], job_hash

        logger.info(f"📊 Generating new job embeddings for {job_data['title']}")

        # Generate profile embedding (title + description)
        profile_text = f"{job_data['title']}\n{job_data.get('description', '')}"
        profile_embedding = await embedding_service.embed_text(profile_text)

        # Generate skills embedding (expanded skills list)
        skills_text = await self._prepare_skills_text(job_data)
        skills_embedding = await embedding_service.embed_text(skills_text)

        # Cache the embeddings
        cache_value = json.dumps({
            'profile': profile_embedding,
            'skills': skills_embedding,
            'generated_at': datetime.utcnow().isoformat()
        })
        await redis_client.set(cache_key, cache_value, ex=self.cache_ttl)

        # Also store in Qdrant for debugging/analysis
        await self._store_job_vectors(job_data, profile_embedding, skills_embedding)

        return profile_embedding, skills_embedding, job_hash

    async def _prepare_skills_text(self, job_data: Dict) -> str:
        """
        Prepare skills text with ontology expansion.

        Why expand?
        - Job says "Python" but candidate has "Python3"
        - Job says "ML" but candidate has "Machine Learning"
        - Ontology expansion bridges these gaps
        """
        must_haves = job_data.get('must_have_skills_json', []) or []
        nice_to_haves = job_data.get('required_skills_json', []) or []

        # Expand skills using ontology
        expanded_must = await expand_skills(must_haves)
        expanded_nice = await expand_skills(nice_to_haves)

        # Weight must-haves higher by repeating them
        skills_parts = (
            expanded_must * 3 +  # Must-haves appear 3x
            expanded_nice * 1     # Nice-to-haves appear 1x
        )

        return " ".join(skills_parts)

    def _generate_job_hash(self, job_data: Dict) -> str:
        """Generate deterministic hash of job content for cache invalidation."""
        content = f"{job_data.get('title', '')}"
        content += f"{job_data.get('description', '')}"
        content += f"{job_data.get('must_have_skills_json', [])}"
        content += f"{job_data.get('required_skills_json', [])}"
        return hashlib.md5(content.encode()).hexdigest()[:8]

    async def _store_job_vectors(
        self,
        job_data: Dict,
        profile_embedding: List[float],
        skills_embedding: List[float]
    ):
        """Store job vectors in Qdrant for analysis (optional but useful)."""
        try:
            points = [
                {
                    "id": f"job_{job_data['id']}_profile",
                    "vector": profile_embedding,
                    "payload": {
                        "kind": "job_profile",
                        "job_id": str(job_data['id']),
                        "title": job_data['title'],
                        "updated_at": datetime.utcnow().isoformat()
                    }
                },
                {
                    "id": f"job_{job_data['id']}_skills",
                    "vector": skills_embedding,
                    "payload": {
                        "kind": "job_skills",
                        "job_id": str(job_data['id']),
                        "skills": job_data.get('must_have_skills_json', []),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                }
            ]
            await vector_store.upsert_points(points)
        except Exception as e:
            # Non-critical - log but don't fail
            logger.warning(f"Failed to store job vectors: {e}")

# Singleton instance
job_embedding_service = JobEmbeddingService()
