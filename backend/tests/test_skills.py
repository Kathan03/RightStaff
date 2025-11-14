"""
Tests for skills extraction and matching.
TODO: Implement for Days 13-14 (Testing & Delivery)
"""

import pytest
from app.utils.skills import extract_skills, normalize_skill, match_skills


@pytest.mark.unit
def test_extract_skills():
    """Test skills extraction from text."""
    # TODO: Implement test
    pass


@pytest.mark.unit
def test_normalize_skill():
    """Test skill normalization."""
    # TODO: Implement test
    assert normalize_skill("Python") == "python"
    assert normalize_skill("  JavaScript  ") == "javascript"


@pytest.mark.unit
def test_match_skills():
    """Test skills matching logic."""
    # TODO: Implement test
    pass
