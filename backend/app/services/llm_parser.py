"""
OpenAI-based resume parser for production-grade extraction.

ARCHITECTURE CHANGE (2025-11-24):
- REMOVED: Local LLM (Qwen/SmolLM) - too heavy, unstable
- ADDED: OpenAI API (gpt-4o-mini) - fast, cheap, reliable

PRIMARY: OpenAI API (gpt-4o-mini)
- Fast inference (~2-5s)
- High accuracy
- No local resources needed
- Cost: ~$0.0001 per resume

FALLBACK: Spacy/Regex (if OpenAI fails)
- Basic extraction using patterns
- Always available
- Lower accuracy but reliable
"""

import asyncio
import json
import logging
import os
import re
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# OpenAI client (lazy import)
_openai_client = None


def _get_openai_client():
    """Get or create OpenAI client (lazy loading)."""
    global _openai_client

    if _openai_client is None:
        try:
            from openai import AsyncOpenAI
            from app.config import settings

            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY not configured")

            _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info("✅ OpenAI client initialized")
        except ImportError:
            logger.error("❌ OpenAI library not installed. Run: pip install openai")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI client: {e}")
            raise

    return _openai_client


class OpenAIResumeParser:
    """
    Production-grade resume parser using OpenAI API.

    Simple, fast, and reliable. No local model management.
    """

    def __init__(self):
        """Initialize parser (client loads on first use)."""
        logger.info("🤖 OpenAI resume parser initialized (client loads on first use)")

    async def parse_resume(self, resume_text: str) -> Dict:
        """
        Extract structured fields from resume using OpenAI API.

        Args:
            resume_text: Raw resume text (from Unstructured parser)

        Returns:
            {
                "full_name": str,
                "email": str,
                "phone": str,
                "location": {"city": str, "state": str, "country": str},
                "years_experience": float,
                "professional_summary": str,
                "skills": List[str]
            }
        """
        logger.info("📄 Starting OpenAI-based resume parsing")

        # Truncate to 3000 chars (fits in OpenAI context, leaves room for prompt)
        resume_snippet = resume_text[:3000]

        try:
            # Call OpenAI API
            parsed_data = await self._parse_with_openai(resume_snippet)

            logger.info(f"✅ Parsed resume via OpenAI: {parsed_data.get('full_name', 'Unknown')}")
            logger.info(f"   Email: {parsed_data.get('email', 'N/A')}")
            logger.info(f"   Years: {parsed_data.get('years_experience', 'N/A')}")
            logger.info(f"   Skills: {len(parsed_data.get('skills', []))} found")

            return parsed_data

        except Exception as e:
            logger.error(f"❌ OpenAI parsing failed: {e}")
            logger.error("   Falling back to empty structure (spacy fallback handled by caller)")
            return self._empty_structure()

    async def _parse_with_openai(self, resume_text: str) -> Dict:
        """
        Call OpenAI API to extract resume fields.

        Uses gpt-4o-mini for fast, cheap, accurate extraction.
        """
        client = _get_openai_client()

        # Construct strict prompt for JSON extraction
        system_prompt = """You are a resume parser that outputs ONLY valid JSON.

Output format (copy exactly):
{
    "full_name": "string or null",
    "email": "string or null",
    "phone": "string or null",
    "location": {"city": "string or null", "state": "string or null", "country": "string or null"},
    "years_experience": number or null,
    "professional_summary": "string or null",
    "skills": ["skill1", "skill2"]
}

Rules:
- Output ONLY JSON, no explanations
- Calculate years_experience from employment dates
- Extract ALL technical skills (languages, frameworks, tools, databases)
- Use null if field not found
- Location: Use "state" for US states/regions"""

        user_prompt = f"""Extract information from this resume:

{resume_text}

Return ONLY the JSON object."""

        logger.info("⏳ Calling OpenAI API (gpt-4o-mini)...")

        # Call OpenAI with timeout
        from app.config import settings
        timeout = getattr(settings, 'llm_inference_timeout', 30)  # 30s for API calls

        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,  # Low temp for deterministic output
                    max_tokens=1000,  # Enough for resume fields
                    response_format={"type": "json_object"}  # Force JSON mode
                ),
                timeout=timeout
            )

            # Extract JSON from response
            json_str = response.choices[0].message.content
            logger.debug(f"OpenAI response: {json_str[:200]}...")

            # Parse JSON
            parsed = json.loads(json_str)

            # Validate and clean
            parsed = self._validate_and_clean(parsed)

            return parsed

        except asyncio.TimeoutError:
            logger.error(f"❌ OpenAI API timed out after {timeout}s")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse OpenAI response as JSON: {e}")
            logger.error(f"   Response: {json_str[:500]}")
            raise
        except Exception as e:
            logger.error(f"❌ OpenAI API call failed: {e}")
            raise

    def _validate_and_clean(self, data: Dict) -> Dict:
        """
        Validate and clean extracted data.

        - Ensure all expected keys exist
        - Clean phone/email formats
        - Validate years_experience is numeric
        - Ensure skills is a list
        """
        cleaned = {
            "full_name": self._clean_string(data.get("full_name")),
            "email": self._clean_email(data.get("email")),
            "phone": self._clean_phone(data.get("phone")),
            "location": self._clean_location(data.get("location")),
            "years_experience": self._clean_years(data.get("years_experience")),
            "professional_summary": self._clean_string(data.get("professional_summary")),
            "skills": self._clean_skills(data.get("skills"))
        }

        return cleaned

    def _clean_string(self, value) -> Optional[str]:
        """Clean string value."""
        if not value or value == "null":
            return None
        return str(value).strip()

    def _clean_email(self, value) -> Optional[str]:
        """Validate and clean email."""
        if not value:
            return None

        email = str(value).strip().lower()

        # Basic email validation
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return email

        return None

    def _clean_phone(self, value) -> Optional[str]:
        """Clean phone number."""
        if not value:
            return None

        return str(value).strip()

    def _clean_location(self, value) -> Dict[str, Optional[str]]:
        """Clean location object."""
        if not value or not isinstance(value, dict):
            return {"city": None, "state": None, "country": None}

        return {
            "city": self._clean_string(value.get("city")),
            "state": self._clean_string(value.get("state")),
            "country": self._clean_string(value.get("country"))
        }

    def _clean_years(self, value) -> Optional[float]:
        """Clean years of experience."""
        if not value:
            return None

        try:
            years = float(value)
            # Sanity check: 0-50 years
            if 0 <= years <= 50:
                return round(years, 1)
        except (ValueError, TypeError):
            pass

        return None

    def _clean_skills(self, value) -> list:
        """Clean skills list."""
        if not value:
            return []

        if isinstance(value, list):
            return [str(s).strip() for s in value if s]

        if isinstance(value, str):
            # Split by comma if single string
            return [s.strip() for s in value.split(',') if s.strip()]

        return []

    def _empty_structure(self) -> Dict:
        """Return empty structure when parsing fails."""
        return {
            "full_name": None,
            "email": None,
            "phone": None,
            "location": {"city": None, "state": None, "country": None},
            "years_experience": None,
            "professional_summary": None,
            "skills": []
        }


# ═══════════════════════════════════════════════════════════════
# Singleton instance
# ═══════════════════════════════════════════════════════════════

_parser_instance = None


def get_openai_parser() -> OpenAIResumeParser:
    """
    Get or create singleton OpenAI parser instance.

    Simple and clean - no model loading complexity.
    """
    global _parser_instance

    if _parser_instance is None:
        _parser_instance = OpenAIResumeParser()

    return _parser_instance


# Backward compatibility alias
get_llm_parser = get_openai_parser
