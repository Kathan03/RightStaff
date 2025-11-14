# backend/tests/test_ranking.py
"""
Unit tests for ranking pipeline components.
Tests each service in isolation with mocked dependencies.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys


# CRITICAL: Mock all external service modules BEFORE any imports
mock_redis = MagicMock()
mock_redis.get = AsyncMock(return_value=None)
mock_redis.set = AsyncMock(return_value=True)
mock_redis.ping = AsyncMock(return_value=True)

sys.modules['app.services.redis_client'] = MagicMock(redis_client=mock_redis)


@pytest.mark.asyncio
async def test_job_embedding_generation():
    """Test that job embeddings are generated correctly."""

    with patch('app.services.job_embeddings.vector_store') as mock_vs, \
         patch('app.services.job_embeddings.embedding_service') as mock_emb, \
         patch('app.services.job_embeddings.expand_skills') as mock_expand:

        # Setup mocks
        mock_emb.embed_text = AsyncMock(return_value=[0.1] * 384)
        mock_expand.return_value = ['Python', 'python', 'py']
        mock_vs.upsert_points = AsyncMock(return_value=True)

        from app.services.job_embeddings import job_embedding_service

        job_data = {
            'id': 'test-job-1',
            'title': 'Senior Python Developer',
            'description': 'Build scalable APIs with FastAPI',
            'must_have_skills_json': ['Python', 'FastAPI'],
            'required_skills_json': ['PostgreSQL', 'Redis']
        }

        profile_emb, skills_emb, job_hash = await job_embedding_service.get_or_create_job_embeddings(job_data)

        assert len(profile_emb) == 384
        assert len(skills_emb) == 384
        assert job_hash is not None
        assert mock_emb.embed_text.call_count == 2
        print("✅ Job embedding generation test passed")


@pytest.mark.asyncio
async def test_dense_retrieval():
    """Test dense retrieval with mocked Qdrant."""

    with patch('app.services.retrieval.vector_store') as mock_store, \
         patch('app.services.retrieval.job_embedding_service') as mock_job_emb:

        mock_result_1 = Mock()
        mock_result_1.payload = {'candidate_id': 'cand-1', 'kind': 'profile'}
        mock_result_1.score = 0.9

        mock_result_2 = Mock()
        mock_result_2.payload = {'candidate_id': 'cand-2', 'kind': 'profile'}
        mock_result_2.score = 0.7

        mock_store.search = Mock(return_value=[mock_result_1, mock_result_2])
        mock_job_emb.get_or_create_job_embeddings = AsyncMock(
            return_value=([0.1] * 384, [0.2] * 384, 'hash123')
        )

        from app.services.retrieval import dense_retriever

        job_data = {'id': 'job-1', 'title': 'Test Job'}
        candidate_ids = ['cand-1', 'cand-2', 'cand-3']

        results = await dense_retriever.retrieve_candidates(
            job_data, candidate_ids, top_k=10
        )

        assert len(results) <= 10
        if results:
            assert results[0].combined_score >= results[-1].combined_score
        print("✅ Dense retrieval test passed")


@pytest.mark.asyncio
async def test_structured_scoring():
    """Test structured scoring calculations."""
    from app.services.scoring import structured_scorer

    candidate = {
        'years_experience': 5,
        'skills': ['Python', 'FastAPI', 'PostgreSQL'],
        'city': 'Austin',
        'open_to_remote': True,
        'updated_at': '2025-11-01T00:00:00Z',
        'professional_summary': 'Experienced software engineer'
    }

    job = {
        'required_skills_json': ['Python', 'FastAPI', 'Redis'],
        'min_years_experience': 3,
        'max_years_experience': 10,
        'location': 'Austin',
        'work_arrangement': 'hybrid',
        'department': 'engineering'
    }

    score = await structured_scorer.calculate_score(candidate, job)

    assert 0 <= score.combined_score <= 1
    assert score.nice_to_have_coverage == 2/3
    assert score.location_score == 1.0
    assert score.experience_score > 0.5
    print("✅ Structured scoring test passed")


@pytest.mark.asyncio
async def test_score_blending():
    """Test that scores are blended correctly."""

    # Import with all dependencies mocked
    with patch('app.services.ranking.AsyncSessionLocal'), \
         patch('app.services.ranking.apply_combined_sql_gates'), \
         patch('app.services.ranking.dense_retriever'), \
         patch('app.services.ranking.structured_scorer'), \
         patch('app.services.ranking.explanation_generator'):

        # Must import AFTER patching
        from app.services.ranking import RankingService
        from app.services.retrieval import DenseRetrievalResult
        from app.services.scoring import StructuredScore

        service = RankingService()

        retrieval_results = [
            DenseRetrievalResult(
                candidate_id='cand-1',
                profile_score=0.8,
                skills_score=0.7,
                chunk_score=0.6,
                combined_score=0.73,
                evidence_chunks=[]
            )
        ]

        structured_scores = {
            'cand-1': StructuredScore(
                nice_to_have_coverage=0.8,
                experience_score=0.7,
                recency_score=0.9,
                domain_score=0.6,
                location_score=1.0,
                combined_score=0.79,
                details={}
            )
        }

        completeness_scores = {'cand-1': 0.85}

        results = service._blend_scores(
            retrieval_results,
            structured_scores,
            completeness_scores
        )

        assert len(results) == 1
        expected = 0.40 * 0.73 + 0.35 * 0.79 + 0.25 * 0.85
        assert abs(results[0]['final_score'] - expected) < 0.01
        print("✅ Score blending test passed")


@pytest.mark.asyncio
async def test_candidate_banding():
    """Test that candidates are correctly banded."""

    with patch('app.services.ranking.AsyncSessionLocal'), \
         patch('app.services.ranking.apply_combined_sql_gates'):

        from app.services.ranking import RankingService

        service = RankingService()

        candidates = [
            {'candidate_id': f'cand-{i}', 'final_score': score}
            for i, score in enumerate([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2])
        ]

        banded = service._band_candidates(candidates)

        high_band = [c for c in banded if c['band'] == 'high']
        low_band = [c for c in banded if c['band'] == 'low']

        assert len(high_band) >= 1
        assert len(low_band) >= 1
        assert all(c['confidence'] > 0 for c in banded)
        print("✅ Candidate banding test passed")


@pytest.mark.asyncio
async def test_explanation_generation():
    """Test explanation generation."""
    from app.services.explanation import explanation_generator
    from app.services.scoring import StructuredScore

    ranking_result = {
        'candidate_id': 'cand-1',
        'band': 'high',
        'final_score': 0.85,
        'scores': {'dense': 0.8, 'structured': 0.9, 'completeness': 0.85}
    }

    job_data = {
        'title': 'Senior Developer',
        'min_years_experience': 5
    }

    structured_scores = {
        'cand-1': StructuredScore(
            nice_to_have_coverage=0.8,
            experience_score=0.9,
            recency_score=0.9,
            domain_score=0.7,
            location_score=1.0,
            combined_score=0.85,
            details={
                'skills_matched': ['Python', 'FastAPI'],
                'years_experience': 7,
                'location': 'Austin',
                'remote_eligible': True
            }
        )
    }

    explanation = await explanation_generator.generate(
        ranking_result,
        job_data,
        [],
        structured_scores
    )

    assert 'summary' in explanation
    assert 'reasons' in explanation
    assert len(explanation['reasons']) > 0
    assert 'Senior Developer' in explanation['summary']
    print("✅ Explanation generation test passed")


@pytest.mark.asyncio
async def test_expand_skills():
    """Test skills expansion with ontology."""
    from app.services.ontology import expand_skills

    skills = ['Python', 'JavaScript']
    expanded = await expand_skills(skills, use_taxonomy=False)

    assert 'Python' in expanded
    assert 'JavaScript' in expanded
    print("✅ Skills expansion test passed")


def test_completeness_scoring():
    """Test profile completeness calculation."""

    with patch('app.services.ranking.AsyncSessionLocal'), \
         patch('app.services.ranking.apply_combined_sql_gates'):

        from app.services.ranking import RankingService

        service = RankingService()

        complete_candidate = {
            'id': 'cand-1',
            'resume_url': 'http://example.com/resume.pdf',
            'skills': ['Python', 'Java', 'AWS', 'Docker'],
            'years_experience': 5,
            'email': 'test@example.com',
            'phone': '+1234567890',
            'professional_summary': 'Experienced software engineer'
        }

        incomplete_candidate = {
            'id': 'cand-2',
            'skills': ['Python'],
            'years_experience': None,
            'email': None,
            'phone': None,
            'professional_summary': None
        }

        scores = service._calculate_completeness_scores([complete_candidate, incomplete_candidate])

        assert scores['cand-1'] > scores['cand-2']
        assert scores['cand-1'] == 1.0
        print("✅ Completeness scoring test passed")
