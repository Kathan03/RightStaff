"""
Tests for LLM-based resume parser.

Tests cover:
1. Model loading (lazy loading)
2. Complete resume parsing
3. Minimal resume parsing
4. Special characters handling
5. Async behavior
6. Error handling and fallback
"""

import pytest
from app.services.llm_parser import get_llm_parser, LLMResumeParser


class TestLLMParserLoading:
    """Test LLM parser initialization and loading."""

    def test_get_llm_parser_singleton(self):
        """Test that get_llm_parser returns singleton instance."""
        parser1 = get_llm_parser()
        parser2 = get_llm_parser()

        assert parser1 is parser2
        assert isinstance(parser1, LLMResumeParser)

    def test_parser_lazy_loading(self):
        """Test that model is not loaded on initialization."""
        parser = LLMResumeParser()

        # Model should not be loaded yet
        assert parser.model is None
        assert parser.tokenizer is None


@pytest.mark.asyncio
class TestLLMResumeParsingComplete:
    """Test parsing complete resumes with all fields."""

    async def test_parse_complete_resume(self):
        """Test parsing a complete resume with all fields."""
        parser = get_llm_parser()

        resume_text = """
        John Doe
        Senior Software Engineer
        john.doe@example.com | (555) 123-4567
        San Francisco, CA 94105

        SUMMARY
        Experienced software engineer with 10+ years in Python development and cloud architecture.
        Proven track record of building scalable systems and leading engineering teams.

        EXPERIENCE
        Google Inc. | Senior Software Engineer | January 2018 - Present
        - Led microservices development team of 8 engineers
        - Architected cloud solutions on AWS and GCP
        - Improved system performance by 40%

        Microsoft | Software Engineer | June 2015 - December 2017
        - Developed enterprise applications using .NET and Azure
        - Implemented CI/CD pipelines

        Amazon | Junior Engineer | May 2013 - May 2015
        - Built e-commerce backend services
        - Worked with large-scale distributed systems

        SKILLS
        Python, JavaScript, AWS, Docker, Kubernetes, FastAPI, PostgreSQL, React, Redis, CI/CD
        """

        result = await parser.parse_resume(resume_text)

        # Validate all fields extracted
        assert result["full_name"] is not None
        assert "john" in result["full_name"].lower() or "doe" in result["full_name"].lower()

        assert result["email"] == "john.doe@example.com"

        assert result["phone"] is not None
        assert "555" in result["phone"]

        # Years of experience should be calculated from employment history
        # 2018-present (~7 years) + 2015-2017 (2.5 years) + 2013-2015 (2 years) = ~11.5 years
        # Allow range of 8-12 years for variance in LLM calculation
        assert result["years_experience"] is not None
        assert 8 <= result["years_experience"] <= 12

        # Skills should be extracted
        assert isinstance(result["skills"], list)
        assert len(result["skills"]) > 0

        # Check for some expected skills (case-insensitive)
        skills_lower = [s.lower() for s in result["skills"]]
        assert any("python" in s for s in skills_lower)

        # Professional summary should be generated
        assert result["professional_summary"] is not None
        assert len(result["professional_summary"]) > 0

    async def test_parse_resume_with_different_date_formats(self):
        """Test parsing resume with various date formats."""
        parser = get_llm_parser()

        resume_text = """
        Jane Smith
        Data Scientist
        jane.smith@example.com

        EXPERIENCE
        Tech Corp | Data Scientist | Jan 2020 - Current
        - Built ML models for customer segmentation

        Analytics Inc | Analyst | 06/2017 - 12/2019
        - Performed statistical analysis

        Research Lab | Intern | Summer 2016
        - Conducted research on NLP
        """

        result = await parser.parse_resume(resume_text)

        assert result["full_name"] is not None
        assert result["email"] == "jane.smith@example.com"
        assert result["years_experience"] is not None
        # Should calculate roughly 4-8 years
        assert 3 <= result["years_experience"] <= 9


@pytest.mark.asyncio
class TestLLMResumeParsingMinimal:
    """Test parsing minimal resumes with few fields."""

    async def test_parse_minimal_resume(self):
        """Test parsing a minimal resume (only name and email)."""
        parser = get_llm_parser()

        resume_text = """
        Jane Smith
        jane.smith@example.com
        """

        result = await parser.parse_resume(resume_text)

        # Name and email should be extracted
        assert result["full_name"] is not None
        assert "jane" in result["full_name"].lower() or "smith" in result["full_name"].lower()
        assert result["email"] == "jane.smith@example.com"

        # Other fields may be None - that's OK
        # years_experience should be None or 0 if no work history
        if result["years_experience"] is not None:
            assert result["years_experience"] >= 0

    async def test_parse_resume_missing_email(self):
        """Test parsing resume without email."""
        parser = get_llm_parser()

        resume_text = """
        Bob Johnson
        Software Developer
        (555) 987-6543

        Expert in Python and JavaScript
        """

        result = await parser.parse_resume(resume_text)

        assert result["full_name"] is not None
        assert result["email"] is None  # No email in resume
        assert result["phone"] is not None


@pytest.mark.asyncio
class TestLLMResumeParsingSpecialCases:
    """Test parsing resumes with special characters and edge cases."""

    async def test_parse_with_special_chars(self):
        """Test parsing resume with special characters."""
        parser = get_llm_parser()

        resume_text = """
        José García-López
        jose.garcia@example.com
        +34 123 456 789
        Madrid, Spain

        Senior Developer with 8 years of experience in web development.

        SKILLS
        Python, JavaScript, React, Node.js
        """

        result = await parser.parse_resume(resume_text)

        # Should handle accented characters
        assert result["full_name"] is not None
        assert result["email"] == "jose.garcia@example.com"

        # Location should include international format
        if result["location"] and result["location"].get("city"):
            assert "madrid" in result["location"]["city"].lower()

    async def test_parse_very_long_resume(self):
        """Test that parser truncates very long resumes correctly."""
        parser = get_llm_parser()

        # Create a resume longer than 2000 chars
        long_text = "John Doe\njohn@example.com\n\n" + "Experience section. " * 200

        result = await parser.parse_resume(long_text)

        # Should still extract basic info
        assert result["full_name"] is not None
        assert result["email"] == "john@example.com"

    async def test_parse_empty_resume(self):
        """Test parsing empty or invalid resume."""
        parser = get_llm_parser()

        result = await parser.parse_resume("")

        # Should return empty structure
        assert result["full_name"] is None
        assert result["email"] is None
        assert result["skills"] == []


@pytest.mark.asyncio
class TestLLMParserValidation:
    """Test data validation and cleaning methods."""

    async def test_email_validation(self):
        """Test that invalid emails are rejected."""
        parser = get_llm_parser()

        # Valid email
        assert parser._clean_email("test@example.com") == "test@example.com"

        # Invalid emails
        assert parser._clean_email("not-an-email") is None
        assert parser._clean_email("missing@domain") is None
        assert parser._clean_email("") is None
        assert parser._clean_email(None) is None

    async def test_years_validation(self):
        """Test years of experience validation."""
        parser = get_llm_parser()

        # Valid years
        assert parser._clean_years(5) == 5.0
        assert parser._clean_years(10.5) == 10.5
        assert parser._clean_years("7") == 7.0

        # Invalid years (out of range)
        assert parser._clean_years(-5) is None
        assert parser._clean_years(100) is None

        # Invalid types
        assert parser._clean_years("not-a-number") is None
        assert parser._clean_years(None) is None

    async def test_skills_cleaning(self):
        """Test skills list cleaning."""
        parser = get_llm_parser()

        # List of skills
        assert parser._clean_skills(["Python", "JavaScript"]) == ["Python", "JavaScript"]

        # Comma-separated string
        assert parser._clean_skills("Python, JavaScript, React") == ["Python", "JavaScript", "React"]

        # Empty or None
        assert parser._clean_skills([]) == []
        assert parser._clean_skills(None) == []
        assert parser._clean_skills("") == []


@pytest.mark.asyncio
class TestLLMParserErrorHandling:
    """Test error handling and edge cases."""

    async def test_parse_with_corrupted_text(self):
        """Test parsing with corrupted/garbled text."""
        parser = get_llm_parser()

        # Simulated corrupted text
        corrupted_text = "asdf;lkj23498@#$%^&*()_+{}|:<>?/.,;'[]\\-="

        result = await parser.parse_resume(corrupted_text)

        # Should return empty structure without crashing
        assert isinstance(result, dict)
        assert "full_name" in result
        assert "email" in result
        assert "skills" in result


# ═══════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestLLMParserIntegration:
    """Integration tests with real-world scenarios."""

    async def test_multiple_concurrent_parses(self):
        """Test that parser handles concurrent requests correctly."""
        import asyncio

        parser = get_llm_parser()

        resume_texts = [
            "Alice Johnson\nalice@example.com\nSoftware Engineer",
            "Bob Smith\nbob@example.com\nData Scientist",
            "Carol White\ncarol@example.com\nProduct Manager",
        ]

        # Parse all resumes concurrently
        tasks = [parser.parse_resume(text) for text in resume_texts]
        results = await asyncio.gather(*tasks)

        # All should complete successfully
        assert len(results) == 3
        assert all(r["email"] is not None for r in results)

    async def test_parser_performance(self):
        """Test that parsing completes within acceptable time."""
        import time

        parser = get_llm_parser()

        resume_text = """
        John Doe
        john.doe@example.com
        Senior Engineer with 10 years experience
        Skills: Python, AWS, Docker
        """

        start_time = time.time()
        result = await parser.parse_resume(resume_text)
        elapsed_time = time.time() - start_time

        # First parse may take longer due to model loading
        # Subsequent parses should be faster
        # Allow up to 30 seconds for first parse (includes model loading)
        assert elapsed_time < 30

        assert result["full_name"] is not None


# ═══════════════════════════════════════════════════════════════
# Test Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def sample_resume_complete():
    """Complete resume sample for testing."""
    return """
    Michael Chen
    Senior Full-Stack Developer
    michael.chen@techcorp.com | (555) 234-5678
    Seattle, WA 98101

    PROFESSIONAL SUMMARY
    Results-driven software engineer with 12+ years of experience building scalable
    web applications and leading cross-functional teams.

    EXPERIENCE
    TechCorp Inc. | Senior Full-Stack Developer | March 2018 - Present
    - Lead development of microservices architecture serving 10M+ users
    - Mentor junior developers and conduct code reviews
    - Technologies: Python, React, PostgreSQL, AWS, Docker

    WebSolutions Ltd. | Software Developer | June 2015 - February 2018
    - Built RESTful APIs and responsive web applications
    - Implemented CI/CD pipelines using Jenkins and GitLab

    StartupXYZ | Junior Developer | August 2012 - May 2015
    - Developed features for e-commerce platform
    - Collaborated with design team on UX improvements

    EDUCATION
    B.S. in Computer Science, University of Washington, 2012

    SKILLS
    Python, JavaScript, React, Node.js, PostgreSQL, MongoDB, AWS, Docker,
    Kubernetes, Redis, FastAPI, Django, Git, Agile, Scrum
    """


@pytest.mark.asyncio
async def test_with_sample_resume(sample_resume_complete):
    """Test parsing with realistic complete resume."""
    parser = get_llm_parser()
    result = await parser.parse_resume(sample_resume_complete)

    assert result["full_name"] is not None
    assert "michael" in result["full_name"].lower() or "chen" in result["full_name"].lower()
    assert result["email"] == "michael.chen@techcorp.com"
    assert result["phone"] is not None
    assert result["years_experience"] is not None
    assert 10 <= result["years_experience"] <= 14  # Should calculate ~12 years
    assert len(result["skills"]) >= 5  # Should extract multiple skills
