"""
Comprehensive tests for webhook handlers.

Tests cover:
1. Candidate-updated webhook validation and queuing
2. Job-ingestion webhook with skill expansion and embeddings
3. Error handling (404, 500)
4. Execution trace documentation

Execution Flow:
- POST /webhooks/candidate-updated
  Entry: app/api/webhooks.py:candidate_updated_webhook()
  Logic: Validates candidate exists in PostgreSQL
  Queue: Pushes job to Redis ingestion_queue
  Storage: app/services/redis_client.py:lpush()

- POST /webhooks/job-ingestion
  Entry: app/api/webhooks.py:job_ingestion_webhook()
  Logic: app/services/ontology.py:expand_skills(), normalize_skill()
  Embeddings: app/services/job_embeddings.py:generate_job_embeddings()
  Storage: app/services/vector_store.py:upsert_points() -> Qdrant jobs_v1
  Cache: app/services/redis_client.py:set() -> Redis
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4, UUID
from fastapi.testclient import TestClient


# ============================================================================
# Candidate Updated Webhook Tests
# ============================================================================

@pytest.mark.asyncio
class TestCandidateUpdatedWebhook:
    """Tests for POST /api/v1/webhooks/candidate-updated endpoint."""

    @pytest.fixture
    def valid_payload(self):
        """Valid webhook payload for testing."""
        return {
            "event_type": "resume_uploaded",
            "candidate_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "s3_resume_url": "resumes/test-candidate/resume.pdf",
            "profile_snapshot": {
                "name": "John Doe",
                "email": "john@example.com"
            }
        }

    async def test_webhook_queues_job_successfully(self, valid_payload):
        """
        Test successful webhook processing and job queuing.

        Execution Trace:
        1. webhooks.py:candidate_updated_webhook() - Entry point
        2. database.py:get_db() - Get database session
        3. PostgreSQL SELECT candidate WHERE id = ? - Validate candidate exists
        4. redis_client.py:lpush("ingestion_queue", job_data) - Queue job
        5. Return 202 Accepted
        """
        with patch('app.api.webhooks.get_db') as mock_get_db, \
             patch('app.api.webhooks.redis_client') as mock_redis:

            # Mock database session
            mock_db = AsyncMock()
            mock_candidate = MagicMock()
            mock_candidate.full_name = "John Doe"

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_candidate
            mock_db.execute.return_value = mock_result

            # Import and test
            from app.api.webhooks import candidate_updated_webhook, WebhookPayload

            payload = WebhookPayload(**valid_payload)

            # Call webhook
            response = await candidate_updated_webhook(payload, mock_db)

            # Verify job was queued
            mock_redis.lpush.assert_called_once()
            call_args = mock_redis.lpush.call_args
            assert call_args[0][0] == "ingestion_queue"

            # Verify response
            assert response["status"] == "accepted"
            assert response["candidate_id"] == valid_payload["candidate_id"]
            assert "processing_job_id" in response

            print("✅ Webhook successfully queued job")

    async def test_webhook_returns_404_for_unknown_candidate(self, valid_payload):
        """
        Test 404 response when candidate doesn't exist.

        Execution Trace:
        1. webhooks.py:candidate_updated_webhook() - Entry point
        2. PostgreSQL SELECT candidate WHERE id = ? - Returns None
        3. Raise HTTPException(404)
        """
        with patch('app.api.webhooks.get_db') as mock_get_db:
            from fastapi import HTTPException

            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None  # Candidate not found
            mock_db.execute.return_value = mock_result

            from app.api.webhooks import candidate_updated_webhook, WebhookPayload

            payload = WebhookPayload(**valid_payload)

            with pytest.raises(HTTPException) as exc_info:
                await candidate_updated_webhook(payload, mock_db)

            assert exc_info.value.status_code == 404
            assert "not found" in str(exc_info.value.detail).lower()

            print("✅ 404 returned for unknown candidate")

    async def test_webhook_job_data_structure(self, valid_payload):
        """
        Test that queued job has correct data structure.

        Expected job structure:
        {
            "job_id": "ingest_{candidate_id}_{timestamp}",
            "candidate_id": str,
            "event_type": str,
            "s3_resume_url": str,
            "timestamp": str (ISO format)
        }
        """
        with patch('app.api.webhooks.redis_client') as mock_redis:
            mock_db = AsyncMock()
            mock_candidate = MagicMock()
            mock_candidate.full_name = "Test User"

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_candidate
            mock_db.execute.return_value = mock_result

            from app.api.webhooks import candidate_updated_webhook, WebhookPayload

            payload = WebhookPayload(**valid_payload)
            await candidate_updated_webhook(payload, mock_db)

            # Extract queued job data
            call_args = mock_redis.lpush.call_args
            job_data = json.loads(call_args[0][1])

            # Verify structure
            assert "job_id" in job_data
            assert job_data["job_id"].startswith("ingest_")
            assert job_data["candidate_id"] == valid_payload["candidate_id"]
            assert job_data["event_type"] == valid_payload["event_type"]
            assert job_data["s3_resume_url"] == valid_payload["s3_resume_url"]

            print("✅ Job data structure is correct")


# ============================================================================
# Job Ingestion Webhook Tests
# ============================================================================

@pytest.mark.asyncio
class TestJobIngestionWebhook:
    """Tests for POST /api/v1/webhooks/job-ingestion endpoint."""

    @pytest.fixture
    def valid_job_request(self):
        """Valid job ingestion request for testing."""
        return {
            "job_id": str(uuid4()),
            "title": "Senior Python Engineer",
            "description": "Build scalable AI systems with FastAPI",
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "must_have_skills": ["Python"],
            "preferred_skills": ["Docker", "Kubernetes"]
        }

    async def test_job_ingestion_creates_embeddings(self, valid_job_request):
        """
        Test that job ingestion creates and stores embeddings.

        Execution Trace:
        1. webhooks.py:job_ingestion_webhook() - Entry point
        2. ontology.py:normalize_skill() - Normalize each skill
        3. ontology.py:expand_skills() - Expand with synonyms
        4. job_embeddings.py:generate_job_embeddings() - Create dual embeddings
        5. vector_store.py:upsert_points("jobs_v1") - Store in Qdrant
        6. redis_client.py:set("job_embeddings:{id}") - Cache embeddings
        7. Return success response
        """
        with patch('app.api.webhooks.expand_skills') as mock_expand, \
             patch('app.api.webhooks.normalize_skill') as mock_normalize, \
             patch('app.api.webhooks.generate_job_embeddings') as mock_gen_emb, \
             patch('app.api.webhooks.vector_store') as mock_vs, \
             patch('app.api.webhooks.redis_client') as mock_redis:

            # Setup mocks
            mock_normalize.return_value = "Python"  # Simplified
            mock_expand.return_value = ["Python", "python", "Python3"]
            mock_gen_emb.return_value = {
                "profile_vector": [0.1] * 384,
                "skills_vector": [0.2] * 384,
                "profile_text": "Senior Python Engineer..."
            }
            mock_vs.upsert_points = AsyncMock(return_value=True)
            mock_redis.set = AsyncMock(return_value=True)

            from app.api.webhooks import job_ingestion_webhook, JobIngestionRequest

            request = JobIngestionRequest(**valid_job_request)
            response = await job_ingestion_webhook(request)

            # Verify embeddings were generated
            mock_gen_emb.assert_called_once()

            # Verify Qdrant storage
            mock_vs.upsert_points.assert_called_once()
            upsert_call = mock_vs.upsert_points.call_args
            assert upsert_call[1]["collection_name"] == "jobs_v1"

            # Verify Redis caching
            mock_redis.set.assert_called_once()
            cache_call = mock_redis.set.call_args
            assert f"job_embeddings:{valid_job_request['job_id']}" in str(cache_call)

            # Verify response
            assert response["status"] == "success"
            assert response["embeddings_created"] is True
            assert response["cached"] is True

            print("✅ Job ingestion created and cached embeddings")

    async def test_job_ingestion_expands_skills(self, valid_job_request):
        """
        Test that skills are expanded using ontology.

        Execution Trace:
        1. ontology.py:normalize_skill() - Map variants to canonical
        2. ontology.py:expand_skills() - Add synonyms and related skills

        Example:
        Input: ["Python", "AWS"]
        Output: ["Python", "python", "Python3", "AWS", "Amazon Web Services", "aws"]
        """
        with patch('app.api.webhooks.expand_skills') as mock_expand, \
             patch('app.api.webhooks.normalize_skill') as mock_normalize, \
             patch('app.api.webhooks.generate_job_embeddings') as mock_gen_emb, \
             patch('app.api.webhooks.vector_store') as mock_vs, \
             patch('app.api.webhooks.redis_client') as mock_redis:

            # Track normalize calls
            normalize_calls = []
            def track_normalize(skill, use_taxonomy=False):
                normalize_calls.append(skill)
                return skill

            mock_normalize.side_effect = track_normalize
            mock_expand.return_value = ["Python", "FastAPI", "PostgreSQL", "python", "fastapi"]
            mock_gen_emb.return_value = {
                "profile_vector": [0.1] * 384,
                "skills_vector": [0.2] * 384,
                "profile_text": "..."
            }
            mock_vs.upsert_points = AsyncMock()
            mock_redis.set = AsyncMock()

            from app.api.webhooks import job_ingestion_webhook, JobIngestionRequest

            request = JobIngestionRequest(**valid_job_request)
            response = await job_ingestion_webhook(request)

            # Verify all skills were normalized
            assert len(normalize_calls) == len(valid_job_request["required_skills"])

            # Verify expand was called
            mock_expand.assert_called_once()

            print(f"✅ Normalized {len(normalize_calls)} skills")

    async def test_job_ingestion_stores_two_vectors(self, valid_job_request):
        """
        Test that two vectors are stored in Qdrant (profile + skills).

        Expected Qdrant points:
        1. {job_id}_profile - Profile embedding (title + description)
        2. {job_id}_skills - Skills embedding (expanded skills list)
        """
        with patch('app.api.webhooks.expand_skills') as mock_expand, \
             patch('app.api.webhooks.normalize_skill') as mock_normalize, \
             patch('app.api.webhooks.generate_job_embeddings') as mock_gen_emb, \
             patch('app.api.webhooks.vector_store') as mock_vs, \
             patch('app.api.webhooks.redis_client') as mock_redis:

            mock_normalize.return_value = "Python"
            mock_expand.return_value = ["Python"]
            mock_gen_emb.return_value = {
                "profile_vector": [0.1] * 384,
                "skills_vector": [0.2] * 384,
                "profile_text": "..."
            }
            mock_vs.upsert_points = AsyncMock()
            mock_redis.set = AsyncMock()

            from app.api.webhooks import job_ingestion_webhook, JobIngestionRequest

            request = JobIngestionRequest(**valid_job_request)
            await job_ingestion_webhook(request)

            # Extract points from upsert call
            call_args = mock_vs.upsert_points.call_args
            points = call_args[1]["points"]

            # Verify two points
            assert len(points) == 2

            # Verify point types
            point_types = [p["payload"]["type"] for p in points]
            assert "profile" in point_types
            assert "skills" in point_types

            print("✅ Stored 2 vectors (profile + skills)")

    async def test_job_ingestion_error_handling(self, valid_job_request):
        """
        Test error handling returns 500 with details.

        Execution Trace:
        1. Any exception in processing -> HTTPException(500)
        2. Error message included in detail
        """
        from fastapi import HTTPException

        with patch('app.api.webhooks.normalize_skill') as mock_normalize:
            mock_normalize.side_effect = Exception("Ontology service unavailable")

            from app.api.webhooks import job_ingestion_webhook, JobIngestionRequest

            request = JobIngestionRequest(**valid_job_request)

            with pytest.raises(HTTPException) as exc_info:
                await job_ingestion_webhook(request)

            assert exc_info.value.status_code == 500
            assert "Failed to create job embeddings" in str(exc_info.value.detail)

            print("✅ Error handling returns 500")


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestWebhookIntegration:
    """Integration tests for webhook endpoints."""

    def test_webhook_endpoints_registered(self):
        """Test that webhook endpoints are properly registered in FastAPI app."""
        from app.main import app

        routes = [route.path for route in app.routes]

        assert "/api/v1/webhooks/candidate-updated" in routes
        assert "/api/v1/webhooks/job-ingestion" in routes

        print("✅ Webhook endpoints registered")

    def test_webhook_payload_validation(self):
        """Test Pydantic validation on webhook payloads."""
        from app.api.webhooks import WebhookPayload, JobIngestionRequest
        from pydantic import ValidationError

        # Invalid candidate-updated payload (missing required field)
        with pytest.raises(ValidationError):
            WebhookPayload(
                event_type="resume_uploaded",
                # Missing candidate_id
                timestamp=datetime.utcnow(),
                s3_resume_url="test.pdf",
                profile_snapshot={}
            )

        # Invalid job-ingestion payload (missing required field)
        with pytest.raises(ValidationError):
            JobIngestionRequest(
                job_id="123",
                title="Test",
                # Missing description
                required_skills=["Python"]
            )

        print("✅ Payload validation works correctly")


# ============================================================================
# Main Test Runner
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("RUNNING WEBHOOK TESTS")
    print("="*80 + "\n")

    pytest.main([__file__, "-v", "--tb=short"])
